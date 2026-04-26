from datetime import datetime
import re

import pandas as pd
from playwright.sync_api import sync_playwright


URL = "https://www.metal.com/Aluminum?currency_type=2"

TARGETS = {
    "SMM Aluminum Index (USD/t)": "SMM Aluminum Index",
    "Petroleum Coke Index (USD/t)": "Petroleum Coke Index",
    "Prebaked Anode (USD/t)": "Prebaked Anode",
    "Coal Tar Pitch (USD/t)": "Coal Tar Pitch",
}


def clean(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def extract_number_after_keyword(full_text, keyword):
    idx = full_text.lower().find(keyword.lower())

    if idx == -1:
        return None

    snippet = full_text[idx: idx + 180]

    numbers = re.findall(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?", snippet)

    if not numbers:
        return None

    for n in numbers:
        try:
            value = float(n.replace(",", ""))
            if value > 1:
                return value
        except Exception:
            continue

    return None


def fetch_visible_text():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page(
            viewport={"width": 1600, "height": 1200},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120 Safari/537.36"
            ),
        )

        page.set_default_timeout(15000)

        page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(8000)

        for _ in range(8):
            page.mouse.wheel(0, 1200)
            page.wait_for_timeout(1000)

        text = clean(page.locator("body").inner_text(timeout=15000))

        browser.close()

    return text


def main():
    full_text = fetch_visible_text()

    row = {"Date": datetime.today().strftime("%Y-%m-%d")}

    for column_name, keyword in TARGETS.items():
        row[column_name] = extract_number_after_keyword(full_text, keyword)

    df = pd.DataFrame([row])

    print("\nCaptured Data:")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
