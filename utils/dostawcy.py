from models import Dostawca, KategoriaFaktury
from database import Session

def prompt_category(kategorie: list[KategoriaFaktury]) -> KategoriaFaktury:
    for idx, kat in enumerate(kategorie, 1):
        print(f"{idx}) {kat.value}")
    while True:
        choice = input("> ").strip().lower()
        if choice.isdigit() and 1 <= int(choice) <= len(kategorie):
            return kategorie[int(choice) - 1]
        for kat in kategorie:
            if choice == kat.value.lower() or choice == kat.name.lower():
                return kat
        print("❗ Nieprawidłowy wybór, spróbuj ponownie.")

def get_or_create_dostawca(nip: str, company_name: str, session=None) -> KategoriaFaktury:
    own_session = session is None
    session = session or Session()
    try:
        dostawca = session.query(Dostawca).filter_by(nip=nip).first()
        if dostawca:
            return dostawca.kategoria

        print(f"\n🔍 Nieznany dostawca: \"{company_name}\" (NIP: {nip})")
        print("📌 Do której kategorii przypisać fakturę?")
        kategorie = list(KategoriaFaktury)
        selected = prompt_category(kategorie)

        nowy = Dostawca(
            company_name=company_name,
            nip=nip,
            kategoria=selected
        )
        session.add(nowy)
        session.commit()
        return selected

    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()
