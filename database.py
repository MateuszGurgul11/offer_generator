import sqlite3
import logging
from typing import Optional, List, Dict
import json
import os
import streamlit as st

logger = logging.getLogger(__name__)

class OfferDatabase:
    def __init__(self):
        """Inicjalizacja połączenia z bazą SQLite"""
        try:
            db_path = 'autoadaptacje.db'
            
            # Sprawdź czy plik istnieje
            if not os.path.exists(db_path):
                st.error(f"Brak pliku bazy danych: {db_path}")
                logger.error(f"Brak pliku bazy danych: {db_path}")
            else:
                logger.info(f"Znaleziono plik bazy danych: {db_path}")
            
            self.conn = sqlite3.connect(db_path)
            self.create_tables()
            
            
        except Exception as e:
            logger.error(f"Błąd podczas inicjalizacji bazy SQLite: {str(e)}")
            st.error(f"Błąd podczas inicjalizacji bazy: {str(e)}")
            raise

    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Tworzenie tabel zgodnie z nowym schematem
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "Agregaty Daikin" (
                "Daikin Product Line" TEXT,
                "Model" TEXT,
                "Refrigerant" TEXT,
                "Instalacja elektryczna pojazdu" TEXT,
                "tylko drogowy" TEXT,
                "drogowy + sieć 230V" TEXT,
                "drogowy + sieć 400V" TEXT,
                "Cena cennikowa (PLN)" REAL,
                "Cooling capacity (0°C at 30°amb) [W]" REAL,
                "Cooling capacity W (-20°C at 30°amb) [W]-20C" REAL,
                "Recommended Van size for 0°C [m3]" REAL,
                "Recommended Van size for -20°C [m3]" REAL,
                "Uwagi" TEXT,
                "Temperature range" TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "Grzanie" (
                "Model jednostki" TEXT,
                "model opcji" TEXT,
                "Cena PLN" INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "Zestaw_podgrzewacza_odplywu_skroplin" (
                "Grzatki Grzałki elektryczne odpływu (35W)" TEXT,
                "model opcji" TEXT,
                "Cena PLN" REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "samochody" (
                "Marka" TEXT,
                "Model" TEXT,
                "Kubatura (m³)" REAL,
                "Zabudowy izotermiczne Cena (zł netto)" INTEGER,
                "Sklejki Cena (zł netto)" INTEGER,
                "Nadkola sklejka 12mm Cena zł netto" INTEGER
            )
        """)
        
        self.conn.commit()

    def get_vehicle_info(self, marka, model):
        """Pobiera informacje o pojeździe z nowej struktury bazy danych"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                "Marka", "Model", "Kubatura (m³)",
                "Zabudowy izotermiczne Cena (zł netto)",
                "Sklejki Cena (zł netto)",
                "Nadkola sklejka 12mm Cena zł netto"
            FROM samochody
            WHERE "Marka" = ? AND "Model" = ?
        """, (marka, model))
        
        result = cursor.fetchone()
        if result:
            return {
                'marka': result[0],
                'model': result[1],
                'kubatura': result[2],
                'zabudowa_cena': result[3],
                'sklejki_cena': result[4],
                'nadkola_cena': result[5]
            }
        return None

    def get_available_aggregates(self):
        """Pobiera dostępne agregaty Daikin"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM "Agregaty Daikin"')
        return cursor.fetchall()

    def get_heating_options(self):
        """Pobiera opcje grzania"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM "Grzanie"')
        return cursor.fetchall() 