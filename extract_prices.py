from datetime import datetime
from pathlib import Path
import os
import re

import pandas as pd
from playwright.sync_api import sync_playwright


BASE_URL = "https://www.metal.com/Aluminum?currency_type=2"

DATA_DIR = Path("data")
DASHBOARD_FILE = DATA_DIR / "latest_dashboard_capture.csv"
GRANULAR_FILE = DATA_DIR / "latest_granular_capture.csv"
DEBUG_TEXT_FILE = DATA_DIR / "debug_visible_text.txt"
DEBUG_HTML_FILE = DATA_DIR / "debug_page.html"

SMM_EMAIL = os.getenv("SMM_EMAIL", "")
SMM_PASSWORD = os.getenv("SMM_PASSWORD", "")


SINGLE_ITEMS = {
    "LME 3M Aluminium (USD/t)": {
        "anchor": "#LME",
        "item": "LMEselect Aluminum 3 Month",
    },
    "SMM A00 Aluminum Ingot (USD/t)": {
        "anchor": "#AluminumIngot",
        "item": "SMM A00 Aluminum Ingot",
    },
}


GROUPS = {
    "Alumina": {
        "anchor": "#Alumina",
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
        "anchor": "#PrebakedAnode",
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
        "anchor": "#CalcinedPetroleumCoke",
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
        "anchor": "#CoalTarPitch",
        "items": [
            "Coal tar pitch (Shandong)",
            "Coal tar pitch (Shanxi)",
            "Coal tar pitch (Hebei)",
        ],
    },
    "Caustic Soda": {
        "anchor": "#CausticSoda",
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

        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(8000)

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


def open_anchor(page, anchor):
    target_url = BASE_URL + anchor
    print(f"Opening anchor: {target_url}")

    page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(7000)

    # Scroll a little to force lazy/virtual table rendering
    for _ in range(3):
        page.mouse.wheel(0, 700)
        page.wait_for_timeout(800)

    try:
        page.wait_for_selector("div[role='row'], .ant-table-row, table tbody tr", timeout=15000)
    except Exception:
        pass

    page.wait_for_timeout(2500)


def extract_item_from_visible_text(page, item_name):
    """
    Fallback for hero / non-table values.
    Example:
    Aluminum Ingot / SMM A00 Aluminum Ingot
    3,207.28
    USD/tonne
    """
    text = page.locator("body").inner_text(timeout=30000)
    lines = [x.strip() for x in text.splitlines() if x.strip()]

    for i, line in enumerate(lines):
        if item_name.lower() in line.lower():
            for j in range(i + 1, min(i + 10, len(lines))):
                val = to_float(lines[j])
                if val is not None and abs(val) > 50:
                    return val

    return None


def extract_item_from_table(page, item_name):
    """
    Reads React / virtual-grid rows.

    Expected visual columns:
    Name | Unit | High | Low | Average/Index/Latest | Change | Date

    Captures:
    - Average = 3rd numeric value in row
    - Index/Latest = 1st numeric value when row has index/latest format
    """
    row_selectors = [
        "div[role='row']",
        ".ant-table-row",
        "table tbody tr",
        "[class*='table'] [class*='row']",
    ]

    for row_selector in row_selectors:
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

                cell_texts = []

                role_cells = row.locator("div[role='cell']")
                td_cells = row.locator("td")

                if role_cells.count() > 0:
                    for c in range(role_cells.count()):
                        cell_texts.append(role_cells.nth(c).inner_text(timeout=1000).strip())

                elif td_cells.count() > 0:
                    for c in range(td_cells.count()):
                        cell_texts.append(td_cells.nth(c).inner_text(timeout=1000).strip())

                else:
                    cell_texts = [x.strip() for x in row_text.splitlines() if x.strip()]

                numeric_values = []

                for txt in cell_texts:
                    val = to_float(txt)
                    if val is not None:
                        numeric_values.append(val)

                # Normal table: High, Low, Average, Change
                if len(numeric_values) >= 3:
                    avg = numeric_values[2]
                    if abs(avg) > 50:
                        return avg

                # Index / LME style: Index or Latest, Change
                if len(numeric_values) >= 1:
                    first = numeric_values[0]
                    if abs(first) > 50:
                        return first

            except Exception:
                continue

    return None


def capture_single(page, anchor, item):
    open_anchor(page, anchor)

    value = extract_item_from_table(page, item)

    if value is None:
        value = extract_item_from_visible_text(page, item)

    return value


def capture_group(page, group_name, anchor, items):
    open_anchor(page, anchor)

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
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            ),
        )

        login_if_possible(page)

        for col, cfg in SINGLE_ITEMS.items():
            dashboard_row[col] = capture_single(page, cfg["anchor"], cfg["item"])

        for group_name, cfg in GROUPS.items():
            avg, rows = capture_group(page, group_name, cfg["anchor"], cfg["items"])
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
                        "Source": BASE_URL + cfg["anchor"],
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
