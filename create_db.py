#PLIK DO USUWANIA STAREJ BAZY I TWORZENIA NOWEJ

import os
from sqlalchemy import create_engine
from models import Base

# Ścieżka do pliku bazy
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "food_cost.db")

# 1. Usuń starą bazę, jeśli istnieje
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("🗑️ Stara baza danych usunięta.")

# 2. Utwórz silnik (engine) i nową bazę
engine = create_engine(f"sqlite:///{DB_PATH}")
Base.metadata.create_all(engine)

print("✅ Nowa baza danych została utworzona.")
