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
                "Marka", "Model", "Kubatura (m³)",
                "Zabudowy izotermiczne Cena (zł netto)",
                "Sklejki Cena (zł netto)",
                "Nadkola sklejka 12mm Cena zł netto"
            FROM samochody
        """)
        
        columns = ["Marka", "Model", "Kubatura (m³)", 
                  "Zabudowy izotermiczne Cena (zł netto)",
                  "Sklejki Cena (zł netto)",
                  "Nadkola sklejka 12mm Cena zł netto"]
        data = cursor.fetchall()

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
    
    # Konfiguracja szerokości kolumn - zaktualizowane nazwy
    gb.configure_column("Marka", width=100)
    gb.configure_column("Model", width=100)
    gb.configure_column("Kubatura (m³)", width=100)
    gb.configure_column("Zabudowy izotermiczne Cena (zł netto)", width=150)
    gb.configure_column("Sklejki Cena (zł netto)", width=150)
    gb.configure_column("Nadkola sklejka 12mm Cena zł netto", width=150)
    
    grid_options = gb.build()
    
    return AgGrid(
        df,
        gridOptions=grid_options,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        height=400,
        key=f"grid_{key_prefix}_{title.lower().replace(' ', '_')}"
    )

def show_statistics(df):
    """Wyświetla statystyki i wykresy"""
    st.subheader("Statystyki")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Liczba pojazdów", len(df))
    
    # Wykres liczby pojazdów według marki
    st.subheader("Liczba pojazdów według marki")
    brand_counts = df['Marka'].value_counts()
    st.bar_chart(brand_counts)
    

def main():
    st.set_page_config(
        page_title="AutoAdaptacje - Panel administracyjny",
        page_icon="assets/favicon.ico",
        layout="wide"
    )
    
    st.image("images/logo.png", width=100)
    st.title("AutoAdaptacje - Statystyki")
    
    # Ładowanie danych
    with st.spinner("Ładowanie danych..."):
        df = load_vehicle_data()
    
    if not df.empty:
        # Zakładki
        tabs = st.tabs(["Baza pojazdów", "Statystyki"])
        
        with tabs[0]:
            # Filtry
            col1, _ = st.columns(2)
            
            with col1:
                selected_brand = st.multiselect(
                    "Filtruj według marki",
                    options=sorted(df['Marka'].unique()),
                    key="filter_brand"
                )
            
            # Aplikowanie filtrów
            filtered_df = df.copy()
            if selected_brand:
                filtered_df = filtered_df[filtered_df['Marka'].isin(selected_brand)]
            
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
