from database import Session
from models import Faktura, KategoriaFaktury
from datetime import datetime
#cały plik jest analogiczny do koszty.py

def dodaj_fakture():
    session = Session()
    try:
        data_str = input("Podaj datę faktury (RRRR-MM-DD): ")
        data = datetime.strptime(data_str, "%Y-%m-%d").date()

        kwota = float(input("Podaj kwotę faktury: "))

        print("Wybierz kategorię:")
        for kat in KategoriaFaktury:
            print(f"- {kat.name}")

        wybor = input("Kategoria: ").lower()

        if wybor not in KategoriaFaktury.__members__:
            print("❌ Nieprawidłowa kategoria.")
            return

        kategoria = KategoriaFaktury[wybor]
        faktura = Faktura(data=data, kwota=kwota, kategoria=kategoria)
        session.add(faktura)
        session.commit()
        print("✅ Faktura zapisana!")
    except Exception as e:
        print("❌ Błąd:", e)
    finally:
        session.close()
