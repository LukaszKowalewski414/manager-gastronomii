from sqlalchemy import Column, Integer, Float, String, Date, Enum
from sqlalchemy.orm import declarative_base
import enum

Base = declarative_base()

# ENUMY

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

# TABELA: Utarg (opcjonalna, używana tylko jeśli nadal działa)
class Utarg(Base):
    __tablename__ = "utargi"
    id = Column(Integer, primary_key=True)
    data = Column(Date, nullable=False)
    bar = Column(Float, default=0.0)
    bramka = Column(Float, default=0.0)

# TABELA: Koszty pracowników (starszy system)
class KosztPracownika(Base):
    __tablename__ = "koszty_pracownikow"
    id = Column(Integer, primary_key=True)
    data = Column(Date, nullable=False)
    kwota = Column(Float, nullable=False)
    kategoria = Column(Enum(KategoriaPracownika), nullable=False)

# TABELA: Faktura (starsza uproszczona wersja)
class Faktura(Base):
    __tablename__ = "faktury"
    id = Column(Integer, primary_key=True)
    data = Column(Date, nullable=False)
    kwota = Column(Float, nullable=False)
    kategoria = Column(Enum(KategoriaFaktury), nullable=False)

# TABELA: Dostawcy
class Dostawca(Base):
    __tablename__ = "dostawcy"
    id = Column(Integer, primary_key=True)
    company_name = Column(String, nullable=False, unique=True)
    nip = Column(String, nullable=False)
    kategoria = Column(Enum(KategoriaFaktury), nullable=False)

# TABELA: Invoice (faktury używane w systemie webowym)
class Invoice(Base):
    __tablename__ = 'invoices'

    id = Column(Integer, primary_key=True)
    invoice_date = Column(Date, nullable=False)  # zmienione z 'date'
    gross_amount = Column(Float, nullable=False)  # zmienione z 'amount_gross'
    net_amount = Column(Float, nullable=True)     # zmienione z 'amount_net'
    supplier = Column(String, nullable=True)
    nip = Column(String, nullable=True)
    category = Column(String, nullable=True)
    lokal = Column(String, nullable=False, default='Rokoko 2.0')

# TABELA: Revenue (przychody)
class Revenue(Base):
    __tablename__ = 'revenues'

    id = Column(Integer, primary_key=True)
    revenue_date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    revenue_type = Column(String, nullable=False)
    lokal = Column(String, nullable=False, default='Rokoko 2.0')  # dodane

# TABELA: EmployeeCost (jeśli używasz do raportowania)
class EmployeeCost(Base):
    __tablename__ = 'employee_costs'

    id = Column(Integer, primary_key=True)
    cost_date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    department = Column(String, nullable=False)
    lokal = Column(String, nullable=False, default='Rokoko 2.0')

# TABELA: Rozliczenie dzienne
class RozliczenieDzien(Base):
    __tablename__ = 'rozliczenia_dzienne'

    id = Column(Integer, primary_key=True)
    daily_date = Column(Date, nullable=False, unique=True)  # zmienione z 'data'

    # Przychody
    revenue_bar = Column(Float, default=0.0)
    revenue_kitchen = Column(Float, default=0.0)
    revenue_entry = Column(Float, default=0.0)
    revenue_other = Column(Float, default=0.0)
    revenue_other_comment = Column(String, nullable=True)

    # Koszty
    cost_bar = Column(Float, default=0.0)
    cost_waiters = Column(Float, default=0.0)
    cost_kitchen = Column(Float, default=0.0)
    cost_marketing = Column(Float, default=0.0)
    cost_marketing_comment = Column(String, nullable=True)
    cost_security = Column(Float, default=0.0)
    cost_other = Column(Float, default=0.0)
    cost_other_comment = Column(String, nullable=True)

    lokal = Column(String, nullable=False, default='Rokoko 2.0')
