from database import OfferDatabase
from openai import OpenAI
import json
from config import OPENAI_API_KEY
from fpdf import FPDF
import tempfile
import streamlit as st
import logging
import os
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)

class OfferGenerator:
    def __init__(self, db: OfferDatabase):
        self.db = db
        if not OPENAI_API_KEY:
            logger.error("Brak klucza API OpenAI")
            raise ValueError("Brak klucza API OpenAI. Sprawdź plik .env")
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def calculate_total_cost(self, offer_data: dict) -> float:
        """Oblicza całkowity koszt na podstawie wszystkich składników"""
        total = 0.0
        
        try:
            # Koszt pojazdu i zabudowy
            pojazd = offer_data.get('pojazd', {})
            total += float(pojazd.get('zabudowa_cena') or 0)
            total += float(pojazd.get('sklejki_cena') or 0)
            total += float(pojazd.get('nadkola_cena') or 0)
            
            # Koszt agregatu
            agregat = offer_data.get('agregat', {})
            total += float(agregat.get('cena_cennikowa') or 0)
            
            # Koszt grzania
            grzanie = offer_data.get('grzanie', {})
            total += float(grzanie.get('cena') or 0)
            
            # Koszt zestawu podgrzewacza
            zestaw = offer_data.get('zestaw_podgrzewacza', {})
            total += float(zestaw.get('cena') or 0)
            
            return total
        except (ValueError, TypeError) as e:
            logger.error(f"Błąd podczas obliczania kosztu całkowitego: {str(e)}")
            return 0.0

    def create_offer(self, text: str) -> tuple:
        if not text:
            logger.warning("Otrzymano pusty tekst")
            st.error("Tekst nie może być pusty")
            return 0, 0 
            
        # Pobieranie danych z bazy
        try:
            cursor = self.db.conn.cursor()
            
            # Pobierz dane o samochodach
            cursor.execute("""
                SELECT 
                    "Marka", "Model", "Kubatura (m³)",
                    "Zabudowy izotermiczne Cena (zł netto)",
                    "Sklejki Cena (zł netto)",
                    "Nadkola sklejka 12mm Cena zł netto"
                FROM samochody
            """)
            vehicles = cursor.fetchall()
            
            # Pobierz dane o agregatach
            cursor.execute("""
                SELECT *
                FROM "Agregaty Daikin"
            """)
            agregaty = cursor.fetchall()
            
            # Pobierz dane o opcjach grzania
            cursor.execute('SELECT * FROM "Grzanie"')
            grzanie = cursor.fetchall()
            
            # Przygotuj dane dla LLM
            db_context = {
                "dostepne_samochody": [
                    {
                        "marka": v[0],
                        "model": v[1],
                        "kubatura": v[2],
                        "zabudowa_cena": float(v[3] if v[3] is not None else 0),
                        "sklejki_cena": float(v[4] if v[4] is not None else 0),
                        "nadkola_cena": float(v[5] if v[5] is not None else 0)
                    } for v in vehicles
                ],
                "dostepne_agregaty": [
                    {
                        "model": a[1],
                        "daikin_product_line": a[0],
                        "refrigerant": a[2],
                        "instalacja_elektryczna": a[3],
                        "cena_cennikowa": float(a[7] if a[7] is not None else 0),
                        "cooling_capacity_0C": float(a[8] if a[8] is not None else 0),
                        "cooling_capacity_-20C": float(a[9] if a[9] is not None else 0),
                        "recommended_van_size_0C": float(a[10] if a[10] is not None else 0),
                        "recommended_van_size_-20C": float(a[11] if a[11] is not None else 0)
                    } for a in agregaty
                ],
                "opcje_grzania": [
                    {
                        "model": g[0],
                        "opcja": g[1],
                        "cena": float(g[2] if g[2] is not None else 0)
                    } for g in grzanie
                ]
            }

            # Zaktualizowany prompt z instrukcjami wyszukiwania danych firmy
            analysis_prompt = f"""
            Przeanalizuj tekst oferty i wybierz odpowiednie dane z bazy danych.
            
            Jeśli w tekście znajduje się nazwa firmy lub NIP, wyszukaj dodatkowe informacje o firmie w publicznie dostępnych źródłach, w tym na stronie https://aleo.com/pl/.
            Wykorzystaj te informacje do uzupełnienia danych firmy w ofercie.
            
            WAŻNE ZASADY DOTYCZĄCE POJAZDÓW:
            1. Nazwy pojazdów w bazie są zapisane w formacie "Opel Combo", "Opel Vivaro" itp.
            2. Podczas wyszukiwania:
               - Traktuj całą nazwę (np. "Opel Vivaro") jako markę pojazdu
               - Model to odpowiedni wariant (np. "L1H1", "L2H2")
            3. Przykład:
               - Dla "Opel Vivaro L2H1":
                 * marka: "Opel Vivaro"
                 * model: "L2H1"
            
            Dostępne dane w bazie:
            {json.dumps(db_context, indent=2, ensure_ascii=False)}
            
            WAŻNE: Zwróć TYLKO czysty JSON, bez żadnego dodatkowego tekstu czy formatowania markdown.
            
            Format odpowiedzi:
            {{
                "dane_firmy": {{
                    "nazwa": "",
                    "adres": "",
                    "nip": "",
                    "osoba_odpowiedzialna": "",
                    "telefon": "",
                    "email": ""
                }},
                "data_oferty": "",
                "numer_oferty": "",
                "pojazd": {{
                    "marka": "",  # np. "Opel Vivaro"
                    "model": "",  # np. "L2H1"
                    "kubatura": null,
                    "zabudowa_cena": null,
                    "sklejki_cena": null,
                    "nadkola_cena": null
                }},
                "agregat": {{
                    "model": "",
                    "daikin_product_line": "",
                    "refrigerant": "",
                    "instalacja_elektryczna": "",
                    "tylko_drogowy": "",
                    "drogowy_siec_230V": "",
                    "drogowy_siec_400V": "",
                    "cena_cennikowa": null,
                    "cooling_capacity_0C": null,
                    "cooling_capacity_-20C": null,
                    "recommended_van_size_0C": null,
                    "recommended_van_size_-20C": null,
                    "uwagi": "",
                    "temperature_range": ""
                }},
                "grzanie": {{
                    "model_jednostki": "",
                    "model_opcji": "",
                    "cena": null
                }},
                "zestaw_podgrzewacza": {{
                    "grzatki_elektryczne": "",
                    "model_opcji": "",
                    "cena": null
                }}
            }}
            
            Podczas wyszukiwania danych:
            1. Dopasuj pojazd na podstawie pełnej nazwy marki (np. "Opel Vivaro") i modelu (np. "L2H1")
            2. Wybierz odpowiedni agregat Daikin na podstawie wymagań klienta i rekomendowanej wielkości pojazdu
            3. Dobierz opcje grzania i podgrzewacza jeśli są wymagane
            4. Upewnij się, że wszystkie ceny są poprawnie skopiowane z bazy danych
            5. Jeśli jakieś pole nie jest wymagane lub nie ma danych, zostaw je puste lub null
            
            Pamiętaj o:
            - Sprawdzeniu czy wybrany agregat jest kompatybilny z pojazdem (na podstawie Recommended Van size)
            - Uwzględnieniu wymagań dot. instalacji elektrycznej pojazdu
            - Sprawdzeniu dostępnych opcji grzania dla wybranego modelu
            """

            # Analiza tekstu oferty
            logger.info("Analizowanie tekstu oferty...")
            analysis_response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": analysis_prompt},
                    {"role": "user", "content": text}
                ]
            )
            
            # Sanityzacja i parsowanie odpowiedzi JSON
            try:
                response_content = analysis_response.choices[0].message.content
                
                # Wyciągnięcie JSON z odpowiedzi
                json_start = response_content.find('{')
                json_end = response_content.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_content = response_content[json_start:json_end]
                    
                    # Próba sparsowania JSON
                    try:
                        extracted_info = json.loads(json_content)
                        logger.info(f"Wyodrębnione informacje: {json.dumps(extracted_info, indent=2, ensure_ascii=False)}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Błąd parsowania wyciągniętego JSON: {str(e)}")
                        logger.error(f"Wyciągnięty JSON: {json_content}")
                        return None, None
                else:
                    logger.error("Nie znaleziono prawidłowej struktury JSON w odpowiedzi")
                    logger.error(f"Otrzymana odpowiedź: {response_content}")
                    return None, None
                
            except json.JSONDecodeError as e:
                logger.error(f"Błąd parsowania JSON: {str(e)}")
                logger.error(f"Otrzymana odpowiedź: {response_content}")
                st.error("Błąd podczas analizy tekstu. Spróbuj ponownie.")
                return None, None
            
            # Po sparsowaniu JSON, sprawdzamy i uzupełniamy brakujące pola
            try:
                if 'zabudowa' in extracted_info:
                    zabudowa = extracted_info['zabudowa']
                    if not isinstance(zabudowa.get('wykonczenia'), list):
                        zabudowa['wykonczenia'] = []
                    
                    # Upewniamy się, że wszystkie wymagane pola istnieją
                    required_fields = {
                        'typ': '', 'temperatura': '', 'cena_netto': 0,
                        'atest_pzh': True, 'gwarancja': '',
                        'material_izolacyjny': {'typ': '', 'grubosc': ''},
                        'sciany_sufit': '', 'podloga': '', 'wykonczenia': []
                    }
                    
                    for field, default_value in required_fields.items():
                        if field not in zabudowa:
                            zabudowa[field] = default_value
                            
                    if 'material_izolacyjny' not in zabudowa:
                        zabudowa['material_izolacyjny'] = {'typ': '', 'grubosc': ''}
                    
                # Obliczanie całkowitego kosztu
                total_cost = self.calculate_total_cost(extracted_info)
                extracted_info['cena_calkowita_netto'] = total_cost
                
                # Pobieranie informacji o pojeździe z bazy
                db_vehicle_info = self.db.get_vehicle_info(
                    marka=extracted_info['pojazd']['marka'],
                    model=extracted_info['pojazd']['model']
                )
                
                if not db_vehicle_info:
                    logger.warning(f"Nie znaleziono pojazdu {extracted_info['pojazd']['marka']} {extracted_info['pojazd']['model']} w bazie")
                    st.warning("Wybrany pojazd nie jest dostępny w bazie")
                    return None, None
                
                logger.info(f"Znaleziono pojazd w bazie: {json.dumps(db_vehicle_info, indent=2, ensure_ascii=False)}")
                
                # Tworzenie finalnej oferty
                offer_data = {
                    "dane_firmy": extracted_info['dane_firmy'],
                    "data_oferty": extracted_info['data_oferty'],
                    "numer_oferty": extracted_info['numer_oferty'],
                    "pojazd": {
                        **extracted_info['pojazd'],
                        "zabudowa_cena": float(db_vehicle_info.get('zabudowa_cena') or 0),
                        "sklejki_cena": float(db_vehicle_info.get('sklejki_cena') or 0),
                        "nadkola_cena": float(db_vehicle_info.get('nadkola_cena') or 0)
                    },
                    "agregat": {
                        **extracted_info['agregat'],
                        "cena_cennikowa": float(extracted_info['agregat'].get('cena_cennikowa') or 0)
                    },
                    "grzanie": {
                        **extracted_info.get('grzanie', {}),
                        "cena": float(extracted_info.get('grzanie', {}).get('cena') or 0)
                    },
                    "zestaw_podgrzewacza": {
                        **extracted_info.get('zestaw_podgrzewacza', {}),
                        "cena": float(extracted_info.get('zestaw_podgrzewacza', {}).get('cena') or 0)
                    },
                    "cena_calkowita_netto": self.calculate_total_cost(extracted_info)
                }
                
                logger.info(f"Wygenerowano ofertę: {json.dumps(offer_data, indent=2, ensure_ascii=False)}")
                
                # Sprawdzenie wymaganych danych
                missing_data = []
                
                # Sprawdź dane firmy
                required_company_data = ['nazwa', 'adres', 'nip']
                for field in required_company_data:
                    if not offer_data.get('dane_firmy', {}).get(field):
                        missing_data.append(f"Dane firmy - {field}")
                
                # Sprawdź dane pojazdu
                required_vehicle_data = ['marka', 'model', 'kubatura']
                for field in required_vehicle_data:
                    if not offer_data.get('pojazd', {}).get(field):
                        missing_data.append(f"Pojazd - {field}")
                
                # Sprawdź dane agregatu
                required_aggregate_data = ['model', 'cena_cennikowa']
                for field in required_aggregate_data:
                    if not offer_data.get('agregat', {}).get(field):
                        missing_data.append(f"Agregat - {field}")

                # Zwróć dane oferty wraz z listą brakujących danych
                return offer_data, missing_data
                
            except Exception as e:
                logger.error(f"Błąd podczas przetwarzania danych: {str(e)}")
                logger.error(f"Szczegóły błędu:\n{traceback.format_exc()}")
                return None, None
            
        except Exception as e:
            logger.error(f"Błąd podczas generowania oferty: {str(e)}")
            logger.error(f"Szczegóły błędu:\n{traceback.format_exc()}")
            st.error(f"Wystąpił błąd: {str(e)}")
            return None, None

    def _generate_pdf(self, offer_data, missing_data) -> str:
        def remove_pl_chars(text):
            """Usuwa polskie znaki z tekstu"""
            if not isinstance(text, str):
                text = str(text)
            chars = {
                'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 
                'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
                'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N', 
                'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z'
            }
            for pl, en in chars.items():
                text = text.replace(pl, en)
            return text

        try:
            # Usuwamy polskie znaki z komunikatów błędów
            if missing_data:
                error_message = "Nie mozna wygenerowac PDF. Brakujace dane:\n- " + "\n- ".join(map(remove_pl_chars, missing_data))
                logger.error(error_message)
                st.error(error_message)
                return None
            
            # Usuwamy polskie znaki ze wszystkich danych
            sanitized_data = {
                'dane_firmy': {remove_pl_chars(k): remove_pl_chars(v) for k, v in offer_data['dane_firmy'].items()},
                'pojazd': {remove_pl_chars(k): remove_pl_chars(str(v)) for k, v in offer_data['pojazd'].items()},
                'agregat': {remove_pl_chars(k): remove_pl_chars(str(v)) for k, v in offer_data['agregat'].items()},
                'data_oferty': remove_pl_chars(str(offer_data.get('data_oferty', ''))),
                'numer_oferty': remove_pl_chars(str(offer_data.get('numer_oferty', '')))
            }
            
            if 'grzanie' in offer_data:
                sanitized_data['grzanie'] = {remove_pl_chars(k): remove_pl_chars(str(v)) for k, v in offer_data['grzanie'].items()}
            
            if 'zestaw_podgrzewacza' in offer_data:
                sanitized_data['zestaw_podgrzewacza'] = {remove_pl_chars(k): remove_pl_chars(str(v)) for k, v in offer_data['zestaw_podgrzewacza'].items()}
            
            pdf = OfferTemplate()
            
            # Sekcje z tekstem (bez polskich znaków)
            pdf.create_section('Dane firmy', sanitized_data['dane_firmy'])
            pdf.create_section('Informacje o pojezdzie', sanitized_data['pojazd'])
            pdf.create_section('Agregat', {k: v for k, v in sanitized_data['agregat'].items() if 'cena' not in k.lower()})
            
            if 'grzanie' in sanitized_data:
                pdf.create_section('Grzanie', sanitized_data['grzanie'])
            
            if 'zestaw_podgrzewacza' in sanitized_data:
                pdf.create_section('Zestaw podgrzewacza', sanitized_data['zestaw_podgrzewacza'])
            
            # Sekcja kosztów
            koszty_data = {
                'Zabudowa izotermiczna': f"{float(offer_data['pojazd'].get('zabudowa_cena') or 0):.2f} PLN",
                'Sklejki': f"{float(offer_data['pojazd'].get('sklejki_cena') or 0):.2f} PLN",
                'Nadkola': f"{float(offer_data['pojazd'].get('nadkola_cena') or 0):.2f} PLN",
                'Agregat': f"{float(offer_data['agregat'].get('cena_cennikowa') or 0):.2f} PLN"
            }
            
            if 'grzanie' in offer_data:
                koszty_data['Grzanie'] = f"{float(offer_data['grzanie'].get('cena') or 0):.2f} PLN"
            
            if 'zestaw_podgrzewacza' in offer_data:
                koszty_data['Zestaw podgrzewacza'] = f"{float(offer_data['zestaw_podgrzewacza'].get('cena') or 0):.2f} PLN"
            
            pdf.create_section('Szczegoly kosztow', {remove_pl_chars(k): v for k, v in koszty_data.items()})
            
            # Obliczanie i wyświetlanie sumy
            total_cost = sum([
                float(offer_data['pojazd'].get('zabudowa_cena') or 0),
                float(offer_data['pojazd'].get('sklejki_cena') or 0),
                float(offer_data['pojazd'].get('nadkola_cena') or 0),
                float(offer_data['agregat'].get('cena_cennikowa') or 0),
                float(offer_data.get('grzanie', {}).get('cena') or 0),
                float(offer_data.get('zestaw_podgrzewacza', {}).get('cena') or 0)
            ])
            
            pdf.create_section('Podsumowanie kosztow', {
                'Cena calkowita netto': f"{total_cost:.2f} PLN",
            })
            
            # Dodaj zdjęcia w prawej kolumnie
            if 'offer_images' in st.session_state and st.session_state['offer_images']:
                pdf.add_images_column(st.session_state['offer_images'])
            
            # Zapisanie PDF
            pdf_path = f"temp/oferta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            pdf.output(pdf_path)
            
            return pdf_path
            
        except Exception as e:
            error_message = f"Blad podczas generowania PDF: {str(e)}"
            logger.error(error_message)
            logger.error(f"Szczegoly bledu:\n{traceback.format_exc()}")
            st.error(error_message)
            return None


class OfferTemplate(FPDF):
    def __init__(self):
        # Najpierw definiujemy wszystkie stałe
        self.header_height = 40
        self.top_margin_after_header = 5
        self.footer_height = 20
        self.content_width = 120
        self.image_x = 140
        self.image_width = 60
        self.image_margin = 5
        
        # Potem inicjalizujemy klasę bazową
        super().__init__()
        self.set_auto_page_break(auto=True, margin=25)
        self.add_page()
        self.set_margins(10, 10, 10)
        
        # Dane do stopki
        self.footer_data = {
            'telefon': '+48 123 456 789',
            'email': 'kontakt@autoadaptacje.pl',
            'www': 'www.autoadaptacje.pl',
            'data_oferty': '',
            'numer_oferty': ''
        }

    def set_footer_data(self, data_oferty, numer_oferty):
        """Ustawia dane do stopki"""
        self.footer_data.update({
            'data_oferty': data_oferty,
            'numer_oferty': numer_oferty
        })
    
    def footer(self):
        # Zapisz aktualną pozycję
        current_y = self.get_y()
        
        # Linia oddzielająca
        self.set_y(-25)
        self.set_fill_color(158, 197, 215)
        self.rect(0, self.get_y(), 210, 0.5, 'F')
        
        # Ustawienia tekstu stopki
        self.set_y(-20)
        self.set_font('Arial', '', 8)
        self.set_text_color(0, 0, 0)
        
        # Lewa strona - dane kontaktowe
        self.cell(70, 4, f"Tel: {self.footer_data['telefon']}", 0, 0, 'L')
        self.cell(70, 4, f"Email: {self.footer_data['email']}", 0, 0, 'C')
        self.cell(50, 4, f"WWW: {self.footer_data['www']}", 0, 1, 'R')
        
        # Druga linia - data i numer oferty
        self.set_y(-15)
        self.cell(70, 4, f"Data oferty: {self.footer_data['data_oferty']}", 0, 0, 'L')
        self.cell(120, 4, f"Numer oferty: {self.footer_data['numer_oferty']}", 0, 1, 'R')
        
        # Przywróć poprzednią pozycję
        self.set_y(current_y)

    def header(self):
        # Logo i nagłówek
        self.set_fill_color(158, 197, 215)
        self.rect(0, 0, 210, self.header_height, 'F')
        
        # Logo
        self.image('images/logo.png', 10, 10, 40)
        
        # Ustawienie pozycji Y po nagłówku
        self.set_y(self.header_height + self.top_margin_after_header)

    def create_section(self, title, content, with_background=True):
        # Jeśli to pierwsza sekcja, upewnij się że zaczyna się po nagłówku
        if self.get_y() < (self.header_height + self.top_margin_after_header):
            self.set_y(self.header_height + self.top_margin_after_header)
        
        # Zapisz aktualną pozycję Y
        start_y = self.get_y()
        
        # Ustaw szerokość tekstu
        self.set_right_margin(210 - self.image_x)
        
        if with_background:
            self.set_fill_color(158, 197, 215)  # Jasny niebieski dla tła
            self.rect(10, self.get_y(), self.content_width - 10, 8, 'F')
        
        self.set_font('Arial', 'B', 12)
        self.set_text_color(0, 0, 0)
        self.cell(self.content_width - 10, 8, title, 0, 1, 'L')
        
        self.set_font('Arial', '', 11)
        if isinstance(content, dict):
            # Lista pól do pominięcia
            skip_fields = [
                'cooling_capacity_0c', 'cooling_capacity_-20c',
                'recommended_van_size_0c', 'recommended_van_size_-20c',
                'daikin_product_line', 'refrigerant', 'temperature_range',
                'tylko_drogowy', 'drogowy_siec_230v', 'drogowy_siec_400v',
                'id', 'uwagi'
            ]
            
            for key, value in content.items():
                # Pomijamy określone pola
                if key.lower() in skip_fields:
                    continue
                    
                # Pomijamy pola z ceną (oprócz sekcji kosztów)
                if (title != 'Podsumowanie kosztow' and title != 'Szczegoly kosztow' and 
                    ('cena' in key.lower() or 'koszt' in key.lower())):
                    continue
                    
                formatted_key = key.replace('_', ' ').title()
                
                # Formatowanie wartości słownikowych
                if isinstance(value, dict):
                    if 'typ' in value and 'grubosc' in value:
                        value = f"{value['typ']}, {value['grubosc']}"
                    elif 'opis' in value:
                        value = value['opis']
                    else:
                        value = ', '.join(f"{k}: {v}" for k, v in value.items() 
                                        if k not in skip_fields and 
                                        (title in ['Podsumowanie kosztow', 'Szczegoly kosztow'] or 'cena' not in k.lower()))
                
                # Formatowanie list
                elif isinstance(value, list):
                    value = ', '.join(str(item) for item in value)
                
                self.multi_cell(self.content_width - 10, 6, f"{formatted_key}: {value}")
        else:
            self.multi_cell(self.content_width - 10, 6, str(content))
        
        # Przywróć standardowy margines
        self.set_right_margin(10)
        return self.get_y() - start_y

    def add_images_column(self, images):
        """Dodaje kolumnę ze zdjęciami po prawej stronie"""
        current_y = self.header_height + self.top_margin_after_header
        image_height = 50  # Wysokość każdego zdjęcia
        
        for image_path in images:
            if os.path.exists(image_path):
                # Sprawdź czy trzeba dodać nową stronę
                if current_y + image_height > self.h - self.footer_height:
                    self.add_page()
                    current_y = self.header_height + self.top_margin_after_header
                
                try:
                    self.image(image_path, x=self.image_x, y=current_y, 
                              w=self.image_width, h=image_height)
                    current_y += image_height + self.image_margin
                except Exception as e:
                    logger.error(f"Błąd podczas dodawania zdjęcia {image_path}: {str(e)}") 