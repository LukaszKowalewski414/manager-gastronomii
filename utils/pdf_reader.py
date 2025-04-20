import fitz
import os
import re

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

    print(f"🧪 RAW: {repr(tekst)}")  # DODANE

    try:
        return round(float(tekst), 2)
    except:
        print("❌ Dalej błąd przy konwersji:", tekst)
        return None

def wyciagnij_dane_z_pdf(tekst):
    import re

    # Szukamy daty
    data = re.search(r"\d{4}[-/\.]\d{2}[-/\.]\d{2}|\d{2}[-/\.]\d{2}[-/\.]\d{4}", tekst)

    # Szukamy kwot
    kwoty_znalezione = []
    linie = tekst.split("\n")
    for i, linia in enumerate(linie):
        if any(klucz in linia.lower() for klucz in
               ["brutto", "do zapłaty", "suma", "razem", "kwota", "wartość", "łącznie"]):
            kandydatki = [linia]
            if i + 1 < len(linie):
                kandydatki.append(linie[i + 1])
            for k in kandydatki:
                matchy = re.findall(r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?", k)
                for m in matchy:
                    print(f"🔎 Znaleziona kwota surowa: {m} w linii: {k}")
                    czyszczona = m.replace(" ", "").replace("zł", "").replace("PLN", "").replace(".", "").replace(",", ".")
                    try:
                        liczba = float(czyszczona)
                        kwoty_znalezione.append(liczba)
                        print(f"✅ Zamieniono na float: {liczba}")
                    except ValueError:
                        print(f"❌ Błąd przy konwersji: {czyszczona}")

    kwota = round(max(kwoty_znalezione), 2) if kwoty_znalezione else None

    # Szukamy NIP-u
    nip = re.search(r"\bPL?\d{10}\b", tekst)
    nip = nip.group(0) if nip else "–"

    # Szukamy nazwy firmy
    firma = "–"
    linie_niskie = tekst.lower().split("\n")
    for i, l in enumerate(linie_niskie):
        if "pl" in l and re.search(r"\d{10}", l):
            firma = linie[i - 1].strip() if i > 0 else "–"
            break

    return {
        "data": data.group(0) if data else "–",
        "kwota": kwota if kwota else "–",
        "nip": nip,
        "firma": firma
    }

