from utils.utargi import dodaj_utarg
from utils.koszty import dodaj_koszt_pracownika
from utils.faktury import dodaj_fakture
from utils.raport import raport_miesieczny
from utils.pdf_reader import czytaj_pdf, wyciagnij_dane_z_pdf
from utils.dostawcy import get_or_create_dostawca
from database import Session
from models import Faktura
from datetime import datetime

# 🔥 NOWA funkcja - dodawanie faktury z pliku PDF

def dodaj_fakture_z_pdf():
    nazwa = input("\n📄 Podaj nazwę pliku PDF (z folderu Faktury/): ").strip()
    tekst = czytaj_pdf(nazwa)

    if not tekst:
        print("❌ Nie udało się odczytać pliku PDF. Przerywam.")
        return

    dane = wyciagnij_dane_z_pdf(tekst)

    # Dodaj konwersję danych na datetime.date i float
    if isinstance(dane["data"], str):
        dane["data"] = datetime.strptime(dane["data"], "%Y-%m-%d").date()

    if isinstance(dane["kwota"], str):
        dane["kwota"] = float(dane["kwota"].replace(",", "."))

    print("\n📄 DANE Z FAKTURY:")
    for k, v in dane.items():
        print(f"{k.capitalize()}: {v}")

    session = Session()
    kategoria = get_or_create_dostawca(dane["nip"], dane["firma"], session)

    nowa_faktura = Faktura(
        data=dane["data"],
        kwota=dane["kwota"],
        kategoria=kategoria
    )
    session.add(nowa_faktura)
    session.commit()

    print("✅ Faktura zapisana do bazy.")


# 🔥 Zmienione menu() - dodano opcję 5

def menu():
    while True:
        print("\n=== MANAGER GASTRONOMII ===")
        print("1. Dodaj utarg")
        print("2. Dodaj koszt pracownika")
        print("3. Dodaj fakturę (ręcznie)")
        print("4. Generuj raport miesięczny")
        print("5. Dodaj fakturę z pliku PDF")  # <-- NOWA OPCJA
        print("0. Wyjście")

        wybor = input("Wybierz opcję: ")

        if wybor == "1":
            dodaj_utarg()
        elif wybor == "2":
            dodaj_koszt_pracownika()
        elif wybor == "3":
            dodaj_fakture()
        elif wybor == "4":
            raport_miesieczny()
        elif wybor == "5":
            dodaj_fakture_z_pdf()  # <-- PODPIĘCIE NOWEJ FUNKCJI
        elif wybor == "0":
            print("Zamykam program.")
            break
        else:
            print("\u2757 Nieprawidłowy wybór.")


if __name__ == "__main__":
    menu()  # <-- tylko menu! nie robimy nic "poza"
