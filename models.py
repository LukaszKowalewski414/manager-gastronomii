#DEFINICJE TABEL
#enum słuy do kategoryzacji, date do przechowywania dat

from sqlalchemy import Column, Integer, Float, String, Date, Enum
from sqlalchemy.ext.declarative import declarative_base
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
