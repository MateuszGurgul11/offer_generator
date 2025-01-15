import streamlit as st
from database import OfferDatabase
from offer_generator import OfferGenerator
import os
import json
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
import pandas as pd
import logging
import sys
import traceback
from datetime import datetime

# Konfiguracja logowania
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def create_editable_grid(data, key, title):
    """Tworzy edytowalną tabelkę AgGrid z zachowaniem stanu"""
    try:
        # Używamy stałego klucza dla każdej tabelki
        session_key = f"data_{key}"
        
        # Inicjalizacja danych w sesji tylko jeśli nie istnieją
        if session_key not in st.session_state:
            if isinstance(data, dict):
                df = pd.DataFrame([
                    {'Pole': k, 'Wartość': v} for k, v in data.items()
                ])
            else:
                df = pd.DataFrame(data)
            st.session_state[session_key] = df
        
        # Konfiguracja opcji tabelki
        gb = GridOptionsBuilder.from_dataframe(st.session_state[session_key])
        gb.configure_default_column(
            editable=True,
            resizable=True,
            sorteable=True,
            filterable=True
        )
        gb.configure_grid_options(domLayout='normal')
        gb.configure_selection('single')
        grid_options = gb.build()
        
        st.subheader(title)
        grid_response = AgGrid(
            st.session_state[session_key],
            gridOptions=grid_options,
            update_mode=GridUpdateMode.VALUE_CHANGED,
            fit_columns_on_grid_load=True,
            allow_unsafe_jscode=True,
            key=key
        )
        
        # Aktualizacja danych w sesji
        st.session_state[session_key] = grid_response['data']
        
        return grid_response['data']
        
    except Exception as e:
        logger.error(f"Błąd podczas tworzenia tabelki {title}: {str(e)}")
        st.error(f"Wystąpił błąd podczas tworzenia tabelki: {str(e)}")
        return pd.DataFrame()

def clear_session_data():
    """Czyści dane sesji związane z tabelkami"""
    keys_to_clear = ['dane_firmy_new', 'dane_pojazdu_new', 'adaptacje_new', 'szczegoly_new']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

def save_to_session(offer_data):
    """Zapisuje dane oferty do sesji z odpowiednimi typami danych"""
    if offer_data:
        st.session_state['current_offer'] = offer_data
        
        # Dane firmy
        if 'dane_firmy' in offer_data:
            dane_firmy_data = [
                {'Pole': k, 'Wartość': str(v)} 
                for k, v in offer_data['dane_firmy'].items()
            ]
            st.session_state['data_dane_firmy_grid'] = pd.DataFrame(dane_firmy_data)
        
        # Dane pojazdu
        if 'pojazd' in offer_data:
            dane_pojazdu_data = [
                {'Pole': k, 'Wartość': str(v)} 
                for k, v in offer_data['pojazd'].items()
            ]
            st.session_state['data_dane_pojazdu_grid'] = pd.DataFrame(dane_pojazdu_data)
        
        # Dane zabudowy
        if 'zabudowa' in offer_data:
            zabudowa = offer_data['zabudowa']
            zabudowa_data = []
            
            # Podstawowe pola
            basic_fields = ['typ', 'temperatura', 'cena_netto']
            for field in basic_fields:
                zabudowa_data.append({
                    'Pole': field,
                    'Wartość': str(zabudowa.get(field, ''))
                })
            
            # Materiał izolacyjny
            if 'material_izolacyjny' in zabudowa:
                material = zabudowa['material_izolacyjny']
                zabudowa_data.append({
                    'Pole': 'material_izolacyjny',
                    'Wartość': f"typ: {material.get('typ', '')}, grubość: {material.get('grubosc', '')}"
                })
            
            # Pozostałe pola
            other_fields = ['sciany_sufit', 'podloga']
            for field in other_fields:
                zabudowa_data.append({
                    'Pole': field,
                    'Wartość': str(zabudowa.get(field, ''))
                })
            
            # Wykonczenia
            wykonczenia = zabudowa.get('wykonczenia', [])
            if isinstance(wykonczenia, list):
                wykonczenia_str = ', '.join(wykonczenia)
            else:
                wykonczenia_str = str(wykonczenia)
            zabudowa_data.append({
                'Pole': 'wykonczenia',
                'Wartość': wykonczenia_str
            })
            
            st.session_state['data_zabudowa_grid'] = pd.DataFrame(zabudowa_data)
        
        # Dane agregatu
        if 'agregat' in offer_data:
            agregat = offer_data['agregat']
            agregat_data = [
                {'Pole': 'model', 'Wartość': str(agregat.get('model', ''))},
                {'Pole': 'typ', 'Wartość': str(agregat.get('typ', ''))},
                {'Pole': 'czynnik', 'Wartość': str(agregat.get('czynnik', ''))},
                {'Pole': 'cena_netto', 'Wartość': f"{str(agregat.get('cena_netto', '0'))} zł"}
            ]
            st.session_state['data_agregat_grid'] = pd.DataFrame(agregat_data)
        
        # Dane montażu
        if 'montaz' in offer_data:
            montaz = offer_data['montaz']
            montaz_data = []
            
            # Mocowanie sprężarki
            if 'mocowanie_sprezarka' in montaz:
                mocowanie = montaz['mocowanie_sprezarka']
                montaz_data.append({
                    'Pole': 'mocowanie_sprezarka',
                    'Wartość': f"opis: {mocowanie.get('opis', '')}, cena: {mocowanie.get('cena_netto', '0')} zł"
                })
            
            # Montaż agregatu
            if 'montaz_agregatu' in montaz:
                montaz_data.append({
                    'Pole': 'montaz_agregatu',
                    'Wartość': f"cena: {montaz['montaz_agregatu'].get('cena_netto', '0')} zł"
                })
            
            st.session_state['data_montaz_grid'] = pd.DataFrame(montaz_data)
        
        # Szczegóły oferty
        szczegoly_data = [
            {'Pole': 'data_oferty', 'Wartość': str(offer_data.get('data_oferty', ''))},
            {'Pole': 'numer_oferty', 'Wartość': str(offer_data.get('numer_oferty', ''))},
            {'Pole': 'cena_calkowita_netto', 'Wartość': f"{str(offer_data.get('cena_calkowita_netto', '0'))} zł"}
        ]
        st.session_state['data_szczegoly_grid'] = pd.DataFrame(szczegoly_data)

def load_from_session():
    """Ładuje dane oferty z sesji"""
    if 'current_offer' in st.session_state:
        return st.session_state['current_offer']
    return None

def main():
    st.set_page_config(
        page_title="AutoAdaptacje",
        page_icon="🚗",
        layout="wide"
    )
    try:
        logger.info("Uruchamianie aplikacji")
        
        st.title("🏢 Generator ofert")
        
        # Pole tekstowe do wprowadzania treści oferty
        offer_text = st.text_area(
            "Wprowadź treść oferty",
            height=300,
            key="offer_input"
        )
        
        if st.button("Generuj ofertę"):
            logger.info("Rozpoczęto generowanie oferty")
            if offer_text:
                with st.spinner("Generuję ofertę..."):
                    try:
                        db = OfferDatabase()
                        generator = OfferGenerator(db)
                        logger.debug("Inicjalizacja generatora zakończona")
                        
                        offer_data, pdf_path = generator.create_offer(offer_text)
                        if offer_data and pdf_path:
                            save_to_session(offer_data)
                            st.session_state['last_pdf_path'] = pdf_path
                            st.success("Pomyślnie wygenerowano ofertę!")
                    except Exception as e:
                        logger.error(f"Błąd podczas generowania oferty: {str(e)}")
                        st.error(f"Wystąpił błąd: {str(e)}")
            else:
                st.warning("Proszę wprowadzić treść oferty")

        # Wyświetlanie zapisanych danych
        offer_data = load_from_session()
        if offer_data:
            st.subheader("Wygenerowana oferta")
            tabs = st.tabs(["Dane firmy", "Pojazd", "Zabudowa i agregat", "Szczegóły", "PDF"])
            
            with tabs[0]:
                dane_firmy = create_editable_grid(
                    st.session_state.get('data_dane_firmy_grid', pd.DataFrame()),
                    'dane_firmy_grid',
                    "Dane firmy"
                )
            
            with tabs[1]:
                dane_pojazdu = create_editable_grid(
                    st.session_state.get('data_dane_pojazdu_grid', pd.DataFrame()),
                    'dane_pojazdu_grid',
                    "Dane pojazdu"
                )
            
            with tabs[2]:
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'data_zabudowa_grid' in st.session_state:
                        zabudowa = create_editable_grid(
                            st.session_state['data_zabudowa_grid'],
                            'zabudowa_grid',
                            "Zabudowa"
                        )
                
                with col2:
                    if 'data_agregat_grid' in st.session_state:
                        agregat = create_editable_grid(
                            st.session_state['data_agregat_grid'],
                            'agregat_grid',
                            "Agregat"
                        )
                
                if 'data_montaz_grid' in st.session_state:
                    montaz = create_editable_grid(
                        st.session_state['data_montaz_grid'],
                        'montaz_grid',
                        "Montaż"
                    )
            
            with tabs[3]:
                if 'data_szczegoly_grid' in st.session_state:
                    szczegoly = create_editable_grid(
                        st.session_state['data_szczegoly_grid'],
                        'szczegoly_grid',
                        "Szczegóły oferty"
                    )
            
            with tabs[4]:
                show_pdf_buttons()
                st.subheader("Zdjęcia")
                
                # Ustawiamy stałe zdjęcia z folderu images
                if 'offer_images' not in st.session_state:
                    # Lista stałych zdjęć
                    st.session_state['offer_images'] = [
                        'images/test1.jpeg',
                        'images/test2.jpeg',
                        'images/test3.jpeg',
                    ]
                
                # Wyświetlamy podgląd zdjęć
                cols = st.columns(2)
                for idx, image_path in enumerate(st.session_state['offer_images']):
                    with cols[idx % 2]:
                        st.image(image_path, caption=f"Zdjęcie {idx + 1}")

    except Exception as e:
        logger.error(f"Krytyczny błąd aplikacji: {str(e)}")
        st.error("Wystąpił krytyczny błąd aplikacji")

def update_offer_from_grids():
    """Aktualizuje dane oferty na podstawie edytowanych tabelek"""
    try:
        required_keys = [
            'data_dane_firmy_grid',
            'data_dane_pojazdu_grid',
            'data_zabudowa_grid',
            'data_agregat_grid',
            'data_montaz_grid',
            'data_szczegoly_grid'
        ]
        
        if all(key in st.session_state for key in required_keys):
            # Konwersja danych z tabelek z powrotem do struktury oferty
            dane_firmy = dict(zip(
                st.session_state['data_dane_firmy_grid']['Pole'],
                st.session_state['data_dane_firmy_grid']['Wartość']
            ))
            
            dane_pojazdu = dict(zip(
                st.session_state['data_dane_pojazdu_grid']['Pole'],
                st.session_state['data_dane_pojazdu_grid']['Wartość']
            ))
            
            # Konwersja danych zabudowy
            zabudowa_df = st.session_state['data_zabudowa_grid']
            zabudowa = {}
            for _, row in zabudowa_df.iterrows():
                if row['Pole'] == 'material_izolacyjny':
                    # Parsowanie material_izolacyjny z formatu "typ: X, grubość: Y"
                    material_str = row['Wartość']
                    typ = material_str.split('grubość:')[0].replace('typ:', '').strip()
                    grubosc = material_str.split('grubość:')[1].strip()
                    zabudowa['material_izolacyjny'] = {'typ': typ, 'grubosc': grubosc}
                else:
                    zabudowa[row['Pole']] = row['Wartość']
            
            # Konwersja danych agregatu
            agregat_df = st.session_state['data_agregat_grid']
            agregat = {}
            for _, row in agregat_df.iterrows():
                wartosc = row['Wartość']
                if 'zł' in str(wartosc):
                    wartosc = wartosc.replace(' zł', '')
                agregat[row['Pole']] = wartosc
            
            # Konwersja danych montażu
            montaz_df = st.session_state['data_montaz_grid']
            montaz = {
                'mocowanie_sprezarka': {'opis': '', 'cena_netto': 0},
                'montaz_agregatu': {'cena_netto': 0}
            }
            
            for _, row in montaz_df.iterrows():
                if row['Pole'] == 'mocowanie_sprezarka':
                    opis = row['Wartość'].split('cena:')[0].replace('opis:', '').strip()
                    cena = row['Wartość'].split('cena:')[1].replace('zł', '').strip()
                    montaz['mocowanie_sprezarka'] = {'opis': opis, 'cena_netto': float(cena)}
                elif row['Pole'] == 'montaz_agregatu':
                    cena = row['Wartość'].split('cena:')[1].replace('zł', '').strip()
                    montaz['montaz_agregatu'] = {'cena_netto': float(cena)}
            
            # Konwersja szczegółów oferty
            szczegoly_df = st.session_state['data_szczegoly_grid']
            szczegoly = {}
            for _, row in szczegoly_df.iterrows():
                pole = row['Pole']
                wartosc = row['Wartość']
                if 'zł' in str(wartosc):
                    wartosc = wartosc.replace(' zł', '')
                szczegoly[pole] = wartosc
            
            # Tworzenie zaktualizowanej oferty
            updated_offer = {
                'dane_firmy': dane_firmy,
                'pojazd': dane_pojazdu,
                'zabudowa': zabudowa,
                'agregat': agregat,
                'montaz': montaz,
                'data_oferty': szczegoly.get('data_oferty', ''),
                'numer_oferty': szczegoly.get('numer_oferty', ''),
                'cena_calkowita_netto': float(szczegoly.get('cena_calkowita_netto', '0'))
            }
            
            return updated_offer
            
    except Exception as e:
        logger.error(f"Błąd podczas aktualizacji oferty: {str(e)}")
        logger.error(f"Szczegóły błędu:\n{traceback.format_exc()}")
        st.error("Nie udało się zaktualizować oferty")
    return None

def show_pdf_buttons():
    """Wyświetla przyciski do obsługi PDF"""
    if 'last_pdf_path' in st.session_state:
        # Aktualizacja oferty z najnowszymi danymi
        updated_offer = update_offer_from_grids()
        if updated_offer:
            # Generowanie nowego PDF
            try:
                generator = OfferGenerator(OfferDatabase())
                new_pdf_path = generator._generate_pdf(updated_offer)
                
                with open(new_pdf_path, "rb") as pdf_file:
                    pdf_bytes = pdf_file.read()
                    st.download_button(
                        label="Pobierz ofertę (PDF)",
                        data=pdf_bytes,
                        file_name="oferta_autoadaptacje.pdf",
                        mime="application/pdf"
                    )
                
                # Usuwanie starego pliku PDF
                if os.path.exists(st.session_state['last_pdf_path']):
                    os.unlink(st.session_state['last_pdf_path'])
                
                # Aktualizacja ścieżki w sesji
                st.session_state['last_pdf_path'] = new_pdf_path
                st.session_state['current_offer'] = updated_offer
                
            except Exception as e:
                logger.error(f"Błąd podczas generowania PDF: {str(e)}")
                st.error("Nie udało się wygenerować PDF")
        else:
            st.error("Nie można zaktualizować oferty - brak wymaganych danych")

def show_filters(df):
    with st.container():
        col1, col2, col3 = st.columns(3)
        
        with col1:
            selected_brand = st.multiselect(
                "Filtruj według marki",
                options=sorted(df['marka'].unique()),
                key="filter_brand"
            )
        
        with col2:
            selected_model = st.multiselect(
                "Filtruj według modelu",
                options=sorted(df['model'].unique()),
                key="filter_model"
            )
        
        with col3:
            min_year = st.number_input(
                "Minimalny rok produkcji",
                min_value=int(df['rok_produkcji'].min()),
                max_value=int(df['rok_produkcji'].max()),
                value=int(df['rok_produkcji'].min()),
                key="filter_year"
            )

if __name__ == "__main__":
    main()
