from sqlalchemy import Column, Integer, Float, String, Date, Enum, Text, Boolean
from sqlalchemy.orm import declarative_base
import enum

Base = declarative_base()

# ===============================
# ENUMY
# ===============================

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

# ===============================
# TABELA: Utarg (starszy system)
# ===============================
class Utarg(Base):
    __tablename__ = "utargi"
    id = Column(Integer, primary_key=True)
    data = Column(Date, nullable=False)
    bar = Column(Float, default=0.0)
    bramka = Column(Float, default=0.0)

# ===============================
# TABELA: Koszty pracowników (starszy system)
# ===============================
class KosztPracownika(Base):
    __tablename__ = "koszty_pracownikow"
    id = Column(Integer, primary_key=True)
    data = Column(Date, nullable=False)
    kwota = Column(Float, nullable=False)
    kategoria = Column(Enum(KategoriaPracownika), nullable=False)

# ===============================
# TABELA: Faktura (starszy system)
# ===============================
class Faktura(Base):
    __tablename__ = "faktury"
    id = Column(Integer, primary_key=True)
    data = Column(Date, nullable=False)
    kwota = Column(Float, nullable=False)
    kategoria = Column(Enum(KategoriaFaktury), nullable=False)

# ===============================
# TABELA: Dostawcy
# ===============================
class Dostawca(Base):
    __tablename__ = "dostawcy"
    id = Column(Integer, primary_key=True)
    company_name = Column(String, nullable=False, unique=True)
    nip = Column(String, nullable=False)
    kategoria = Column(Enum(KategoriaFaktury), nullable=False)

# ===============================
# TABELA: Invoice (nowy system)
# ===============================
class Invoice(Base):
    __tablename__ = 'invoices'

    id = Column(Integer, primary_key=True)
    invoice_date = Column(Date)
    gross_amount = Column(Float)
    net_amount = Column(Float)
    supplier = Column(String)
    nip = Column(String)
    category = Column(String)
    goods_type = Column(String)
    lokal = Column(String)
    note = Column(Text)
    use_netto = Column(Boolean, default=False)

    # ✅ DODAJ TE POLA:
    invoice_number = Column(String)
    description = Column(String)


# ===============================
# TABELA: Revenue (nowy system)
# ===============================
class Revenue(Base):
    __tablename__ = 'revenues'

    id = Column(Integer, primary_key=True)
    revenue_date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    revenue_type = Column(String, nullable=False)
    lokal = Column(String, nullable=False, default='Rokoko 2.0')

# ===============================
# TABELA: Koszty pracowników (nowy system)
# ===============================
class EmployeeCost(Base):
    __tablename__ = 'employee_costs'

    id = Column(Integer, primary_key=True)
    cost_date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    department = Column(String, nullable=False)
    lokal = Column(String, nullable=False, default='Rokoko 2.0')

# ===============================
# TABELA: Rozliczenie dzienne
# ===============================
class RozliczenieDzien(Base):
    __tablename__ = 'rozliczenia_dzienne'

    id = Column(Integer, primary_key=True)
    daily_date = Column(Date, nullable=False)

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

    # Liczba pracowników
    staff_bar = Column(Integer, nullable=True)
    staff_kitchen = Column(Integer, nullable=True)
    staff_waiters = Column(Integer, nullable=True)
    staff_security = Column(Integer, nullable=True)

    # Notatka
    notatka = Column(Text, nullable=True)

    # Lokal (kluczowe!)
    lokal = Column(String, nullable=False, default='Rokoko 2.0')


