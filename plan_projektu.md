# 🧠 Manager Gastronomii – Plan Projektu

## ✅ Etap 1 – MVP terminalowe (ZAKOŃCZONY – 2025-04-17)

**Cel:**  
Stworzenie prostego terminalowego systemu do zarządzania utargiem, kosztami pracowników i fakturami oraz raportowania miesięcznego.

**Zrealizowano:**
- struktura katalogów: `data/`, `utils/`, `reports/`
- modele danych: `Utarg`, `KosztPracownika`, `Faktura`
- baza danych SQLite + SQLAlchemy
- dodawanie danych z terminala (menu: 1–2–3)
- miesięczny raport z wskaźnikami (4)
- repozytorium na GitHubie z obsługą SSH

---

## 🟡 Etap 2 – Odczyt PDF

**Cel:**  
Wrzucenie faktury PDF i automatyczne odczytanie danych

**Zadania:**
- [ ] Konfiguracja biblioteki (`PyMuPDF` / `pdfminer` / `pdfplumber`)
- [ ] Wybór folderu/faktury do przetworzenia
- [ ] Wyciągnięcie z PDF: daty, kwoty, firmy
- [ ] Wyświetlenie danych w terminalu

---

## 🟡 Etap 3 – Automatyczna kategoryzacja faktur

**Cel:**  
Przypisywanie faktur do kategorii na podstawie nazw firm

**Zadania:**
- [ ] Prosty system reguł (np. `"Coca-Cola" -> towar`)
- [ ] Możliwość korekty kategorii ręcznie
- [ ] Zapis do bazy jako `Faktura`

---

## 🔵 Etap 4 – Dashboard webowy (Flask)

**Cel:**  
Przeglądanie i dodawanie danych przez przeglądarkę

**Zadania:**
- [ ] Frontend (HTML + CSS lub Tailwind)
- [ ] Widoki: lista utargów, koszty, faktury
- [ ] Formularze do dodawania danych i wrzucania PDF
- [ ] Prosty system logowania

---

## 🔵 Etap 5 – Eksport i Docker

**Cel:**  
Przygotowanie projektu do działania w wielu lokalach lub chmurze

**Zadania:**
- [ ] Eksport raportów do pliku (CSV / PDF)
- [ ] Konteneryzacja w Dockerze
- [ ] Obsługa wielu lokali
- [ ] Wersje językowe (opcjonalnie)

---

## 🚀 Cel końcowy:
Kompletny system gastronomiczny z możliwością automatyzacji i analiz — gotowy do skalowania 💼📈
