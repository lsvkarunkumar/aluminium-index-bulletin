from datetime import datetime
from pathlib import Path
import os
import re

import pandas as pd
from playwright.sync_api import sync_playwright


URL = "https://www.metal.com/Aluminum?currency_type=2"

DATA_DIR = Path("data")
DASHBOARD_FILE = DATA_DIR / "latest_dashboard_capture.csv"
GRANULAR_FILE = DATA_DIR / "latest_granular_capture.csv"
DEBUG_TEXT_FILE = DATA_DIR / "debug_visible_text.txt"
DEBUG_HTML_FILE = DATA_DIR / "debug_page.html"

SMM_EMAIL = os.getenv("SMM_EMAIL", "")
SMM_PASSWORD = os.getenv("SMM_PASSWORD", "")


SINGLE_CAPTURE = {
    "LME 3M Aluminium (USD/t)": ["LMEselect Aluminum 3 Month", "LMEselect Aluminum Month"],
    "SMM A00 Aluminum Ingot (USD/t)": ["SMM A00 Aluminum Ingot"],
}


GROUPS = {
    "Alumina": [
        "SMM Alumina Index (Al₂O₃≥98.5%)",
        "SMM Shandong Alumina (Al₂O₃≥98.5%)",
        "SMM Henan Alumina (Al₂O₃≥98.5%)",
        "SMM Shanxi Alumina (Al₂O₃≥98.5%)",
        "SMM Guangxi Alumina (Al₂O₃≥98.5%)",
        "SMM Guizhou Alumina (Al₂O₃≥98.5%)",
    ],
    "Prebaked Anode": [
        "East China Prebaked Anode",
        "Central China Prebaked Anode",
        "Southwest China Prebaked Anode",
        "Northwest China Prebaked Anode",
        "Prebaked Anode for High-Purity Aluminum FOB China",
        "Prebaked Anode for High-end Aluminum FOB China",
    ],
    "Calcined Petroleum Coke": [
        "Northeast China Low-Sulfur Calcined Petroleum Coke",
        "East China Medium-Sulfur Ordinary Calcined Petroleum Coke",
        "East China Medium-Sulfur Low Vanadium Calcined Petroleum Coke",
        "East China Medium-High Sulfur Ordinary Calcined Petroleum Coke",
        "East China Medium-High Sulfur Low Vanadium Calcined Petroleum Coke",
        "East China High Sulfur Ordinary Calcined Petroleum Coke",
    ],
    "Coal Tar Pitch": [
        "Coal tar pitch (Shandong)",
        "Coal tar pitch (Shanxi)",
        "Coal tar pitch (Hebei)",
    ],
    "Caustic Soda": [
        "Shandong 32% Ion-Membrane Process Caustic Soda Solution POT",
        "Shandong 50% Ion-Membrane Process Caustic Soda Solution POT",
        "Henan 32% Membrane Grade Liquid Caustic Soda",
        "Shanxi 32% Membrane Grade Liquid Caustic Soda",
        "Guangxi 32% Membrane Grade Liquid Caustic Soda",
    ],
}


def clean(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def to_float(value):
    try:
        return float(str(value).replace(",", "").replace("+", "").strip())
    except Exception:
        return None


def login_if_possible(page):
    if not SMM_EMAIL or not SMM_PASSWORD:
        print("No login secrets found. Continuing without login.")
        return

    try:
        print("Attempting SMM login...")

        page.locator("button.signInButton").first.click(timeout=10000)
        page.wait_for_timeout(3000)

        inputs = page.locator("input")

        if inputs.count() < 2:
            print("Login input fields not found.")
            return

        inputs.nth(0).fill(SMM_EMAIL)
        inputs.nth(1).fill(SMM_PASSWORD)

        buttons = page.locator("button").all()
        clicked = False

        for btn in buttons:
            try:
                txt = btn.inner_text(timeout=1000).strip().lower()
                if txt in ["sign in", "login", "log in"]:
                    btn.click(timeout=3000)
                    clicked = True
                    break
            except Exception:
                pass

        if not clicked:
            page.keyboard.press("Enter")

        page.wait_for_timeout(10000)
        print("Login attempt completed.")

    except Exception as e:
        print(f"Login attempt skipped/failed: {e}")


def fetch_visible_lines():
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
        page.wait_for_timeout(8000)

        login_if_possible(page)

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(10000)

        for _ in range(12):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(900)

        text = page.locator("body").inner_text(timeout=30000)
        html = page.content()

        DEBUG_TEXT_FILE.write_text(text, encoding="utf-8")
        DEBUG_HTML_FILE.write_text(html, encoding="utf-8")

        browser.close()

    lines = [clean(x) for x in text.splitlines()]
    lines = [x for x in lines if x]

    return lines


def extract_top_smm_a00(lines):
    for i, line in enumerate(lines):
        if line.strip().lower() == "aluminum ingot / smm a00 aluminum ingot":
            for j in range(i + 1, min(i + 8, len(lines))):
                val = to_float(lines[j])
                if val is not None and val > 500:
                    return val
    return None


def extract_single_from_lines(lines, keywords):
    for keyword in keywords:
        if keyword == "SMM A00 Aluminum Ingot":
            val = extract_top_smm_a00(lines)
            if val is not None:
                return val

        for i, line in enumerate(lines):
            if keyword.lower() in line.lower():
                for j in range(i + 1, min(i + 10, len(lines))):
                    val = to_float(lines[j])
                    if val is not None and val > 500:
                        return val

    return None


def find_item_block(lines, item_name):
    for i, line in enumerate(lines):
        if line.strip().lower() == item_name.strip().lower():
            return lines[i : min(i + 12, len(lines))]
    return []


def extract_price_from_item_block(block):
    if not block:
        return None

    useful_numbers = []

    for line in block:
        if re.search(r"SMM-[A-Z]+-[A-Z]+-\d+", line):
            continue

        if "/" in line and re.search(r"\d{1,2}/\d{1,2}/\d{4}", line):
            continue

        if any(
            unit in line.lower()
            for unit in [
                "usd/tonne",
                "usd/dmt",
                "usd/kg",
                "cny/mt",
                "thb/kg",
                "myr/kg",
                "us cent/lb",
            ]
        ):
            continue

        val = to_float(line)

        if val is None:
            continue

        useful_numbers.append(val)

    if len(useful_numbers) >= 3:
        return useful_numbers[2]

    return None


def extract_group_values(lines, group_name, items):
    rows = []
    values = []

    for item in items:
        block = find_item_block(lines, item)
        value = extract_price_from_item_block(block)

        rows.append(
            {
                "Group": group_name,
                "Item": item,
                "Value": value,
            }
        )

        if value is not None:
            values.append(value)

    avg = sum(values) / len(values) if values else None
    return avg, rows


def main():
    lines = fetch_visible_lines()
    today = datetime.today().strftime("%Y-%m-%d")

    dashboard_row = {"Date": today}
    granular_rows = []

    for column_name, keywords in SINGLE_CAPTURE.items():
        dashboard_row[column_name] = extract_single_from_lines(lines, keywords)

    for group_name, items in GROUPS.items():
        avg, rows = extract_group_values(lines, group_name, items)
        dashboard_row[f"{group_name} Avg (USD/t)"] = avg

        for row in rows:
            granular_rows.append(
                {
                    "Date": today,
                    "Group": row["Group"],
                    "Item": row["Item"],
                    "Value": row["Value"],
                    "Currency": "USD",
                    "Unit": "t",
                    "Source": URL,
                }
            )

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
