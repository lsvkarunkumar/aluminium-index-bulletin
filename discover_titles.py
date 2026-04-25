import pandas as pd
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup


URL = "https://www.metal.com/Aluminum?currency_type=2"

DATA_DIR = Path("data")
OUT_FILE = DATA_DIR / "discovered_index_list.csv"


def clean(text):
    return " ".join(str(text).split())


def is_valid_index(text):
    t = text.lower()

    valid_keywords = [
        "aluminium", "aluminum", "alumina", "bauxite",
        "cpc", "anode", "pitch", "scrap", "alloy",
        "billet", "rod", "plate", "coil", "premium", "index"
    ]

    invalid_keywords = [
        "announcement", "about us", "contact", "policy",
        "terms", "privacy", "subscribe", "download app",
        "copyright", "whatsapp", "sitemap", "sign in",
        "methodology", "events", "news and reports"
    ]

    if any(x in t for x in invalid_keywords):
        return False

    return any(x in t for x in valid_keywords)


def main():
    DATA_DIR.mkdir(exist_ok=True)

    rows = []

    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(URL, headers=headers, timeout=30)
        print("Status code:", response.status_code)
        print("HTML length:", len(response.text))

        soup = BeautifulSoup(response.text, "html.parser")

        candidates = []

        for tag in soup.find_all(["tr", "li", "div", "span", "a"]):
            text = clean(tag.get_text(" ", strip=True))

            if len(text) < 5:
                continue

            if len(text) > 120:
                continue

            if is_valid_index(text):
                candidates.append(text)

        seen = set()

        for name in candidates:
            key = name.lower()

            if key in seen:
                continue

            seen.add(key)

            rows.append(
                {
                    "Section": "",
                    "Sub Section": "",
                    "Index Name": name,
                    "Column Name": f"{name} (USD/t)",
                    "Currency": "USD",
                    "Unit": "t",
                    "Source URL": URL,
                    "Active": "TRUE",
                    "Discovered At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Review Status": "Pending",
                }
            )

    except Exception as e:
        print("Discovery failed:", str(e))

    df = pd.DataFrame(
        rows,
        columns=[
            "Section",
            "Sub Section",
            "Index Name",
            "Column Name",
            "Currency",
            "Unit",
            "Source URL",
            "Active",
            "Discovered At",
            "Review Status",
        ],
    )

    df.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")

    print(f"Discovery completed. Rows saved: {len(df)}")
    print(f"Output file: {OUT_FILE}")


if __name__ == "__main__":
    main()
