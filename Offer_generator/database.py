import sqlite3
import logging
from typing import Optional, List, Dict
import json

logger = logging.getLogger(__name__)

class OfferDatabase:
    def __init__(self):
        """Inicjalizacja połączenia z bazą SQLite"""
        try:
            self.conn = sqlite3.connect('autoadaptacje.db')
            self.create_tables()
            logger.info("Połączono z bazą SQLite")
        except Exception as e:
            logger.error(f"Błąd podczas inicjalizacji bazy SQLite: {str(e)}")
            raise

    def create_tables(self):
        """Tworzenie tabel w bazie danych"""
        try:
            cursor = self.conn.cursor()
            
            # Tabela samochodów
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS samochody (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    marka TEXT NOT NULL,
                    model TEXT NOT NULL,
                    rok_produkcji INTEGER,
                    kubatura TEXT,
                    klimatyzacja BOOLEAN DEFAULT 0,
                    dostepnosc INTEGER DEFAULT 1,
                    ostatnia_aktualizacja TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela zabudów izotermicznych
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS zabudowy (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    typ TEXT DEFAULT 'izotermiczna',
                    temperatura TEXT,
                    cena_netto REAL,
                    atest_pzh BOOLEAN DEFAULT 1,
                    gwarancja TEXT,
                    material_izolacyjny_typ TEXT,
                    material_izolacyjny_grubosc TEXT,
                    sciany_sufit TEXT,
                    podloga TEXT,
                    wykonczenia TEXT,
                    dostepnosc INTEGER DEFAULT 1
                )
            ''')
            
            # Tabela agregatów
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS agregaty (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model TEXT NOT NULL,
                    typ TEXT DEFAULT 'drogowy',
                    czynnik TEXT,
                    cena_netto REAL,
                    dostepnosc INTEGER DEFAULT 1
                )
            ''')
            
            # Tabela montażu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS montaz (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mocowanie_sprezarka_opis TEXT,
                    mocowanie_sprezarka_cena REAL,
                    montaz_agregatu_cena REAL
                )
            ''')
            
            # Dodaj przykładowe dane
            # self._add_sample_data()
            
            self.conn.commit()
            logger.info("Tabele zostały utworzone")
            
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia tabel: {str(e)}")
            raise

    def _add_sample_data(self):
        """Dodawanie przykładowych danych"""
        try:
            cursor = self.conn.cursor()
            
            # Przykładowe samochody
            cursor.execute('''
                INSERT OR IGNORE INTO samochody (marka, model, rok_produkcji, kubatura, klimatyzacja)
                VALUES 
                    ('Fiat', 'Scudo', 2023, '6M3', 1),
                    ('Fiat', 'Ducato', 2023, '8M3', 1),
                    ('Peugeot', 'Boxer', 2023, '8M3', 1)
            ''')
            
            # Przykładowe zabudowy
            cursor.execute('''
                INSERT OR IGNORE INTO zabudowy (
                    temperatura, cena_netto, gwarancja, 
                    material_izolacyjny_typ, material_izolacyjny_grubosc,
                    sciany_sufit, podloga, wykonczenia
                )
                VALUES 
                    ('0 st.C', 11000, '2 lata', 
                    'pianka poliuretanowa', '40 mm',
                    'laminat gładki biały', 'wylewka antypoślizgowa', 
                    'blacha nierdzewna,aluminium')
            ''')
            
            # Przykładowe agregaty
            cursor.execute('''
                INSERT OR IGNORE INTO agregaty (model, typ, czynnik, cena_netto)
                VALUES 
                    ('Zanotti Z200SA000E/EU', 'drogowy', '134', 12100)
            ''')
            
            # Przykładowy montaż
            cursor.execute('''
                INSERT OR IGNORE INTO montaz (
                    mocowanie_sprezarka_opis, 
                    mocowanie_sprezarka_cena,
                    montaz_agregatu_cena
                )
                VALUES 
                    ('Mocowanie +sprężarka', 4200, 3500)
            ''')
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Błąd podczas dodawania przykładowych danych: {str(e)}")
            raise

    def get_vehicle_info(self, marka: Optional[str] = None, model: Optional[str] = None) -> Optional[Dict]:
        """Pobiera informacje o pojeździe z bazy"""
        try:
            cursor = self.conn.cursor()
            
            query = """
                SELECT 
                    id, marka, model, rok_produkcji, kubatura, klimatyzacja
                FROM samochody
                WHERE dostepnosc = 1
            """
            params = []
            
            if marka:
                query += " AND LOWER(TRIM(marka)) = LOWER(TRIM(?))"
                params.append(marka)
            if model:
                query += " AND LOWER(TRIM(model)) = LOWER(TRIM(?))"
                params.append(model)
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': int(row[0]),
                    'marka': str(row[1]).strip(),
                    'model': str(row[2]).strip(),
                    'rok_produkcji': int(row[3]),
                    'kubatura': str(row[4]).strip(),
                    'klimatyzacja': bool(row[5])
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania danych z bazy: {str(e)}")
            return None

    def get_available_adaptations(self, vehicle_id: int) -> List[str]:
        """Pobiera dostępne adaptacje dla danego pojazdu"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT wykonczenia
                FROM zabudowy
                WHERE id = ? AND dostepnosc = 1
            """, (vehicle_id,))
            
            row = cursor.fetchone()
            if row and row[0]:
                return row[0].split(',')
            return []
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania adaptacji: {str(e)}")
            return []

    def get_all_vehicles(self):
        """Pobiera wszystkie pojazdy z bazy"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 
                    id, marka, model, rok_produkcji, kubatura, klimatyzacja
                FROM samochody
                WHERE dostepnosc = 1
            """)
            
            vehicles = []
            for row in cursor.fetchall():
                vehicles.append({
                    'id': row[0],
                    'marka': row[1],
                    'model': row[2],
                    'rok_produkcji': row[3],
                    'kubatura': row[4],
                    'klimatyzacja': bool(row[5])
                })
            
            return vehicles
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania wszystkich pojazdów: {str(e)}")
            return []

    def __del__(self):
        """Zamknięcie połączenia z bazą przy usuwaniu obiektu"""
        if hasattr(self, 'conn'):
            self.conn.close() 