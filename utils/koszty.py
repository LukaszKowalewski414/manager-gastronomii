from database import Session
from models import KosztPracownika, KategoriaPracownika
from datetime import datetime

def dodaj_koszt_pracownika():
    session = Session()
    try:
        data_str = input("Podaj datę (RRRR-MM-DD): ")
        data = datetime.strptime(data_str, "%Y-%m-%d").date()
        #zmiana tekstu jaki wpisałem na format daty w py
        #.data()- odcina godzinę, zostaje data.

        kwota = float(input("Podaj kwotę kosztu: "))

        print("Wybierz kategorię:")
        for kat in KategoriaPracownika:
            print(f"- {kat.name}")
        #wydrukowanie wszysktich kategorii do wyboru.

        wybor = input("Kategoria: ").lower()

        if wybor not in KategoriaPracownika.__members__:
            print("❌ Nieprawidłowa kategoria.")
            return
        #jeśli ktoś wybierze nieprawidłową kategorię
        #program to odrzuci

        kategoria = KategoriaPracownika[wybor]  #konwersja tekstu na obiekt enuma
        koszt = KosztPracownika(data=data, kwota=kwota, kategoria=kategoria)
        session.add(koszt)
        session.commit()
        print("✅ Koszt pracownika zapisany!")
    except Exception as e:
        print("❌ Błąd:", e)
    finally:
        session.close()
