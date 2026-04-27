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


SINGLE_ITEMS = {
    "LME 3M Aluminium (USD/t)": {
        "section": "LME",
        "item": "LMEselect Aluminum 3 Month",
    },
    "SMM A00 Aluminum Ingot (USD/t)": {
        "section": "Aluminum Ingot",
        "item": "SMM A00 Aluminum Ingot",
    },
}


GROUPS = {
    "Alumina": {
        "section": "SMM Aluminum Index",
        "items": [
            "SMM Alumina Index (Al₂O₃≥98.5%)",
            "SMM Shandong Alumina Index (Al₂O₃≥98.5%)",
            "SMM Henan Alumina Index (Al₂O₃≥98.5%)",
            "SMM Shanxi Alumina Index (Al₂O₃≥98.5%)",
            "SMM Guangxi Alumina Index (Al₂O₃≥98.5%)",
            "SMM Guizhou Alumina Index (Al₂O₃≥98.5%)",
        ],
    },
    "Prebaked Anode": {
        "section": "Prebaked Anode",
        "items": [
            "East China Prebaked Anode",
            "Central China Prebaked Anode",
            "Southwest China Prebaked Anode",
            "Northwest China Prebaked Anode",
            "Prebaked Anode for High-Purity Aluminum FOB China",
            "Prebaked Anode for High-end Aluminum FOB China",
        ],
    },
    "Calcined Petroleum Coke": {
        "section": "Calcined Petroleum Coke",
        "items": [
            "Northeast China Low-Sulfur Calcined Petroleum Coke",
            "East China Medium-Sulfur Ordinary Calcined Petroleum Coke",
            "East China Medium-Sulfur Low Vanadium Calcined Petroleum Coke",
            "East China Medium-High Sulfur Ordinary Calcined Petroleum Coke",
            "East China Medium-High Sulfur Low Vanadium Calcined Petroleum Coke",
            "East China High Sulfur Ordinary Calcined Petroleum Coke",
        ],
    },
    "Coal Tar Pitch": {
        "section": "Coal Tar Pitch",
        "items": [
            "Coal tar pitch (Shandong)",
            "Coal tar pitch (Shanxi)",
            "Coal tar pitch (Hebei)",
        ],
    },
    "Caustic Soda": {
        "section": "Caustic Soda",
        "items": [
            "Shandong 32% Ion-Membrane Process Caustic Soda Solution POT",
            "Shandong 50% Ion-Membrane Process Caustic Soda Solution POT",
            "Henan 32% Membrane Grade Liquid Caustic Soda",
            "Shanxi 32% Membrane Grade Liquid Caustic Soda",
            "Guangxi 32% Membrane Grade Liquid Caustic Soda",
        ],
    },
}


def clean(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def to_float(value):
    try:
        return float(str(value).replace(",", "").replace("+", "").strip())
    except Exception:
        return None


def is_date_line(text):
    return bool(re.search(r"\d{1,2}/\d{1,2}/\d{4}", str(text)))


def is_unit_line(text):
    t = str(text).lower()
    return any(
        u in t
        for u in [
            "usd/tonne",
            "usd/dmt",
            "usd/kg",
            "cny/mt",
            "us cent/lb",
            "thb/kg",
            "myr/kg",
        ]
    )


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


def click_section(page, section_name):
    print(f"Opening section: {section_name}")

    try:
        locator = page.locator(f"xpath=//*[normalize-space(text())='{section_name}']")
        count = locator.count()

        if count == 0:
            print(f"Section not found: {section_name}")
            return False

        # Prefer first visible item from left menu / visible page
        for i in range(count):
            item = locator.nth(i)
            try:
                if item.is_visible():
                    item.scroll_into_view_if_needed(timeout=5000)
                    item.click(timeout=5000)
                    page.wait_for_timeout(3500)
                    return True
            except Exception:
                pass

        locator.first.click(timeout=5000)
        page.wait_for_timeout(3500)
        return True

    except Exception as e:
        print(f"Could not open section {section_name}: {e}")
        return False


def get_page_lines(page):
    text = page.locator("body").inner_text(timeout=30000)
    lines = [clean(x) for x in text.splitlines()]
    return [x for x in lines if x]


def extract_item_average_from_lines(lines, item_name):
    """
    Expected visible table structure:
    Item Name
    SMM Code
    Unit
    High
    Low
    Average / Index / Latest
    Change
    Date

    For normal table: take 3rd numeric after Unit = Average.
    For index/LME style: take 1st numeric after Unit if only Index/Latest exists.
    """
    item_lower = item_name.strip().lower()

    for i, line in enumerate(lines):
        if line.strip().lower() == item_lower:
            block = lines[i : min(i + 16, len(lines))]

            unit_seen = False
            nums_after_unit = []

            for b in block[1:]:
                if re.search(r"SMM-[A-Z]+-[A-Z]+-\d+", b):
                    continue

                if is_unit_line(b):
                    unit_seen = True
                    continue

                if is_date_line(b):
                    break

                if not unit_seen:
                    continue

                val = to_float(b)

                if val is not None:
                    nums_after_unit.append(val)

           # Strict: only accept Average (3rd value)
if len(nums_after_unit) >= 3:
    avg = nums_after_unit[2]

    # Reject obvious wrong values (change-like small numbers)
    if avg > 50:   # threshold for real price
        return avg

# If we don't get valid average → return None
return None


def capture_single(page, section, item):
    click_section(page, section)
    lines = get_page_lines(page)
    return extract_item_average_from_lines(lines, item)


def capture_group(page, group_name, section, items):
    click_section(page, section)
    lines = get_page_lines(page)

    rows = []
    values = []

    for item in items:
        value = extract_item_average_from_lines(lines, item)

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
    DATA_DIR.mkdir(exist_ok=True)
    today = datetime.today().strftime("%Y-%m-%d")

    dashboard_row = {"Date": today}
    granular_rows = []

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

        # Single values
        for col, cfg in SINGLE_ITEMS.items():
            dashboard_row[col] = capture_single(page, cfg["section"], cfg["item"])

        # Group values
        for group_name, cfg in GROUPS.items():
            avg, rows = capture_group(page, group_name, cfg["section"], cfg["items"])
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

        text = page.locator("body").inner_text(timeout=30000)
        html = page.content()

        DEBUG_TEXT_FILE.write_text(text, encoding="utf-8")
        DEBUG_HTML_FILE.write_text(html, encoding="utf-8")

        browser.close()

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
