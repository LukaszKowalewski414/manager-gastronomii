import json
import os

NIP_CATEGORIES_FILE = "utils/data/nip_categories.json"

def get_category_for_nip(nip: str) -> str | None:
    if not os.path.exists(NIP_CATEGORIES_FILE):
        return None
    with open(NIP_CATEGORIES_FILE) as f:
        data = json.load(f)
    return data.get(nip)

def save_category_for_nip(nip: str, category: str):
    if os.path.exists(NIP_CATEGORIES_FILE):
        with open(NIP_CATEGORIES_FILE) as f:
            data = json.load(f)
    else:
        data = {}
    data[nip] = category
    with open(NIP_CATEGORIES_FILE, "w") as f:
        json.dump(data, f, indent=2)
