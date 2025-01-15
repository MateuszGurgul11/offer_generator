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
        
        # Koszt zabudowy
        total += float(offer_data.get('zabudowa', {}).get('cena_netto', 0))
        
        # Koszt agregatu
        total += float(offer_data.get('agregat', {}).get('cena_netto', 0))
        
        # Koszty montażu
        montaz = offer_data.get('montaz', {})
        total += float(montaz.get('mocowanie_sprezarka', {}).get('cena_netto', 0))
        total += float(montaz.get('montaz_agregatu', {}).get('cena_netto', 0))
        
        return total

    def create_offer(self, text: str) -> tuple:
        if not text:
            logger.warning("Otrzymano pusty tekst")
            st.error("Tekst nie może być pusty")
            return None, None
            
        # Pobieranie danych z bazy
        try:
            cursor = self.db.conn.cursor()
            
            # Pobierz dane o samochodach
            cursor.execute("""
                SELECT marka, model, rok_produkcji, kubatura, klimatyzacja
                FROM samochody WHERE dostepnosc = 1
            """)
            vehicles = cursor.fetchall()
            
            # Pobierz dane o zabudowach
            cursor.execute("""
                SELECT typ, temperatura, cena_netto, atest_pzh, gwarancja,
                       material_izolacyjny_typ, material_izolacyjny_grubosc,
                       sciany_sufit, podloga, wykonczenia
                FROM zabudowy WHERE dostepnosc = 1
            """)
            zabudowy = cursor.fetchall()
            
            # Pobierz dane o agregatach
            cursor.execute("""
                SELECT model, typ, czynnik, cena_netto
                FROM agregaty WHERE dostepnosc = 1
            """)
            agregaty = cursor.fetchall()
            
            # Pobierz dane o montażu
            cursor.execute("""
                SELECT mocowanie_sprezarka_opis, mocowanie_sprezarka_cena, montaz_agregatu_cena
                FROM montaz
            """)
            montaz = cursor.fetchall()
            
            # Przygotuj dane dla LLM
            db_context = {
                "dostepne_samochody": [
                    {
                        "marka": v[0],
                        "model": v[1],
                        "rok_produkcji": v[2],
                        "kubatura": v[3],
                        "klimatyzacja": bool(v[4])
                    } for v in vehicles
                ],
                "dostepne_zabudowy": [
                    {
                        "typ": z[0],
                        "temperatura": z[1],
                        "cena_netto": z[2],
                        "atest_pzh": bool(z[3]),
                        "gwarancja": z[4],
                        "material_izolacyjny": {
                            "typ": z[5],
                            "grubosc": z[6]
                        },
                        "sciany_sufit": z[7],
                        "podloga": z[8],
                        "wykonczenia": z[9].split(',') if z[9] else []
                    } for z in zabudowy
                ],
                "dostepne_agregaty": [
                    {
                        "model": a[0],
                        "typ": a[1],
                        "czynnik": a[2],
                        "cena_netto": a[3]
                    } for a in agregaty
                ],
                "dostepne_montaze": [
                    {
                        "mocowanie_sprezarka": {
                            "opis": m[0],
                            "cena_netto": m[1]
                        },
                        "montaz_agregatu": {
                            "cena_netto": m[2]
                        }
                    } for m in montaz
                ]
            }

            # Zaktualizowany prompt z poprawioną strukturą JSON
            analysis_prompt = f"""
            Przeanalizuj tekst oferty i wybierz odpowiednie dane z bazy danych.
            
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
                    "marka": "",
                    "model": "",
                    "rok_produkcji": null,
                    "kubatura": "",
                    "klimatyzacja": false
                }},
                "zabudowa": {{
                    "typ": "",
                    "temperatura": "",
                    "cena_netto": 0,
                    "atest_pzh": true,
                    "gwarancja": "",
                    "material_izolacyjny": {{
                        "typ": "",
                        "grubosc": ""
                    }},
                    "sciany_sufit": "",
                    "podloga": "",
                    "wykonczenia": []
                }},
                "agregat": {{
                    "model": "",
                    "typ": "",
                    "czynnik": "",
                    "cena_netto": 0
                }},
                "montaz": {{
                    "mocowanie_sprezarka": {{
                        "opis": "",
                        "cena_netto": 0
                    }},
                    "montaz_agregatu": {{
                        "cena_netto": 0
                    }}
                }}
            }}
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
                
                # Sprawdzanie dostępnych adaptacji
                available_adaptations = self.db.get_available_adaptations(db_vehicle_info['id'])
                requested_adaptations = extracted_info['zabudowa']['wykonczenia']
                
                # Sprawdzanie czy wszystkie wymagane adaptacje są dostępne
                unavailable = [adapt for adapt in requested_adaptations if adapt not in available_adaptations]
                
                if unavailable:
                    logger.warning(f"Wykryto niedostępne adaptacje: {unavailable}")
                    st.warning(f"Niektóre wymagane adaptacje nie są dostępne dla tego pojazdu: {', '.join(unavailable)}")
                
                # Tworzenie finalnej oferty
                offer_data = {
                    "dane_firmy": extracted_info['dane_firmy'],
                    "data_oferty": extracted_info['data_oferty'],
                    "numer_oferty": extracted_info['numer_oferty'],
                    "pojazd": {
                        **extracted_info['pojazd'],
                        **db_vehicle_info  # Dodanie dodatkowych informacji z bazy
                    },
                    "zabudowa": extracted_info['zabudowa'],
                    "agregat": extracted_info['agregat'],
                    "montaz": extracted_info['montaz'],
                    "cena_calkowita_netto": extracted_info['cena_calkowita_netto']
                }
                
                logger.info(f"Wygenerowano ofertę: {json.dumps(offer_data, indent=2, ensure_ascii=False)}")
                
                # Generowanie PDF
                pdf_path = self._generate_pdf(offer_data)
                return offer_data, pdf_path
                
            except Exception as e:
                logger.error(f"Błąd podczas przetwarzania danych: {str(e)}")
                logger.error(f"Szczegóły błędu:\n{traceback.format_exc()}")
                return None, None
            
        except Exception as e:
            logger.error(f"Błąd podczas generowania oferty: {str(e)}")
            logger.error(f"Szczegóły błędu:\n{traceback.format_exc()}")
            st.error(f"Wystąpił błąd: {str(e)}")
            return None, None

    def _generate_pdf(self, offer_data) -> str:
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

        def sanitize_dict(d):
            """Rekurencyjnie usuwa polskie znaki ze słownika"""
            if isinstance(d, dict):
                return {k: sanitize_dict(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [sanitize_dict(x) for x in d]
            elif isinstance(d, str):
                return remove_pl_chars(d)
            return d

        try:
            # Usuwanie polskich znaków z całej struktury danych
            sanitized_data = sanitize_dict(offer_data)

            # Tworzenie dokumentu z szablonu
            pdf = OfferTemplate()
            
            # Ustawienie danych stopki
            pdf.set_footer_data(
                data_oferty=sanitized_data.get('data_oferty', ''),
                numer_oferty=sanitized_data.get('numer_oferty', '')
            )
            
            # Sekcje z tekstem
            pdf.create_section('Dane firmy', sanitized_data['dane_firmy'])
            pdf.create_section('Informacje o pojezdzie', sanitized_data['pojazd'])
            
            # Przygotowanie danych zabudowy
            zabudowa_data = sanitized_data['zabudowa'].copy()
            if 'material_izolacyjny' in zabudowa_data:
                material = zabudowa_data['material_izolacyjny']
                zabudowa_data['material_izolacyjny'] = f"{material['typ']}, {material['grubosc']}"
            
            pdf.create_section('Zabudowa izotermiczna', zabudowa_data)
            
            # Przygotowanie danych agregatu
            agregat_data = {k: v for k, v in sanitized_data['agregat'].items() if 'cena' not in k.lower()}
            pdf.create_section('Agregat', agregat_data)
            
            # Przygotowanie danych montażu
            montaz_data = {}
            if 'mocowanie_sprezarka' in sanitized_data['montaz']:
                montaz_data['Mocowanie sprezarki'] = sanitized_data['montaz']['mocowanie_sprezarka']['opis']
            if 'montaz_agregatu' in sanitized_data['montaz']:
                montaz_data['Montaz agregatu'] = 'Tak'
            
            pdf.create_section('Montaz', montaz_data)
            
            # Sekcja kosztów na końcu
            pdf.create_section('Podsumowanie kosztow', {
                'Cena calkowita netto': f"{sanitized_data['cena_calkowita_netto']} PLN"
            })
            
            # Dodaj zdjęcia w prawej kolumnie
            if 'offer_images' in st.session_state and st.session_state['offer_images']:
                pdf.add_images_column(st.session_state['offer_images'])

            # Zapisanie PDF
            pdf_path = f"temp/oferta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            pdf.output(pdf_path)
            
            # Usuwamy czyszczenie zdjęć, bo są stałe
            return pdf_path
            
        except Exception as e:
            logger.error(f"Błąd podczas generowania PDF: {str(e)}")
            logger.error(f"Szczegóły błędu:\n{traceback.format_exc()}")
            raise


class OfferTemplate(FPDF):
    def __init__(self):
        # Najpierw definiujemy wszystkie stałe
        self.header_height = 40  # Wysokość nagłówka
        self.top_margin_after_header = 5  # Dodatkowy margines po nagłówku
        self.footer_height = 20
        self.content_width = 120
        self.image_x = 140
        self.image_width = 60
        
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
        self.set_y(-25)  # 25mm od dołu strony
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
        self.set_fill_color(158, 197, 215)  # Jasny niebieski
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
            for key, value in content.items():
                # Pomijamy wyświetlanie ceny i id
                if (title != 'Podsumowanie kosztow' and ('cena' in key.lower() or 'koszt' in key.lower())) or key.lower() == 'id':
                    continue
                    
                formatted_key = key.replace('_', ' ').title()
                
                # Formatowanie wartości słownikowych
                if isinstance(value, dict):
                    if 'typ' in value and 'grubosc' in value:
                        value = f"{value['typ']}, {value['grubosc']}"
                    elif 'opis' in value:
                        value = value['opis']
                    else:
                        value = ', '.join(f"{k}: {v}" for k, v in value.items() if title == 'Podsumowanie kosztow' or 'cena' not in k.lower())
                
                # Formatowanie list
                elif isinstance(value, list):
                    value = ', '.join(str(item) for item in value)
                
                self.multi_cell(self.content_width - 10, 6, f"{formatted_key}: {value}")
        else:
            self.multi_cell(self.content_width - 10, 6, str(content))
        
        # Przywróć standardowy margines
        self.set_right_margin(10)
        return self.get_y() - start_y  # Zwróć wysokość sekcji

    def add_images_column(self, images):
        """Dodaje kolumnę zdjęć po prawej stronie"""
        if not images:
            return
            
        current_y = 70  # Początkowa pozycja Y (pod nagłówkiem)
        
        for img_path in images:
            if os.path.exists(img_path):
                # Sprawdź czy jest miejsce na stronie
                if current_y + self.image_width > self.page_break_trigger:
                    self.add_page()
                    current_y = 70
                
                # Dodaj zdjęcie
                self.image(img_path, self.image_x, current_y, self.image_width)
                current_y += self.image_width  # Dodaj odstęp między zdjęciami 