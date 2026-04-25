from datetime import datetime
from pathlib import Path
import re

import pandas as pd
from playwright.sync_api import sync_playwright


URL = "https://www.metal.com/Aluminum?currency_type=2"

DATA_DIR = Path("data")
OUT_FILE = DATA_DIR / "discovered_index_list.csv"


def clean(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def is_valid_title(text):
    t = text.lower()

    if len(t) < 4 or len(t) > 100:
        return False

    invalid = [
        "announcement", "sign in", "download", "privacy", "terms",
        "copyright", "whatsapp", "subscribe", "methodology",
        "about us", "contact us", "sitemap", "news", "events"
    ]

    valid = [
        "aluminum", "aluminium", "alumina", "bauxite", "cpc",
        "anode", "pitch", "scrap", "alloy", "billet", "rod",
        "plate", "coil", "premium", "index", "ingot"
    ]

    if any(x in t for x in invalid):
        return False

    return any(x in t for x in valid)


def main():
    DATA_DIR.mkdir(exist_ok=True)

    titles = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1600, "height": 1200},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120 Safari/537.36"
            ),
        )

        page.goto(URL, wait_until="networkidle", timeout=90000)

        for _ in range(8):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(1500)

        elements = page.locator("body *").all()

        for el in elements:
            try:
                text = clean(el.inner_text(timeout=500))
                if is_valid_title(text):
                    titles.append(text)
            except Exception:
                continue

        browser.close()

    seen = set()
    rows = []

    for title in titles:
        key = title.lower()

        if key in seen:
            continue

        seen.add(key)

        rows.append(
            {
                "Section": "",
                "Sub Section": "",
                "Index Name": title,
                "Column Name": f"{title} (USD/t)",
                "Currency": "USD",
                "Unit": "t",
                "Source URL": URL,
                "Active": "TRUE",
                "Discovered At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Review Status": "Pending",
            }
        )

    df = pd.DataFrame(rows)
    df.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")

    print(f"Browser discovery completed. Rows saved: {len(df)}")


if __name__ == "__main__":
    main()
