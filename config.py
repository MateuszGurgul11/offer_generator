import os
from dotenv import load_dotenv
import streamlit as st

# Próba załadowania zmiennych środowiskowych z pliku .env
load_dotenv()

# Próba pobrania klucza API z różnych źródeł
OPENAI_API_KEY = (
    os.getenv('OPENAI_API_KEY') or  # Z pliku .env
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