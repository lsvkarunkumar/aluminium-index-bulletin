from datetime import datetime
from pathlib import Path
import re

import pandas as pd
from playwright.sync_api import sync_playwright


URL = "https://www.metal.com/Aluminum?currency_type=2"

DATA_DIR = Path("data")
DEBUG_TEXT_FILE = DATA_DIR / "debug_visible_text.txt"
DEBUG_HTML_FILE = DATA_DIR / "debug_page.html"


TARGETS = {
    "SMM Aluminum Index (USD/t)": "SMM Aluminum Index",
    "Petroleum Coke Index (USD/t)": "Petroleum Coke Index",
    "Prebaked Anode (USD/t)": "Prebaked Anode",
    "Coal Tar Pitch (USD/t)": "Coal Tar Pitch",
}


def clean(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def fetch_debug_content():
    DATA_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page(
            viewport={"width": 1600, "height": 1400},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120 Safari/537.36"
            ),
        )

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(12000)

        for _ in range(10):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(1200)

        visible_text = page.locator("body").inner_text(timeout=20000)
        html = page.content()

        browser.close()

    DEBUG_TEXT_FILE.write_text(visible_text, encoding="utf-8")
    DEBUG_HTML_FILE.write_text(html, encoding="utf-8")

    return clean(visible_text)


def main():
    text = fetch_debug_content()

    print("Debug files created:")
    print(DEBUG_TEXT_FILE)
    print(DEBUG_HTML_FILE)

    print("\nKeyword check:")
    for _, keyword in TARGETS.items():
        found = keyword.lower() in text.lower()
        print(f"{keyword}: {found}")

    row = {"Date": datetime.today().strftime("%Y-%m-%d")}

    for col in TARGETS:
        row[col] = None

    df = pd.DataFrame([row])

    print("\nCaptured Data:")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
