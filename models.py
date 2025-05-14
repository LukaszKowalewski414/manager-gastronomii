#DEFINICJE TABEL
#enum słuy do kategoryzacji, date do przechowywania dat

from sqlalchemy import Column, Integer, Float, String, Date, Enum
from sqlalchemy.orm import declarative_base
import enum

#wszystkie tabele muszą dziedziczyć po base zeby sql lite traktował
#je jako tabele w bazie
Base = declarative_base()

class KategoriaPracownika(enum.Enum):
    bar = "bar"
    kelnerzy = "kelnerzy"
    marketing = "marketing"
    inne = "inne"

class KategoriaFaktury(enum.Enum):
    towar = "towar"
    lokal = "lokal"
    marketing = "marketing"
    podatki = "podatki"
    inne = "inne"

class Utarg(Base):
    __tablename__ = "utargi"
    id = Column(Integer, primary_key=True)
    data = Column(Date, nullable=False)
    bar = Column(Float, default=0.0)
    bramka = Column(Float, default=0.0)

class KosztPracownika(Base):
    __tablename__ = "koszty_pracownikow"
    id = Column(Integer, primary_key=True)
    data = Column(Date, nullable=False)
    kwota = Column(Float, nullable=False)
    kategoria = Column(Enum(KategoriaPracownika), nullable=False)

class Faktura(Base):
    __tablename__ = "faktury"
    id = Column(Integer, primary_key=True)
    data = Column(Date, nullable=False)
    kwota = Column(Float, nullable=False)
    kategoria = Column(Enum(KategoriaFaktury), nullable=False)

class Dostawca(Base):
    __tablename__ = "dostawcy"

    id = Column(Integer, primary_key=True)
    company_name = Column(String, nullable=False, unique=True)
    nip = Column(String, nullable=False)
    kategoria = Column(Enum(KategoriaFaktury), nullable=False)


class Invoice(Base):
    __tablename__ = 'invoices'

    id = Column(Integer, primary_key=True)
    filename = Column(String)
    invoice_date = Column(Date)
    gross_amount = Column(Float)
    net_amount = Column(Float)
    supplier_nip = Column(String)
    supplier_name = Column(String)
    category = Column(String)


class Revenue(Base):
    __tablename__ = 'revenues'

    id = Column(Integer, primary_key=True)
    revenue_date = Column(Date)
    amount = Column(Float)
    revenue_type = Column(String)


class EmployeeCost(Base):
    __tablename__ = 'employee_costs'

    id = Column(Integer, primary_key=True)
    cost_date = Column(Date)
    amount = Column(Float)
    department = Column(String)

class RozliczenieDzien(Base):
    __tablename__ = 'rozliczenia_dzienne'

    id = Column(Integer, primary_key=True)
    data = Column(Date, nullable=False, unique=True)

    # Przychody
    sprzedaz_bar = Column(Float)
    sprzedaz_kuchnia = Column(Float)
    sprzedaz_wejsciowki = Column(Float)
    sprzedaz_inne = Column(Float)

    # Koszty
    koszt_bar = Column(Float)
    koszt_kelnerzy = Column(Float)
    koszt_kuchnia = Column(Float)
    koszt_marketing = Column(Float)
    koszt_marketing_komentarz = Column(String)
    koszt_ochrona = Column(Float)
    koszt_inne = Column(Float)
    koszt_inne_komentarz = Column(String)
