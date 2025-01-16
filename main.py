import streamlit as st
from database import OfferDatabase
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd
import json

def load_vehicle_data():
    """Ładuje wszystkie dane o pojazdach z bazy"""
    db = OfferDatabase()
    try:
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT 
                id, marka, model, rok_produkcji, kubatura, klimatyzacja,
                dostepnosc, ostatnia_aktualizacja
            FROM samochody
        """)
        
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()

        # Konwersja danych do DataFrame
        df = pd.DataFrame(data, columns=columns)
        
        return df
        
    except Exception as e:
        st.error(f"Błąd podczas ładowania danych: {str(e)}")
        return pd.DataFrame()

def create_grid(df, title, key_prefix):
    """Tworzy interaktywną tabelkę AgGrid"""
    st.subheader(title)
    
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        resizable=True,
        filterable=True,
        sorteable=True,
        editable=False
    )
    
    # Konfiguracja szerokości kolumn
    gb.configure_column("id", width=70)
    gb.configure_column("marka", width=100)
    gb.configure_column("model", width=100)
    gb.configure_column("rok_produkcji", width=100)
    gb.configure_column("typ_nadwozia", width=100)
    gb.configure_column("mozliwe_adaptacje", width=300)
    
    grid_options = gb.build()
    
    # Dodanie unikalnego klucza dla każdej tabeli
    grid_key = f"grid_{key_prefix}_{title.lower().replace(' ', '_')}"
    
    return AgGrid(
        df,
        gridOptions=grid_options,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        height=400,
        key=grid_key  # Unikalny klucz dla każdej tabeli
    )

def show_statistics(df):
    """Wyświetla statystyki i wykresy"""
    st.subheader("Statystyki")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Liczba pojazdów", len(df))
        
    
    # Wykres liczby pojazdów według marki
    st.subheader("Liczba pojazdów według marki")
    brand_counts = df['marka'].value_counts()
    st.bar_chart(brand_counts)
    

def main():
    st.set_page_config(
        page_title="AutoAdaptacje - Panel administracyjny",
        page_icon="🚗",
        layout="wide"
    )
    
    st.title("🚗 AutoAdaptacje - Panel administracyjny")
    
    # Ładowanie danych
    with st.spinner("Ładowanie danych..."):
        df = load_vehicle_data()
    
    if not df.empty:
        # Zakładki
        tabs = st.tabs(["Baza pojazdów", "Statystyki"])
        
        with tabs[0]:
            # Filtry
            col1, col2 = st.columns(2)
            
            with col1:
                selected_brand = st.multiselect(
                    "Filtruj według marki",
                    options=sorted(df['marka'].unique()),
                    key="filter_brand"
                )
            
            with col2:
                min_year = st.number_input(
                    "Minimalny rok produkcji",
                    min_value=int(df['rok_produkcji'].min()),
                    max_value=int(df['rok_produkcji'].max()),
                    value=int(df['rok_produkcji'].min()),
                    key="filter_year"
                )
            
            # Aplikowanie filtrów
            filtered_df = df.copy()
            if selected_brand:
                filtered_df = filtered_df[filtered_df['marka'].isin(selected_brand)]
            filtered_df = filtered_df[filtered_df['rok_produkcji'] >= min_year]
            
            # Wyświetlanie danych z unikalnym kluczem
            create_grid(filtered_df, "Baza pojazdów", "main")
            
        with tabs[1]:
            show_statistics(df)
    else:
        st.warning("Brak danych w bazie")
    
    # Stopka
    st.markdown("---")
    st.markdown("Panel administracyjny AutoAdaptacje © 2025")

if __name__ == "__main__":
    main()
