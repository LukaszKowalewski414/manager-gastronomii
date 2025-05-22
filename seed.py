#PLIK DO TESTÓW W DASHBOARDZIE

from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Invoice, Revenue, RozliczenieDzien

# 🔌 Połączenie z bazą
engine = create_engine("sqlite:///data/food_cost.db")
Session = sessionmaker(bind=engine)
db_session = Session()

# 🧾 Faktura (Invoice)
invoice = Invoice(
    invoice_date=date(2025, 4, 10),
    gross_amount=1234.56,
    net_amount=1000.00,
    supplier="Test Sp. z o.o.",
    nip="1234567890",
    category="towar",
    lokal="Rokoko 2.0"
)

# 💰 Przychód (Revenue)
revenue = Revenue(
    revenue_date=date(2025, 4, 10),
    amount=8000.00,
    revenue_type="sprzedaz_bar",
    lokal="Rokoko 2.0"
)

# 📊 Rozliczenie dzienne (RozliczenieDzien)
rozliczenie = RozliczenieDzien(
    daily_date=date(2025, 4, 10),
    revenue_bar=5000,
    revenue_kitchen=2000,
    revenue_entry=800,
    revenue_other=200,

    cost_bar=1500,
    cost_waiters=600,
    cost_kitchen=700,
    cost_marketing=300,
    comment_marketing="social media",
    cost_security=400,
    cost_other=100,
    comment_other="naprawa kranu",

    lokal="Rokoko 2.0"
)

# 💾 Zapis do bazy
db_session.add_all([invoice, revenue, rozliczenie])
db_session.commit()
db_session.close()

print("✅ Dodano dane testowe do bazy.")
