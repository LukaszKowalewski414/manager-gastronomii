from database import Session
from models import Utarg
from datetime import datetime

def dodaj_utarg():
    session = Session()
    try:
        data_str = input("Podaj datę (RRRR-MM-DD): ")
        data = datetime.strptime(data_str, "%Y-%m-%d").date()
        bar = float(input("Podaj utarg z baru: "))
        bramka = float(input("Podaj utarg z bramki: "))
        nowy_utarg = Utarg(data=data, bar=bar, bramka=bramka)
        session.add(nowy_utarg)
        session.commit()
        print("✅ Utarg został zapisany!")
    except Exception as e:
        print("❌ Błąd:", e)
    finally:
        session.close()
