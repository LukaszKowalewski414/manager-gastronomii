import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)

# 🔹 Główna funkcja używana przez dashboardy i formularz faktury
def get_use_netto(lokal):
    config = load_config()
    return config.get(lokal, {}).get("use_netto", False)

# 🔹 Zapis preferencji użytkownika dla danego lokalu
def set_use_netto(lokal, value: bool):
    config = load_config()
    if lokal not in config:
        config[lokal] = {}
    config[lokal]["use_netto"] = value
    save_config(config)

# ✅ Alias dla formularza – bardziej czytelna nazwa
def get_default_use_netto_for_invoice(lokal):
    return get_use_netto(lokal)

def set_default_use_netto_for_invoice(lokal, value: bool):
    set_use_netto(lokal, value)
