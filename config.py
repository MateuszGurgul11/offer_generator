import os
import streamlit as st

# Próba załadowania zmiennych środowiskowych z pliku .env

# Próba pobrania klucza API z różnych źródeł
OPENAI_API_KEY = (
    st.secrets.get("OPENAI_API_KEY") or  # Z sekretów Streamlit
    None  # Jeśli nie znaleziono
)

if not OPENAI_API_KEY:
    st.error("""
    Brak klucza API OpenAI. 
    1. Utwórz plik .env w głównym katalogu projektu
    2. Dodaj linię: OPENAI_API_KEY=sk-twój_klucz_api
    lub
    Dodaj klucz w ustawieniach Streamlit Cloud
    """) 
