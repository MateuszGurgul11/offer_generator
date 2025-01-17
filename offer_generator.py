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

def calculate_attachments_cost(prefix="", render_ui=True):
    """Oblicza koszt dodatkowego wyposażenia i zapisuje wybrane opcje w session_state"""
    total_cost = 0
    selected_options = {}
    
    with st.sidebar:
        st.header("Dodatkowe wyposażenie")
        
        # Sekcja: Izolacja
        st.subheader("Izolacja")
        if st.checkbox("Izoterma 0st.C", value=False, key=f"{prefix}izoterma_0st_c"):
            total_cost += 100
            selected_options['izoterma_0st_c'] = True
        if st.checkbox("Chłodnia -20st.C", value=False, key=f"{prefix}chlodnia_-20st_c"):
            total_cost += 100
            selected_options['chlodnia_-20st_c'] = True
        if st.checkbox("Atest PZH", value=False, key=f"{prefix}atest_pzh"):
            total_cost += 100
            selected_options['atest_pzh'] = True

        # Sekcja: Materiały
        st.subheader("Materiały")
        materiał_izolacyjny = st.checkbox("Materiał izolacyjny", key=f"{prefix}material_izolacyjny")
        if materiał_izolacyjny:
            selected_options['material_izolacyjny'] = True
            if st.checkbox("Pianka poliuretanowa 40mm", key=f"{prefix}pianka_40mm"):
                total_cost += 100
                selected_options['pianka_40mm'] = True
            if st.checkbox("Pianka poliuretanowa 80mm", key=f"{prefix}pianka_80mm"):
                total_cost += 100
                selected_options['pianka_80mm'] = True

        # Sekcja: Wykończenie
        st.subheader("Wykończenie")
        if st.checkbox("Ściany, sufity: laminat gładki biały", key=f"{prefix}laminat_bialy"):
            total_cost += 100
            selected_options['laminat_bialy'] = True

        # Sekcja: Podłoga
        st.subheader("Podłoga")
        podloga = st.checkbox("Podłoga", key=f"{prefix}podloga")
        if podloga:
            selected_options['podloga'] = True
            if st.checkbox("Wylewka antypoślizgowa", key=f"{prefix}wylewka_anty_slizgowa"):
                total_cost += 100
                selected_options['wylewka_anty_slizgowa'] = True
            if st.checkbox("Blacha aluminiowa ryflowana", key=f"{prefix}blacha_ryflowana"):
                total_cost += 100
                selected_options['blacha_ryflowana'] = True

        # Sekcja: Listwy
        st.subheader("Listwy")
        listwa_przypodlogowa = st.checkbox("Listwa przypodłogowa na ścianach", key=f"{prefix}listwa_przypodlogowa")
        if listwa_przypodlogowa:
            selected_options['listwa_przypodlogowa'] = True
            if st.checkbox("Aluminiowa biała", key=f"{prefix}aluminiowa_biala"):
                total_cost += 100
                selected_options['aluminiowa_biala'] = True
            if st.checkbox("Aluminiowa srebrna", key=f"{prefix}aluminiowa_srebrna"):
                total_cost += 100
                selected_options['aluminiowa_srebrna'] = True
            if st.checkbox("Stal nierdzewna", key=f"{prefix}stal_nierdzewna"):
                total_cost += 100
                selected_options['stal_nierdzewna'] = True
            if st.checkbox("Blacha aluminiowa ryflowana", key=f"{prefix}blacha_ryflowana"):
                total_cost += 100
                selected_options['blacha_ryflowana'] = True
            if st.checkbox("Brak", key=f"{prefix}brak"):
                total_cost += 0
                selected_options['brak'] = True

        # Sekcja: Oświetlenie
        st.subheader("Oświetlenie")
        if st.checkbox("Oświetlenie LED standard (01702)", key=f"{prefix}oswietlenie_led_standard"):
            total_cost += 100
            selected_options['oswietlenie_led_standard'] = True
        if st.checkbox("Oświetlenie LED wzmocnione (01660)", key=f"{prefix}oswietlenie_led_wzmocnione"):
            total_cost += 100
            selected_options['oswietlenie_led_wzmocnione'] = True

        # Sekcja: Drzwi
        st.subheader("Drzwi")
        drzwi_boczne = st.checkbox("Drzwi boczne", key=f"{prefix}drzwi_boczne")
        if drzwi_boczne:
            selected_options['drzwi_boczne'] = True
            if st.checkbox("Wewnętrzne", key=f"{prefix}drzwi_boczne_wewnetrzne"):
                total_cost += 100
                selected_options['drzwi_boczne_wewnetrzne'] = True
            if st.checkbox("Normalnie otwierane", key=f"{prefix}drzwi_boczne_normalnie"):
                total_cost += 100
                selected_options['drzwi_boczne_normalnie'] = True
            if st.checkbox("Brak", key=f"{prefix}brak"):
                total_cost += 0
                selected_options['brak'] = True

        if st.checkbox("Drzwi tylne grube", key=f"{prefix}drzwi_tylne_grube"):
            total_cost += 100
            selected_options['drzwi_tylne_grube'] = True
        if st.checkbox("Futryna drzwi tylnych", key=f"{prefix}futryna_drzwi_tylnych"):
            total_cost += 100
            selected_options['futryna_drzwi_tylnych'] = True

        # Sekcja: Nadkola
        st.subheader("Nadkola")
        nadkola = st.checkbox("Nadkola", key=f"{prefix}nadkola")
        if nadkola:
            selected_options['nadkola'] = True
            if st.checkbox("Odlew z laminatu", key=f"{prefix}nadkola_odlew_laminat"):
                total_cost += 100
                selected_options['nadkola_odlew_laminat'] = True
            if st.checkbox("Kwadratowe wzmocnienie kątownikami", key=f"{prefix}nadkola_wzmocnienie"):
                total_cost += 100
                selected_options['nadkola_wzmocnienie'] = True
            if st.checkbox("Blacha aluminiowa ryflowana", key=f"{prefix}nadkola_blacha_ryflowana"):
                total_cost += 100
                selected_options['nadkola_blacha_ryflowana'] = True

        # Sekcja: Inne
        st.subheader("Inne")
        if st.checkbox("Listwa airline", key=f"{prefix}listwa_airline"):
            total_cost += 100
            selected_options['listwa_airline'] = True
        if st.checkbox("Drążek rozporowy", key=f"{prefix}drazek_rozporowy"):
            total_cost += 100
            selected_options['drazek_rozporowy'] = True
        if st.checkbox("Przygotowanie do montażu agregatu chłodniczego", key=f"{prefix}przygotowanie_agregatu"):
            total_cost += 100
            selected_options['przygotowanie_agregatu'] = True

        inne = st.text_input("Inne (opisz)", key=f"{prefix}inne")
        if inne:
            selected_options['inne'] = inne

        # Podsumowanie
        st.subheader("Podsumowanie")
        st.write(f"Koszt dodatkowego wyposażenia: {total_cost} zł")

    # Zapisz wybrane opcje w session_state
    if render_ui:
        st.session_state['selected_attachments'] = selected_options
        st.session_state['attachments_cost'] = total_cost
    
    return total_cost

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

            # Dodaj koszt dodatkowego wyposażenia
            if 'attachments_cost' in st.session_state:
                total += st.session_state['attachments_cost']
            
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
                "dane_klienta": {{
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
                
                # Dodaj koszt dodatkowego wyposażenia do ceny całkowitej
                if 'attachments_cost' in st.session_state:
                    extracted_info['cena_calkowita_netto'] = (
                        float(extracted_info.get('cena_calkowita_netto', 0)) + 
                        float(st.session_state['attachments_cost'])
                    )
                
                # Tworzenie finalnej oferty
                offer_data = {
                    "dane_klienta": extracted_info['dane_klienta'],
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
                    "cena_calkowita_netto": extracted_info['cena_calkowita_netto']
                }
                
                # Dodaj informacje o wybranym dodatkowym wyposażeniu
                if 'selected_attachments' in st.session_state:
                    offer_data['dodatkowe_wyposazenie'] = st.session_state['selected_attachments']
                
                logger.info(f"Wygenerowano ofertę: {json.dumps(offer_data, indent=2, ensure_ascii=False)}")
                
                # Sprawdzenie wymaganych danych
                missing_data = []
                
                # Sprawdź dane klienta
                required_company_data = ['nazwa', 'adres', 'nip']
                for field in required_company_data:
                    if not offer_data.get('dane_klienta', {}).get(field):
                        missing_data.append(f"Dane Klienta - {field}")
                
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
            
            chars_map = {
                'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 
                'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
                'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N', 
                'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z'
            }
            
            for pl, en in chars_map.items():
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
                'dane_klienta': {remove_pl_chars(k): remove_pl_chars(v) for k, v in offer_data['dane_klienta'].items()},
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
            pdf.create_section('Dane Klienta', sanitized_data['dane_klienta'])
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
            
            # Dodaj sekcję dodatkowego wyposażenia
            if 'selected_attachments' in st.session_state and st.session_state['selected_attachments']:
                # Sanityzacja nazw wyposażenia
                sanitized_attachments = {
                    remove_pl_chars(k): 'Tak' 
                    for k, v in st.session_state['selected_attachments'].items() if v
                }
                pdf.create_section(remove_pl_chars('Dodatkowe wyposazenie'), sanitized_attachments)
                
                # Dodaj koszt dodatkowego wyposażenia do sekcji kosztów
                if 'attachments_cost' in st.session_state:
                    koszty_data[remove_pl_chars('Dodatkowe wyposazenie')] = f"{float(st.session_state['attachments_cost']):.2f} PLN"
            
            # Sanityzacja sekcji kosztów
            sanitized_koszty = {remove_pl_chars(k): v for k, v in koszty_data.items()}
            pdf.create_section(remove_pl_chars('Szczegoly kosztow'), sanitized_koszty)
            
            # Obliczanie i wyświetlanie sumy
            total_cost = sum([
                float(offer_data['pojazd'].get('zabudowa_cena') or 0),
                float(offer_data['pojazd'].get('sklejki_cena') or 0),
                float(offer_data['pojazd'].get('nadkola_cena') or 0),
                float(offer_data['agregat'].get('cena_cennikowa') or 0),
                float(offer_data.get('grzanie', {}).get('cena') or 0),
                float(offer_data.get('zestaw_podgrzewacza', {}).get('cena') or 0)
            ])
            
            # Dodaj koszt dodatkowego wyposażenia do sumy
            if 'attachments_cost' in st.session_state:
                total_cost += float(st.session_state['attachments_cost'])
            
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
        
        # Inicjalizacja z obsługą UTF-8
        super().__init__()
        self.set_auto_page_break(auto=True, margin=25)
        self.add_page()
        self.set_margins(10, 10, 10)
        
        # Włącz obsługę UTF-8
        self.set_font('Arial', '', 12)
        
        # Dane do stopki (bez polskich znaków)
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
        def remove_pl_chars(text):
            """Usuwa polskie znaki z tekstu"""
            if not isinstance(text, str):
                text = str(text)
            
            chars_map = {
                'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 
                'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
                'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N', 
                'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z'
            }
            
            for pl, en in chars_map.items():
                text = text.replace(pl, en)
            return text

        # Sanityzacja tytułu i zawartości
        title = remove_pl_chars(title)
        
        if isinstance(content, dict):
            content = {remove_pl_chars(k): remove_pl_chars(str(v)) for k, v in content.items()}
        else:
            content = remove_pl_chars(str(content))
            
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