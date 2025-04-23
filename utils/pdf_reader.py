import fitz
import os
import re
from datetime import datetime

# ─── helpery do wyboru nazwy firmy ────────────────────────────────────────────

forbidden_keywords = {
    "faktura", "nr", "bdo", "opłaty", "usługi", "dostawy", "zakończenia",
    "data", "miejscowość", "kod", "termin", "ul.", "tel", "www", "kontakt",
    "@", "wykonania"
}

def is_valid_candidate(line: str) -> bool:
    l = line.strip()
    # wyklucza linie zaczynające się od cyfry (np. kod pocztowy)
    if l and l[0].isdigit():
        return False
    if not (3 < len(l) < 100 and l.count(" ") >= 1):
        return False
    if l.endswith(":"):
        return False
    if sum(1 for c in l if c.isupper()) < 2:
        return False
    low = l.lower()
    if any(kw in low for kw in forbidden_keywords):
        return False
    if low.startswith("lub "):
        return False
    return True

def score_candidate(line: str) -> int:
    # liczba wielkich liter + liczba spacji
    return sum(1 for c in line if c.isupper()) + line.count(" ")

def extract_company_name(lines: list[str], nip_idx: int) -> str | None:
    window = 4
    above = lines[max(0, nip_idx - window): nip_idx]
    below = lines[nip_idx + 1: nip_idx + 1 + window]

    valid_above = [l for l in above if is_valid_candidate(l)]
    if valid_above:
        return max(valid_above, key=score_candidate).strip()

    valid_below = [l for l in below if is_valid_candidate(l)]
    if valid_below:
        return max(valid_below, key=score_candidate).strip()

    return None

# ─────────────────────────────────────────────────────────────────────────────


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

    # ─── znajdź NIP SPRZEDAWCY i nazwę FIRMY ───────────────────────
    dane["nip"] = "–"
    dane["firma"] = "–"

    # skanuj cały dokument aż znajdziesz pierwszy poprawny NIP
    for i, linia in enumerate(linie):
        m = re.search(r"(?:PL)?\s*[:\-]?\s*(\d[\d\-\s]{8,15})", linia)
        if not m:
            continue
        nip_raw = m.group(1)
        czysty = nip_raw.replace(" ", "").replace("-", "")
        if len(czysty) == 10 and czysty.isdigit():
            dane["nip"] = czysty
            print(f"✅ Znalazłem NIP sprzedawcy: {czysty}")
            # teraz jedna funkcja, która wybiera firmę z okolic tej linii
            nazwa = extract_company_name(linie, i)
            if nazwa:
                dane["firma"] = nazwa
                print(f"🏢 Trafiona firma: {dane['firma']}")
            else:
                print("⚠️ Nie znalazłem nazwy firmy w 4 liniach od NIP-u sprzedawcy")
            break
    # ───────────────────────────────────────────────────────────────


    # Skróć firmę, jeśli zawiera przecinki – weź tylko pierwszy człon
    if "," in dane["firma"]:
        dane["firma"] = dane["firma"].split(",")[0].strip()
        print(f"✂️ Skrócona firma: {dane['firma']}")


    return dane
