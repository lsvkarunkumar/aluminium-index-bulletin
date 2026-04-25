from datetime import datetime
from pathlib import Path
import re

import pandas as pd
import requests
from bs4 import BeautifulSoup


SOURCE_URL = "https://www.metal.com/Aluminum?currency_type=2"

DATA_DIR = Path("data")
DISCOVERY_FILE = DATA_DIR / "discovered_index_list.csv"


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text


def make_column_name(index_name: str) -> str:
    name = clean_text(index_name)
    name = name.replace("Price", "").strip()
    return f"{name} (USD/t)"


def discover_titles():
    DATA_DIR.mkdir(exist_ok=True)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    response = requests.get(SOURCE_URL, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    possible_titles = []

    for tag in soup.find_all(["h1", "h2", "h3", "h4", "a", "span", "div"]):
        text = clean_text(tag.get_text(" ", strip=True))

        if not text:
            continue

        if len(text) < 4:
            continue

        keywords = [
            "Aluminium",
            "Aluminum",
            "Alumina",
            "Bauxite",
            "CPC",
            "Anode",
            "Pitch",
            "Scrap",
            "ADC",
            "Alloy",
            "Billet",
            "Rod",
            "Plate",
            "Coil",
            "Premium",
            "Index",
        ]

        if any(k.lower() in text.lower() for k in keywords):
            possible_titles.append(text)

    unique_titles = []
    seen = set()

    for title in possible_titles:
        title_key = title.lower()

        if title_key not in seen:
            seen.add(title_key)
            unique_titles.append(title)

    rows = []

    for title in unique_titles:
        rows.append(
            {
                "Section": "",
                "Sub Section": "",
                "Index Name": title,
                "Column Name": make_column_name(title),
                "Currency": "USD",
                "Unit": "t",
                "Source URL": SOURCE_URL,
                "Active": "TRUE",
                "Discovered At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Review Status": "Pending",
            }
        )

    df = pd.DataFrame(rows)

    df.to_csv(DISCOVERY_FILE, index=False, encoding="utf-8-sig")

    print(f"Discovery completed. {len(df)} possible titles saved.")
    print(f"Output file: {DISCOVERY_FILE}")


if __name__ == "__main__":
    discover_titles()
