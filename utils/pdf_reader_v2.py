import fitz
import os
import re
import pdfplumber
from datetime import datetime

# ─── HELPERY DO NAZWY FIRMY ──────────────────────────────────────────────────

forbidden_keywords = {
    "faktura", "nr", "bdo", "opłaty", "usługi", "dostawy", "zakończenia",
    "data", "miejscowość", "kod", "termin", "ul.", "tel", "www", "kontakt",
    "@", "wykonania", "numer", "nabywca", "odbiorca", "rokoko", "spółka"
}

def is_valid_candidate(line: str) -> bool:
    l = line.strip()
    if not (3 < len(l) < 100 and l.count(" ") >= 1):
        return False
    if l.lower().startswith("faktura nr"):
        return False
    if l[0].isdigit() or l.endswith(":"):
        return False
    if sum(1 for c in l if c.isupper()) < 2:
        return False
    low = l.lower()
    if any(kw in low for kw in forbidden_keywords):
        return False
    return True

def score_candidate(line: str) -> int:
    return sum(1 for c in line if c.isupper()) + line.count(" ")

def extract_company_name(lines: list[str], nip_idx: int) -> str | None:
    window = 4
    above = lines[max(0, nip_idx - window): nip_idx]
    below = lines[nip_idx + 1: nip_idx + 1 + window]
    candidates = [l for l in above + below if is_valid_candidate(l)]
    if candidates:
        return max(candidates, key=score_candidate).strip()
    return None

def normalize_number(s):
    s = s.replace(" ", "").replace("\u00A0", "").replace("zł", "").replace("pln", "")
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    return s

# ─────────────────────────────────────────────────────────────────────────────

def czytaj_pdf(path: str) -> str | None:
    if not os.path.exists(path):
        print("❌ Nie znaleziono pliku:", path)
        return None
    doc = fitz.open(path)
    text = "".join(page.get_text("text") for page in doc)
    doc.close()
    return text

def extract_net_sum_with_pdfplumber(path: str) -> float | None:
    total = 0.0
    found = False
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                header = [cell.strip().lower() if cell else "" for cell in table[0]]
                idx = next((i for i,h in enumerate(header) if h == "netto" or "netto" in h), None)
                if idx is None:
                    continue
                for row in table[1:]:
                    cell = row[idx]
                    if not cell:
                        continue
                    try:
                        total += float(normalize_number(cell))
                        found = True
                    except:
                        pass
    return total if found and total > 0 else None

def wyciagnij_date_z_tekstu(text: str) -> str:
    lines = [l.strip().replace(":", " ") for l in text.split("\n")]
    patterns = ["data faktury", "data wystawienia", "faktura z dnia", "wystawiono"]
    for i, line in enumerate(lines):
        low = line.lower()
        if any(p in low for p in patterns):
            if "termin" in low:
                continue
            for cand in (line, lines[i+1] if i+1 < len(lines) else ""):
                for d in re.findall(r"\d{2}[.\-/]\d{2}[.\-/]\d{4}|\d{4}[.\-/]\d{2}[.\-/]\d{2}", cand):
                    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y"):
                        try:
                            return datetime.strptime(d.replace(" ", "").replace(",", "."), fmt).date().isoformat()
                        except ValueError:
                            continue
    for i, line in enumerate(lines):
        if "termin" in line.lower():
            continue
        for d in re.findall(r"\d{2}[.\-/]\d{2}[.\-/]\d{4}|\d{4}[.\-/]\d{2}[.\-/]\d{2}", line):
            for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y"):
                try:
                    return datetime.strptime(d.replace(" ", "").replace(",", "."), fmt).date().isoformat()
                except ValueError:
                    continue
    return "–"

def wyciagnij_dane_z_pdf(text: str, path: str) -> dict:
    dane = {
        "data": "–",
        "kwota brutto": "–",
        "kwota netto": "–",
        "nip": "–",
        "firma": "–"
    }
    lines = text.split("\n")

    # NIP-y z całego dokumentu
    nip_candidates = []
    for i, line in enumerate(lines):
        for m in re.findall(r"(?:PL)?\s*[:\-]?\s*(\d[\d\-\s]{8,15})", line):
            nip = m.replace(" ", "").replace("-", "")
            if len(nip) == 10 and nip.isdigit():
                nip_candidates.append((i, nip))

    # 1️⃣ Data
    dane["data"] = wyciagnij_date_z_tekstu(text)

    # 2️⃣ Kwota brutto
    brutto_vals = []
    for i, line in enumerate(lines):
        if any(k in line.lower() for k in ["brutto", "do zapłaty"]):
            brutto_vals += [float(normalize_number(m)) for m in re.findall(r"\d{1,3}(?:[., ]\d{3})*[.,]\d{2}", line)]
    if not brutto_vals:
        for line in lines:
            brutto_vals += [float(normalize_number(m)) for m in re.findall(r"\d{1,3}(?:[., ]\d{3})*[.,]\d{2}", line)]
    if brutto_vals:
        dane["kwota brutto"] = f"{max(brutto_vals):.2f}"
    brutto = float(dane["kwota brutto"]) if dane["kwota brutto"] != "–" else None
    threshold = brutto * 0.7 if brutto else 0

    # 3️⃣ Kwota netto
    net = extract_net_sum_with_pdfplumber(path)
    if net and brutto and threshold <= net <= brutto:
        dane["kwota netto"] = f"{net:.2f}"

    # 4️⃣ NIP i firma – szukamy tego, który nie jest w sekcji Nabywca
    nabywca_block = "\n".join([l.lower() for l in lines if "nabywca" in l.lower() or "odbiorca" in l.lower()])
    for idx, nip in nip_candidates:
        if nip not in nabywca_block:
            dane["nip"] = nip
            firma = extract_company_name(lines, idx)
            if firma and "rokoko" not in firma.lower():
                dane["firma"] = firma.split(",")[0].strip()
            break

    print("📄 PARSER V2 WYNIKI:")
    for k,v in dane.items():
        print(f"{k}: {v}")

    return dane

def parse_invoice_from_pdf_v2(path: str) -> dict | None:
    text = czytaj_pdf(path)
    if text is None:
        return None
    return wyciagnij_dane_z_pdf(text, path)
