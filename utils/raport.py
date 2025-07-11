from database import Session
from models import Utarg, KosztPracownika, Faktura, KategoriaPracownika, KategoriaFaktury
from sqlalchemy import extract
from datetime import datetime

def raport_miesieczny():
    session = Session()
    try:
        miesiac_str = input("Podaj miesiąc (RRRR-MM): ")
        rok, miesiac = map(int, miesiac_str.split("-"))

        # === UTARGI ===
        utargi = session.query(Utarg).filter(
            extract('month', Utarg.data) == miesiac,
            extract('year', Utarg.data) == rok
        ).all()
        dni_otwarte = len(utargi)
        suma_bar = sum(u.bar for u in utargi)
        suma_bramka = sum(u.bramka for u in utargi)
        suma_utarg = suma_bar + suma_bramka

        # === KOSZTY PRACOWNIKÓW ===
        koszty = session.query(KosztPracownika).filter(
            extract('month', KosztPracownika.data) == miesiac,
            extract('year', KosztPracownika.data) == rok
        ).all()

        koszt_ogolem = sum(k.kwota for k in koszty)
        koszt_barmanow = sum(k.kwota for k in koszty if k.kategoria == KategoriaPracownika.bar)

        # === FAKTURY ===
        faktury = session.query(Faktura).filter(
            extract('month', Faktura.data) == miesiac,
            extract('year', Faktura.data) == rok
        ).all()

        suma_faktur = sum(f.kwota for f in faktury)
        koszt_towaru = sum(f.kwota for f in faktury if f.kategoria == KategoriaFaktury.towar)

        # === WYNIKI ===
        print(f"\n📅 Raport za {miesiac_str}")
        print(f"- Dni otwarte: {dni_otwarte}")
        print(f"- Utarg bar: {suma_bar:.2f} zł")
        print(f"- Utarg bramka: {suma_bramka:.2f} zł")
        print(f"- Suma utargu: {suma_utarg:.2f} zł")
        print(f"- Koszty pracowników: {koszt_ogolem:.2f} zł")
        print(f"- Koszt barmanów: {koszt_barmanow:.2f} zł")
        print(f"- Koszty z faktur: {suma_faktur:.2f} zł")
        print(f"- Koszt towaru: {koszt_towaru:.2f} zł")

        # === WSKAŹNIKI ===
        if suma_utarg > 0:
            print(f"- Pracownicy / utarg: {koszt_ogolem / suma_utarg:.2%}")
        if suma_bar > 0:
            print(f"- Barmani / bar: {koszt_barmanow / suma_bar:.2%}")
            print(f"- Food cost: {koszt_towaru / suma_bar:.2%}")
        if suma_kuchnia > 0:
            print(f"- Kucharze / kuchnia: {koszt_kucharzy / suma_kuchnia:.2%}")

    except Exception as e:
        print("❌ Błąd podczas generowania raportu:", e)
    finally:
        session.close()
