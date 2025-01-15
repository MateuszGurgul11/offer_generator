import os
from dotenv import load_dotenv
import streamlit as st

# Ładowanie zmiennych środowiskowych
load_dotenv()

# Konfiguracja ścieżek dla Streamlit Cloud
if os.getenv('STREAMLIT_RUNTIME'):
    BASE_DIR = '/mount/src/offer_generator/Offer_generator'
else:
    # Lokalna ścieżka
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

IMAGES_DIR = os.path.join(BASE_DIR, 'images')

# Utwórz folder images jeśli nie istnieje
if not os.path.exists(IMAGES_DIR):
    try:
        os.makedirs(IMAGES_DIR)
        print(f"Utworzono katalog: {IMAGES_DIR}")
    except Exception as e:
        print(f"Nie można utworzyć katalogu {IMAGES_DIR}: {str(e)}")
else:
    print(f"Katalog już istnieje: {IMAGES_DIR}")

# Wyświetl informacje o ścieżkach
print(f"BASE_DIR: {BASE_DIR}")
print(f"IMAGES_DIR: {IMAGES_DIR}")

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
