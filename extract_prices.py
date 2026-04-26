from datetime import datetime
from pathlib import Path
import re
import pandas as pd
from playwright.sync_api import sync_playwright


URL = "https://www.metal.com/Aluminum?currency_type=2"

DATA_DIR = Path("data")
DASHBOARD_FILE = DATA_DIR / "latest_dashboard_capture.csv"
GRANULAR_FILE = DATA_DIR / "latest_granular_capture.csv"
DEBUG_TEXT_FILE = DATA_DIR / "debug_visible_text.txt"

SINGLE_CAPTURE = {
    "LME 3M Aluminium (USD/t)": ["LMEselect Aluminum 3 Month", "LMEselect Aluminum Month"],
    "SMM Aluminium Index (USD/t)": ["Aluminum Ingot / SMM A00 Aluminum Ingot"],
}

GROUPS = {
    "Alumina": ["SMM Alumina Index", "SMM Shandong Alumina", "SMM Henan Alumina", "SMM Shanxi Alumina", "SMM Guangxi Alumina", "SMM Guizhou Alumina"],
    "Prebaked Anode": ["East China Prebaked Anode", "Central China Prebaked Anode", "Southwest China Prebaked Anode", "Northwest China Prebaked Anode", "Prebaked Anode for High-Purity Aluminum FOB China", "Prebaked Anode for High-end Aluminum FOB China"],
    "Calcined Petroleum Coke": ["Northeast China Low-Sulfur Calcined Petroleum Coke", "East China Medium-Sulfur Ordinary Calcined Petroleum Coke", "East China Medium-Sulfur Low Vanadium Calcined Petroleum Coke", "East China Medium-High Sulfur Ordinary Calcined Petroleum Coke", "East China Medium-High Sulfur Low Vanadium Calcined Petroleum Coke", "East China High Sulfur Ordinary Calcined Petroleum Coke"],
    "Coal Tar Pitch": ["Coal tar pitch (Shandong)", "Coal tar pitch (Shanxi)", "Coal tar pitch (Hebei)"],
    "Caustic Soda": ["Caustic Soda", "Shandong 32% Ion-Membrane Process Caustic Soda", "Shandong 50% Ion-Membrane Process Caustic Soda", "Shanxi 32% Membrane Grade Liquid Caustic Soda", "Guangxi 32% Membrane Grade Liquid Caustic Soda"],
}


def clean(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def to_number(value):
    try:
        return float(str(value).replace(",", "").replace("+", "").strip())
    except Exception:
        return None


def fetch_visible_text():
    DATA_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1600, "height": 1400},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        )

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(12000)

        for _ in range(10):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(1000)

        text = page.locator("body").inner_text(timeout=20000)
        browser.close()

    DEBUG_TEXT_FILE.write_text(text, encoding="utf-8")
    return text


def extract_single_value(text, keywords):
    flat = clean(text)

    for keyword in keywords:
        idx = flat.lower().find(keyword.lower())
        if idx == -1:
            continue

        snippet = flat[idx: idx + 220]
        nums = re.findall(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?", snippet)

        for n in nums:
            val = to_number(n)
            if val and val > 100:
                return val

    return None


def extract_item_value(text, item_name):
    """
    Tries to capture actual price/index/average.
    Important: does NOT use Change as price.
    If page exposes only Change and Date, returns None.
    """
    flat = clean(text)
    idx = flat.lower().find(item_name.lower())

    if idx == -1:
        return None

    snippet = flat[idx: idx + 260]

    # Pattern tries to capture numbers before date, excluding small change-like values
    nums = re.findall(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?", snippet)

    candidates = []
    for n in nums:
        val = to_number(n)
        if val is not None:
            candidates.append(val)

    # Reject obvious SMM code fragments and tiny change values.
    price_candidates = [x for x in candidates if x >= 50]

    if not price_candidates:
        return None

    return price_candidates[0]


def average(values):
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def main():
    text = fetch_visible_text()
    today = datetime.today().strftime("%Y-%m-%d")

    dashboard_row = {"Date": today}
    granular_rows = []

    # Single captures
    for col, keywords in SINGLE_CAPTURE.items():
        dashboard_row[col] = extract_single_value(text, keywords)

    # Group captures
    for group_name, items in GROUPS.items():
        values = []

        for item in items:
            value = extract_item_value(text, item)
            values.append(value)

            granular_rows.append(
                {
                    "Date": today,
                    "Group": group_name,
                    "Item": item,
                    "Value": value,
                    "Currency": "USD",
                    "Unit": "t",
                    "Source": URL,
                }
            )

        dashboard_row[f"{group_name} Avg (USD/t)"] = average(values)

    dashboard_df = pd.DataFrame([dashboard_row])
    granular_df = pd.DataFrame(granular_rows)

    dashboard_df.to_csv(DASHBOARD_FILE, index=False)
    granular_df.to_csv(GRANULAR_FILE, index=False)

    print("\nDashboard Capture:")
    print(dashboard_df.to_string(index=False))

    print("\nGranular Capture:")
    print(granular_df.to_string(index=False))


if __name__ == "__main__":
    main()
