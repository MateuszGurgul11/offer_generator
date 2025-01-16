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

def calculate_total_cost():
    """Oblicza cenę całkowitą na podstawie aktualnych danych w tabelkach"""
    try:
        total = 0.0
        
        # Koszty pojazdu
        if 'data_dane_pojazdu_grid' in st.session_state:
            pojazd_df = st.session_state['data_dane_pojazdu_grid']
            for _, row in pojazd_df.iterrows():
                if 'cena' in row['Pole'].lower():
                    try:
                        value = row['Wartość'].replace('zł', '').strip()
                        if value:
                            total += float(value)
                    except (ValueError, TypeError):
                        logger.warning(f"Nie można przekonwertować wartości: {row['Wartość']}")
        
        # Koszt agregatu
        if 'data_agregat_grid' in st.session_state:
            agregat_df = st.session_state['data_agregat_grid']
            cena_row = agregat_df[agregat_df['Pole'] == 'cena_cennikowa']
            if not cena_row.empty:
                try:
                    value = cena_row.iloc[0]['Wartość'].replace('zł', '').strip()
                    if value:
                        total += float(value)
                except (ValueError, TypeError):
                    logger.warning(f"Nie można przekonwertować ceny agregatu: {cena_row.iloc[0]['Wartość']}")
        
        # Koszt grzania
        if 'data_grzanie_grid' in st.session_state:
            grzanie_df = st.session_state['data_grzanie_grid']
            cena_row = grzanie_df[grzanie_df['Pole'] == 'cena']
            if not cena_row.empty:
                try:
                    value = cena_row.iloc[0]['Wartość'].replace('zł', '').strip()
                    if value:
                        total += float(value)
                except (ValueError, TypeError):
                    logger.warning(f"Nie można przekonwertować ceny grzania: {cena_row.iloc[0]['Wartość']}")
        
        # Koszt zestawu podgrzewacza
        if 'data_zestaw_podgrzewacza_grid' in st.session_state:
            zestaw_df = st.session_state['data_zestaw_podgrzewacza_grid']
            cena_row = zestaw_df[zestaw_df['Pole'] == 'cena']
            if not cena_row.empty:
                try:
                    value = cena_row.iloc[0]['Wartość'].replace('zł', '').strip()
                    if value:
                        total += float(value)
                except (ValueError, TypeError):
                    logger.warning(f"Nie można przekonwertować ceny zestawu: {cena_row.iloc[0]['Wartość']}")
        
        logger.info(f"Obliczona cena całkowita: {total}")
        return total
        
    except Exception as e:
        logger.error(f"Błąd podczas obliczania ceny całkowitej: {str(e)}")
        return 0.0

def create_editable_grid(data, key, title):
    """Tworzy edytowalną tabelkę AgGrid"""
    try:
        gb = GridOptionsBuilder.from_dataframe(data)
        gb.configure_default_column(
            editable=True,
            resizable=True,
            sorteable=True,
            filterable=True
        )
        gb.configure_grid_options(domLayout='normal')
        gb.configure_selection('single')
        grid_options = gb.build()
        
        st.write(f"### {title}")
        grid_response = AgGrid(
            data,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.VALUE_CHANGED,
            fit_columns_on_grid_load=True,
            allow_unsafe_jscode=True,
            key=key
        )
        
        # Aktualizacja danych w sesji
        st.session_state[f'data_{key}'] = grid_response['data']
        
        # Aktualizacja ceny całkowitej po każdej edycji
        if any('cena' in str(col).lower() for col in data['Pole']):
            total_cost = calculate_total_cost()
            if 'data_szczegoly_grid' in st.session_state:
                szczegoly_df = st.session_state['data_szczegoly_grid']
                szczegoly_df.loc[szczegoly_df['Pole'] == 'Cena calkowita netto', 'Wartość'] = f"{total_cost:.2f} zł"
                st.session_state['data_szczegoly_grid'] = szczegoly_df
        
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
    """Zapisuje dane oferty do sesji"""
    try:
        # Dane firmy
        dane_firmy_data = [
            {'Pole': 'nazwa', 'Wartość': str(offer_data['dane_firmy'].get('nazwa', ''))},
            {'Pole': 'adres', 'Wartość': str(offer_data['dane_firmy'].get('adres', ''))},
            {'Pole': 'nip', 'Wartość': str(offer_data['dane_firmy'].get('nip', ''))},
            {'Pole': 'osoba_odpowiedzialna', 'Wartość': str(offer_data['dane_firmy'].get('osoba_odpowiedzialna', ''))},
            {'Pole': 'telefon', 'Wartość': str(offer_data['dane_firmy'].get('telefon', ''))},
            {'Pole': 'email', 'Wartość': str(offer_data['dane_firmy'].get('email', ''))}
        ]
        st.session_state['data_dane_firmy_grid'] = pd.DataFrame(dane_firmy_data)
        
        # Dane pojazdu
        pojazd = offer_data.get('pojazd', {})
        pojazd_data = [
            {'Pole': 'marka', 'Wartość': str(pojazd.get('marka', ''))},
            {'Pole': 'model', 'Wartość': str(pojazd.get('model', ''))},
            {'Pole': 'kubatura', 'Wartość': str(pojazd.get('kubatura', ''))},
            {'Pole': 'zabudowa_cena', 'Wartość': f"{str(pojazd.get('zabudowa_cena', '0'))} zł"},
            {'Pole': 'sklejki_cena', 'Wartość': f"{str(pojazd.get('sklejki_cena', '0'))} zł"},
            {'Pole': 'nadkola_cena', 'Wartość': f"{str(pojazd.get('nadkola_cena', '0'))} zł"}
        ]
        st.session_state['data_dane_pojazdu_grid'] = pd.DataFrame(pojazd_data)
        
        # Dane agregatu
        agregat = offer_data.get('agregat', {})
        agregat_data = [
            {'Pole': 'model', 'Wartość': str(agregat.get('model', ''))},
            {'Pole': 'daikin_product_line', 'Wartość': str(agregat.get('daikin_product_line', ''))},
            {'Pole': 'refrigerant', 'Wartość': str(agregat.get('refrigerant', ''))},
            {'Pole': 'instalacja_elektryczna', 'Wartość': str(agregat.get('instalacja_elektryczna', ''))},
            {'Pole': 'tylko_drogowy', 'Wartość': str(agregat.get('tylko_drogowy', ''))},
            {'Pole': 'drogowy_siec_230V', 'Wartość': str(agregat.get('drogowy_siec_230V', ''))},
            {'Pole': 'drogowy_siec_400V', 'Wartość': str(agregat.get('drogowy_siec_400V', ''))},
            {'Pole': 'cena_cennikowa', 'Wartość': f"{str(agregat.get('cena_cennikowa', '0'))} zł"},
            {'Pole': 'cooling_capacity_0C', 'Wartość': str(agregat.get('cooling_capacity_0C', ''))},
            {'Pole': 'cooling_capacity_-20C', 'Wartość': str(agregat.get('cooling_capacity_-20C', ''))},
            {'Pole': 'recommended_van_size_0C', 'Wartość': str(agregat.get('recommended_van_size_0C', ''))},
            {'Pole': 'recommended_van_size_-20C', 'Wartość': str(agregat.get('recommended_van_size_-20C', ''))},
            {'Pole': 'uwagi', 'Wartość': str(agregat.get('uwagi', ''))},
            {'Pole': 'temperature_range', 'Wartość': str(agregat.get('temperature_range', ''))}
        ]
        st.session_state['data_agregat_grid'] = pd.DataFrame(agregat_data)
        
        # Dane grzania
        if 'grzanie' in offer_data and offer_data['grzanie']:
            grzanie = offer_data['grzanie']
            grzanie_data = [
                {'Pole': 'model_jednostki', 'Wartość': str(grzanie.get('model_jednostki', ''))},
                {'Pole': 'model_opcji', 'Wartość': str(grzanie.get('model_opcji', ''))},
                {'Pole': 'cena', 'Wartość': f"{str(grzanie.get('cena', '0'))} zł"}
            ]
            st.session_state['data_grzanie_grid'] = pd.DataFrame(grzanie_data)
        
        # Dane zestawu podgrzewacza
        if 'zestaw_podgrzewacza' in offer_data and offer_data['zestaw_podgrzewacza']:
            zestaw = offer_data['zestaw_podgrzewacza']
            zestaw_data = [
                {'Pole': 'Grzatki elektryczne', 'Wartość': str(zestaw.get('grzatki_elektryczne', ''))},
                {'Pole': 'Model opcji', 'Wartość': str(zestaw.get('model_opcji', ''))},
                {'Pole': 'cena', 'Wartość': f"{str(zestaw.get('cena', '0'))} zł"}
            ]
            st.session_state['data_zestaw_podgrzewacza_grid'] = pd.DataFrame(zestaw_data)
        
        # Szczegóły oferty
        szczegoly_data = [
            {'Pole': 'Data oferty', 'Wartość': str(offer_data.get('data_oferty', ''))},
            {'Pole': 'Numer oferty', 'Wartość': str(offer_data.get('numer_oferty', ''))},
            {'Pole': 'Cena calkowita netto', 'Wartość': f"{str(offer_data.get('cena_calkowita_netto', '0'))} zł"}
        ]
        st.session_state['data_szczegoly_grid'] = pd.DataFrame(szczegoly_data)
        
    except Exception as e:
        logger.error(f"Błąd podczas zapisywania danych do sesji: {str(e)}")
        logger.error(f"Szczegóły błędu:\n{traceback.format_exc()}")
        st.error("Wystąpił błąd podczas zapisywania danych")

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
        
        # Generowanie oferty
        if st.button("Generuj ofertę"):
            logger.info("Rozpoczęto generowanie oferty")
            if offer_text:
                with st.spinner("Generuję ofertę..."):
                    try:
                        db = OfferDatabase()
                        generator = OfferGenerator(db)
                        logger.debug("Inicjalizacja generatora zakończona")
                        
                        offer_data, missing_data = generator.create_offer(offer_text)
                        
                        if offer_data:
                            save_to_session(offer_data)
                            st.session_state['missing_data'] = missing_data
                            st.success("Pomyślnie wygenerowano ofertę!")
                    except Exception as e:
                        logger.error(f"Błąd podczas generowania oferty: {str(e)}")
                        st.error(f"Wystąpił błąd: {str(e)}")
            else:
                st.warning("Proszę wprowadzić treść oferty")

        # Wyświetlanie tabelek (tylko jeśli są dane w sesji)
        if any(key.startswith('data_') for key in st.session_state.keys()):
            st.subheader("Wygenerowana oferta")
            tabs = st.tabs(["Dane firmy", "Pojazd", "Agregat", "Grzanie", "Szczegóły", "PDF"])
            
            with tabs[0]:
                if 'data_dane_firmy_grid' in st.session_state:
                    create_editable_grid(
                        st.session_state['data_dane_firmy_grid'],
                        'dane_firmy_grid',
                        "Dane firmy"
                    )
            
            with tabs[1]:
                if 'data_dane_pojazdu_grid' in st.session_state:
                    create_editable_grid(
                        st.session_state['data_dane_pojazdu_grid'],
                        'dane_pojazdu_grid',
                        "Dane pojazdu"
                    )
            
            with tabs[2]:
                if 'data_agregat_grid' in st.session_state:
                    create_editable_grid(
                        st.session_state['data_agregat_grid'],
                        'agregat_grid',
                        "Agregat"
                    )
            
            with tabs[3]:
                col1, col2 = st.columns(2)
                with col1:
                    if 'data_grzanie_grid' in st.session_state:
                        create_editable_grid(
                            st.session_state['data_grzanie_grid'],
                            'grzanie_grid',
                            "Grzanie"
                        )
                
                with col2:
                    if 'data_zestaw_podgrzewacza_grid' in st.session_state:
                        create_editable_grid(
                            st.session_state['data_zestaw_podgrzewacza_grid'],
                            'zestaw_podgrzewacza_grid',
                            "Zestaw podgrzewacza"
                        )
            
            with tabs[4]:
                if 'data_szczegoly_grid' in st.session_state:
                    create_editable_grid(
                        st.session_state['data_szczegoly_grid'],
                        'szczegoly_grid',
                        "Szczegóły oferty"
                    )
            
            with tabs[5]:
                st.write("### Generowanie PDF")
                
                # Dodaj informację o brakujących danych
                if 'missing_data' in st.session_state and st.session_state['missing_data']:
                    st.warning("Uwaga: Brakujące dane w ofercie:")
                    for field in st.session_state['missing_data']:
                        st.warning(f"- {field}")
                
                # Przyciski do obsługi PDF
                show_pdf_buttons()
                
                # Zdjęcia
                st.subheader("Zdjęcia")
                if 'offer_images' not in st.session_state:
                    st.session_state['offer_images'] = [
                        'images/test1.jpeg',
                        'images/test2.jpeg',
                        'images/test3.jpeg',
                    ]
                
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
        if all(key in st.session_state for key in ['data_dane_firmy_grid', 'data_dane_pojazdu_grid', 'data_agregat_grid']):
            # Konwersja danych z tabelek z powrotem do struktury oferty
            updated_offer = {
                'dane_firmy': dict(zip(
                    st.session_state['data_dane_firmy_grid']['Pole'],
                    st.session_state['data_dane_firmy_grid']['Wartość']
                )),
                'pojazd': dict(zip(
                    st.session_state['data_dane_pojazdu_grid']['Pole'],
                    st.session_state['data_dane_pojazdu_grid']['Wartość'].str.replace(' zł', '')
                )),
                'agregat': dict(zip(
                    st.session_state['data_agregat_grid']['Pole'],
                    st.session_state['data_agregat_grid']['Wartość'].str.replace(' zł', '')
                ))
            }
            
            # Dodaj opcjonalne sekcje jeśli istnieją
            if 'data_grzanie_grid' in st.session_state:
                updated_offer['grzanie'] = dict(zip(
                    st.session_state['data_grzanie_grid']['Pole'],
                    st.session_state['data_grzanie_grid']['Wartość'].str.replace(' zł', '')
                ))
            
            if 'data_zestaw_podgrzewacza_grid' in st.session_state:
                updated_offer['zestaw_podgrzewacza'] = dict(zip(
                    st.session_state['data_zestaw_podgrzewacza_grid']['Pole'],
                    st.session_state['data_zestaw_podgrzewacza_grid']['Wartość'].str.replace(' zł', '')
                ))
            
            # Dodaj szczegóły oferty
            szczegoly = dict(zip(
                st.session_state['data_szczegoly_grid']['Pole'],
                st.session_state['data_szczegoly_grid']['Wartość'].str.replace(' zł', '')
            ))
            updated_offer.update({
                'data_oferty': szczegoly.get('data_oferty', ''),
                'numer_oferty': szczegoly.get('numer_oferty', ''),
                'cena_calkowita_netto': float(szczegoly.get('cena_calkowita_netto', '0'))
            })
            
            return updated_offer
            
    except Exception as e:
        logger.error(f"Błąd podczas aktualizacji oferty: {str(e)}")
        st.error("Nie udało się zaktualizować oferty")
    return None

def show_pdf_buttons():
    """Wyświetla przyciski do obsługi PDF"""
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Generuj PDF z aktualnych danych"):
            try:
                # Pobierz aktualne dane z tabelek
                updated_offer = update_offer_from_grids()
                if updated_offer:
                    # Generowanie nowego PDF
                    generator = OfferGenerator(OfferDatabase())
                    new_pdf_path = generator._generate_pdf(updated_offer, [])  # Puste missing_data
                    
                    if new_pdf_path:
                        st.session_state['last_pdf_path'] = new_pdf_path
                        st.session_state['current_offer'] = updated_offer
                        st.success("PDF został wygenerowany!")
                else:
                    st.error("Nie można wygenerować PDF - brak wymaganych danych")
            except Exception as e:
                logger.error(f"Błąd podczas generowania PDF: {str(e)}")
                st.error("Nie udało się wygenerować PDF")
    
    with col2:
        if 'last_pdf_path' in st.session_state and os.path.exists(st.session_state['last_pdf_path']):
            with open(st.session_state['last_pdf_path'], "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
                st.download_button(
                    label="Pobierz ofertę (PDF)",
                    data=pdf_bytes,
                    file_name=f"oferta_autoadaptacje_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf"
                )

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
