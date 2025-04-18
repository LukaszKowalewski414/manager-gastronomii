#POŁĄCZENIE Z SQL LITE

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Tworzenie folderu na bazę danych, jeśli nie istnieje
os.makedirs("data", exist_ok=True)

engine = create_engine("sqlite:///data/food_cost.db")
Session = sessionmaker(bind=engine)
