from utils.utargi import dodaj_utarg
from utils.koszty import dodaj_koszt_pracownika
from utils.faktury import dodaj_fakture
from utils.raport import raport_miesieczny
# from utils.koszty import dodaj_koszt_pracownika (dodamy za chwilę)
# from utils.faktury import dodaj_fakture (dodamy później)

def menu():
    while True:
        print("\n=== MANAGER GASTRONOMII ===")
        print("1. Dodaj utarg")
        print("2. Dodaj koszt pracownika")
        print("3. Dodaj fakturę")
        print("4. Generuj raport miesięczny")
        print("0. Wyjście")

        wybor = input("Wybierz opcję: ")

        if wybor == "1":
            dodaj_utarg()
        elif wybor == "2":
            dodaj_koszt_pracownika()
        elif wybor == "3":
            dodaj_fakture()
        elif wybor == "4":
            raport_miesieczny()
        elif wybor == "0":
            print("Zamykam program.")
            break
        else:
            print("Nieprawidłowy wybór.")

if __name__ == "__main__":
    menu()
