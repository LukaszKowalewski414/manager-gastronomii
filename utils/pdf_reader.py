import fitz
import os
import re
import pdfplumber
from datetime import datetime

# ─── HELPERY DO NAZWY FIRMY ──────────────────────────────────────────────────

forbidden_keywords = {
    "faktura", "nr", "bdo", "opłaty", "usługi", "dostawy", "zakończenia",
    "data", "miejscowość", "kod", "termin", "ul.", "tel", "www", "kontakt",
    "@", "wykonania"
}

def is_valid_candidate(line: str) -> bool:
    l = line.strip()
    if not (3 < len(l) < 100 and l.count(" ") >= 1):
        return False
    if l[0].isdigit() or l.endswith(":"):
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
    return sum(1 for c in line if c.isupper()) + line.count(" ")

def extract_company_name(lines: list[str], nip_idx: int) -> str | None:
    window = 4
    above = lines[max(0, nip_idx - window): nip_idx]
    below = lines[nip_idx + 1: nip_idx + 1 + window]
    candidates = [l for l in above + below if is_valid_candidate(l)]
    if candidates:
        return max(candidates, key=score_candidate).strip()
    return None

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
                idx = next((i for i,h in enumerate(header) if h == "netto"), None)
                if idx is None:
                    idx = next((i for i,h in enumerate(header) if "netto" in h), None)
                if idx is None:
                    continue
                for row in table[1:]:
                    cell = row[idx]
                    if not cell:
                        continue
                    num = re.sub(r"[^\d,\.]", "", cell)
                    if "." in num and "," in num:
                        num = num.replace(".", "").replace(",", ".")
                    else:
                        num = num.replace(",", ".")
                    try:
                        total += float(num)
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
            # sprawdz tę i następną linię
            for cand in (line, lines[i+1] if i+1 < len(lines) else ""):
                for d in re.findall(r"\d{2}[.\-/]\d{2}[.\-/]\d{4}|\d{4}[.\-/]\d{2}[.\-/]\d{2}", cand):
                    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y"):
                        try:
                            return datetime.strptime(d.replace(" ", "").replace(",", "."), fmt).date().isoformat()
                        except ValueError:
                            continue
    # fallback globalny, ale skip linie z 'termin'
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

    # 1️⃣ Data
    dane["data"] = wyciagnij_date_z_tekstu(text)

    # 2️⃣ Brutto
    brutto_vals = []
    for i, line in enumerate(lines):
        low = line.lower()
        if any(k in low for k in ["brutto", "do zapłaty"]):
            block = [line] + ([lines[i+1]] if i+1 < len(lines) else [])
            for b in block:
                if "%" in b:
                    continue
                for m in re.findall(r"\d{1,3}(?:[., ]\d{3})*[.,]\d{2}", b):
                    s = m.replace(" ", "").replace("zł", "").replace("pln", "") \
                         .replace("\u00A0", "").replace(".", "").replace(",", ".")
                    try:
                        brutto_vals.append(float(s))
                    except:
                        pass
    if brutto_vals:
        mb = max(brutto_vals)
        dane["kwota brutto"] = f"{mb:.2f}"
    brutto = float(dane["kwota brutto"]) if dane["kwota brutto"] != "–" else None
    # wymagamy, że netto >= 70% brutto
    threshold = brutto * 0.7 if brutto else 0

    # 3️⃣ Netto z tabeli
    net_sum = extract_net_sum_with_pdfplumber(path)
    if net_sum is not None and brutto is not None and threshold <= net_sum <= brutto:
        dane["kwota netto"] = f"{net_sum:.2f}"
    else:
        # 4️⃣ Brutto - VAT
        for i, line in enumerate(lines):
            low = line.lower()
            if "podatek vat" in low or "wartość vat" in low:
                for w in lines[i+1 : i+11]:
                    if "%" in w:
                        continue
                    m = re.search(r"\d{1,3}(?:[., ]\d{3})*[.,]\d{2}", w)
                    if m and brutto is not None:
                        vat_s = m.group(0).replace(" ", "").replace("zł", "").replace("pln", "") \
                                      .replace("\u00A0", "").replace(".", "").replace(",", ".")
                        try:
                            vat = float(vat_s)
                            net = brutto - vat
                        except:
                            continue
                        if threshold <= net <= brutto:
                            dane["kwota netto"] = f"{net:.2f}"
                            break
                if dane["kwota netto"] != "–":
                    break
        # 5️⃣ Numeric-only summary fallback
        if dane["kwota netto"] == "–" and brutto is not None:
            for line in lines:
                m = re.match(r"^\s*(\d{1,3}(?:[., ]\d{3})*[.,]\d{2})\s*(?:zł)?\s*$",
                             line.strip(), flags=re.IGNORECASE)
                if not m:
                    continue
                num_s = m.group(1).replace(" ", "").replace("\u00A0", "")
                if "." in num_s and "," in num_s:
                    num_s = num_s.replace(".", "").replace(",", ".")
                else:
                    num_s = num_s.replace(",", ".")
                try:
                    v = float(num_s)
                except ValueError:
                    continue
                if threshold <= v <= brutto:
                    dane["kwota netto"] = f"{v:.2f}"
                    break

    # 6️⃣ NIP i nazwa sprzedawcy
    # najpierw szukamy sekcji "sprzedawca"
    found = False
    for i, line in enumerate(lines):
        if "sprzedawca" in line.lower():
            for w in lines[i:i+10]:
                m = re.search(r"(?:PL)?\s*[:\-]?\s*(\d[\d\-\s]{8,15})", w)
                if m:
                    nip = m.group(1).replace(" ", "").replace("-", "")
                    if len(nip) == 10 and nip.isdigit():
                        dane["nip"] = nip
                        idx = lines.index(w)
                        firma = extract_company_name(lines, idx)
                        if firma:
                            dane["firma"] = firma.split(",")[0].strip()
                        found = True
                        break
            if found:
                break
    # fallback: pierwszy poprawny NIP
    if not found:
        for i, line in enumerate(lines):
            m = re.search(r"(?:PL)?\s*[:\-]?\s*(\d[\d\-\s]{8,15})", line)
            if not m:
                continue
            nip = m.group(1).replace(" ", "").replace("-", "")
            if len(nip) == 10 and nip.isdigit():
                dane["nip"] = nip
                firma = extract_company_name(lines, i)
                if firma:
                    dane["firma"] = firma.split(",")[0].strip()
                break

    return dane

def parse_invoice_from_pdf(path: str) -> dict | None:
    text = czytaj_pdf(path)
    if text is None:
        return None
    return wyciagnij_dane_z_pdf(text, path)
