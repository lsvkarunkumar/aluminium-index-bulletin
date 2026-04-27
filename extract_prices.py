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


def to_float(value):
    try:
        cleaned = str(value).replace(",", "").replace("+", "").strip()
        if cleaned in ["", "-", "--", "Sign In"]:
            return None
        return float(cleaned)
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


def click_section(page, section_name):
    print(f"Opening section: {section_name}")

    try:
        locator = page.locator(f"xpath=//*[normalize-space(text())='{section_name}']")
        count = locator.count()

        if count == 0:
            print(f"Section not found: {section_name}")
            return False

        for i in range(count):
            item = locator.nth(i)
            try:
                if item.is_visible():
                    item.scroll_into_view_if_needed(timeout=5000)
                    item.click(timeout=5000)
                    page.wait_for_timeout(4000)
                    return True
            except Exception:
                pass

        locator.first.click(timeout=5000)
        page.wait_for_timeout(4000)
        return True

    except Exception as e:
        print(f"Could not open section {section_name}: {e}")
        return False


def extract_item_from_table(page, item_name):
    """
    Reads actual table rows, not body text.

    Expected columns:
    Name | Unit | High | Low | Average/Index/Latest | Change | Date

    Captures:
    - Average column where present
    - Index/Latest column for index/LME sections
    """
    possible_rows = [
        "table tbody tr",
        "div[role='row']",
        ".ant-table-row",
    ]

    for row_selector in possible_rows:
        rows = page.locator(row_selector)
        count = rows.count()

        if count == 0:
            continue

        for i in range(count):
            row = rows.nth(i)

            try:
                row_text = row.inner_text(timeout=1500)

                if item_name.lower() not in row_text.lower():
                    continue

                cells = row.locator("td")
                cell_count = cells.count()

                cell_texts = []

                if cell_count > 0:
                    for c in range(cell_count):
                        cell_texts.append(cells.nth(c).inner_text(timeout=1000).strip())
                else:
                    # fallback for div-based table rows
                    cell_texts = [
                        x.strip()
                        for x in row_text.splitlines()
                        if x.strip()
                    ]

                numeric_values = []

                for txt in cell_texts:
                    val = to_float(txt)
                    if val is not None:
                        numeric_values.append(val)

                # For Name | Unit | High | Low | Average | Change | Date:
                # numeric values should usually be [High, Low, Average, Change]
                if len(numeric_values) >= 3:
                    return numeric_values[2]

                # For index/LME style: Name | Unit | Index/Latest | Change | Date
                if len(numeric_values) >= 1:
                    first_val = numeric_values[0]
                    if abs(first_val) > 50:
                        return first_val

            except Exception:
                continue

    return None


def capture_single(page, section, item):
    click_section(page, section)
    page.wait_for_timeout(3000)
    return extract_item_from_table(page, item)


def capture_group(page, group_name, section, items):
    click_section(page, section)
    page.wait_for_timeout(3000)

    rows = []
    values = []

    for item in items:
        value = extract_item_from_table(page, item)

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

        for col, cfg in SINGLE_ITEMS.items():
            dashboard_row[col] = capture_single(page, cfg["section"], cfg["item"])

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
