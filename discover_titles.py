import pandas as pd
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup


URL = "https://www.metal.com/Aluminum?currency_type=2"

DATA_DIR = Path("data")
OUT_FILE = DATA_DIR / "discovered_index_list.csv"


def is_valid_index(text):
    text = text.lower()

    valid_keywords = [
        "aluminium", "aluminum", "alumina", "bauxite",
        "cpc", "anode", "pitch",
        "scrap", "alloy", "billet", "rod", "plate",
        "premium", "index"
    ]

    invalid_keywords = [
        "announcement", "about", "contact", "policy",
        "terms", "privacy", "subscribe", "download",
        "copyright", "whatsapp", "email", "news",
        "report", "event"
    ]

    if any(x in text for x in invalid_keywords):
        return False

    if any(x in text for x in valid_keywords):
        return True

    return False


def clean(text):
    return " ".join(str(text).split())


def main():
    DATA_DIR.mkdir(exist_ok=True)

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(URL, headers=headers, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    candidates = []

    # Only pick structured blocks (tables / rows / spans)
    for tag in soup.find_all(["tr", "li", "div", "span"]):
        text = clean(tag.get_text())

        if len(text) < 5:
            continue

        if is_valid_index(text):
            candidates.append(text)

    # Remove duplicates
    seen = set()
    final = []

    for c in candidates:
        key = c.lower()
        if key not in seen:
            seen.add(key)
            final.append(c)

    rows = []

    for name in final:
        rows.append({
            "Section": "",
            "Sub Section": "",
            "Index Name": name,
            "Column Name": f"{name} (USD/t)",
            "Currency": "USD",
            "Unit": "t",
            "Source URL": URL,
            "Active": "TRUE",
            "Discovered At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Review Status": "Pending"
        })

    df = pd.DataFrame(rows)
    df.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")

    print(f"Filtered titles: {len(df)} saved.")


if __name__ == "__main__":
    main()
