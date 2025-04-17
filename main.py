from models import Base
from database import engine

def init_db():
    Base.metadata.create_all(engine)
    print("Baza danych gotowa!")

if __name__ == "__main__":
    init_db()
