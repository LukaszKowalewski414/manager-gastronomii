import fitz
import os
import re
from datetime import datetime

def czytaj_pdf(nazwa_pliku):
    sciezka = os.path.join("faktury", nazwa_pliku)

    if not os.path.exists(sciezka):
        print("❌ Nie znaleziono pliku:", sciezka)
        return

    dokument = fitz.open(sciezka)
    tekst_caly = ""

    for strona in dokument:
        tekst_caly += strona.get_text()

    dokument.close()
    return tekst_caly

def oczysc_kwote(tekst):
    tekst = tekst.lower().replace("pln", "").replace("zł", "")
    tekst = tekst.replace("\u00A0", "").replace(" ", "")
    tekst = tekst.replace(".", "")
    tekst = tekst.replace(",", ".")

    print(f"🧪 RAW: {repr(tekst)}")

    try:
        return round(float(tekst), 2)
    except:
        print("❌ Dalej błąd przy konwersji:", tekst)
        return None

def wyciagnij_date_z_tekstu(tekst):
    """
    Wyszukuje datę wystawienia faktury na podstawie słów kluczowych.
    """
    linie = [linia.strip().replace(":", " ") for linia in tekst.split("\n")]
    potencjalne_linie = []
    wzorce_slow = ["data faktury", "data wystawienia", "faktura z dnia", "wystawiono"]

    for i, linia in enumerate(linie):
        if any(w in linia.lower() for w in wzorce_slow):
            print(f"🟡 Znaleziono linię z kontekstem daty: {linia}")
            potencjalne_linie.append(linia)
            if i + 1 < len(linie):
                print(f"➕ Dodaję również następną linię: {linie[i + 1]}")
                potencjalne_linie.append(linie[i + 1])

    for linia in potencjalne_linie:
        print(f"🔍 Analizuję linię z datą: {linia.strip()}")
        daty = re.findall(r"\d{2}[.\-\/]\d{2}[.\-\/]\d{4}|\d{4}[.\-\/]\d{2}[.\-\/]\d{2}", linia)
        print(f"📆 Znalezione daty: {daty}")
        for d in daty:
            for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y"):
                try:
                    parsed_date = datetime.strptime(d.replace(" ", "").replace(",", "."), fmt).date()
                    print(f"✅ Udało się sparsować: {parsed_date}")
                    return parsed_date.isoformat()
                except ValueError:
                    continue

    # 🔹 DEBUG 3: Fallback – gdy brak linii kontekstowych
    print("⚠️ Używam fallbacku – przeszukuję cały tekst...")
    fallback = re.findall(r"\d{2}[.\-\/]\d{2}[.\-\/]\d{4}|\d{4}[.\-\/]\d{2}[.\-\/]\d{2}", tekst)
    print(f"📋 Daty w fallbacku: {fallback}")
    for d in fallback:
        for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                parsed_date = datetime.strptime(d.replace(" ", "").replace(",", "."), fmt).date()
                print(f"✅ Fallback parsowanie: {parsed_date}")
                return parsed_date.isoformat()
            except ValueError:
                continue

    print("❌ Nie znaleziono żadnej daty.")
    return "–"



def wyciagnij_dane_z_pdf(tekst):
    dane = {
        "data": "–",
        "kwota": "–",
        "nip": "–",
        "firma": "–"
    }

    linie = tekst.split("\n")

    # === SZUKANIE DATY (nowa funkcja z kontekstem) ===
    dane["data"] = wyciagnij_date_z_tekstu(tekst)

    # === SZUKANIE KWOTY (agresywne + czyszczenie i kontekst) ===
    kwoty_znalezione = []
    linie = tekst.split("\n")

    for i, linia in enumerate(linie):
        if any(klucz in linia.lower() for klucz in
               ["brutto", "do zapłaty", "suma", "razem", "kwota", "wartość", "łącznie"]):
            kandydatki = [linia]
            if i + 1 < len(linie):
                kandydatki.append(linie[i + 1])
            for k in kandydatki:
                matchy = re.findall(r"\d{1,3}(?:[., ]\d{3})*[.,]\d{2}", k)
                for m in matchy:
                    print(f"🔎 Znaleziona kwota surowa: {m} w linii: {k}")
                    czyszczona = (
                        m.replace(" ", "")
                         .replace("zł", "")
                         .replace("PLN", "")
                         .replace("\u00A0", "")
                         .replace(".", "")
                         .replace(",", ".")
                    )
                    try:
                        liczba = float(czyszczona)
                        kwoty_znalezione.append(liczba)
                        print(f"✅ Zamieniono na float: {liczba}")
                    except ValueError:
                        print(f"❌ Błąd przy konwersji: {czyszczona}")

    if kwoty_znalezione:
        dane["kwota"] = f"{max(kwoty_znalezione):.2f}"
        print(f"✅ Wybrana największa kwota: {dane['kwota']}")


    # === SZUKANIE NIPU (różne formaty) ===
    match = re.search(r"(PL)?[ \-]?\d{3}[ \-]?\d{3}[ \-]?\d{3}", tekst)
    if match:
        dane["nip"] = match.group().replace(" ", "").replace("-", "")

    # === SZUKANIE NAZWY FIRMY (po słowie "Sprzedawca") ===
    for i, linia in enumerate(linie):
        if "sprzedawca" in linia.lower():
            if i + 1 < len(linie):
                nazwa = linie[i + 1].strip()
                if 3 < len(nazwa) < 100:
                    dane["firma"] = nazwa
            break

    return dane
