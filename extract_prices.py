import os
import re
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import pandas as pd
from bs4 import BeautifulSoup


OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

URLS = {
    "Aluminum Ingot": "https://www.metal.com/Aluminum?currency_type=2#AluminumIngot",
    "Bauxite": "https://www.metal.com/Aluminum?currency_type=2#Bauxite",
    "Alumina": "https://www.metal.com/Aluminum?currency_type=2#Alumina",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_html(url: str) -> str:
    base_url = url.split("#")[0]
    response = requests.get(base_url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text


def extract_price_near_keyword(text: str, keyword: str):
    idx = text.lower().find(keyword.lower())
    if idx == -1:
        return None

    window = text[max(0, idx - 500): idx + 1500]

    patterns = [
        r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?)\s*-\s*(\d{1,3}(?:,\d{3})+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)",
        r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, window)
        if match:
            nums = [x.replace(",", "") for x in match.groups()]
            nums = [float(x) for x in nums if x]

            if len(nums) == 2:
                low, high = nums
                return {
                    "price_low": low,
                    "price_high": high,
                    "price_mid": round((low + high) / 2, 2),
                    "raw_match": match.group(0),
                }

            if len(nums) == 1:
                return {
                    "price_low": nums[0],
                    "price_high": nums[0],
                    "price_mid": nums[0],
                    "raw_match": match.group(0),
                }

    return None


def scrape():
    run_time = datetime.now(timezone.utc).isoformat()
    rows = []
    status = {
        "run_time_utc": run_time,
        "success": True,
        "items_found": 0,
        "errors": [],
    }

    for product, url in URLS.items():
        try:
            html = fetch_html(url)
            text = clean_text(html)

            result = extract_price_near_keyword(text, product)

            if result is None:
                rows.append({
                    "run_time_utc": run_time,
                    "product": product,
                    "url": url,
                    "price_low": None,
                    "price_high": None,
                    "price_mid": None,
                    "raw_match": None,
                    "status": "NOT_FOUND",
                })
                status["errors"].append(f"{product}: price not found")
                continue

            rows.append({
                "run_time_utc": run_time,
                "product": product,
                "url": url,
                "price_low": result["price_low"],
                "price_high": result["price_high"],
                "price_mid": result["price_mid"],
                "raw_match": result["raw_match"],
                "status": "OK",
            })

            status["items_found"] += 1
            time.sleep(2)

        except Exception as e:
            rows.append({
                "run_time_utc": run_time,
                "product": product,
                "url": url,
                "price_low": None,
                "price_high": None,
                "price_mid": None,
                "raw_match": None,
                "status": "ERROR",
            })
            status["errors"].append(f"{product}: {str(e)}")

    if status["items_found"] == 0:
        status["success"] = False

    df = pd.DataFrame(rows)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily_file = OUTPUT_DIR / f"smm_prices_{today}.csv"
    master_file = OUTPUT_DIR / "smm_prices_master.csv"
    status_file = OUTPUT_DIR / "status.json"

    df.to_csv(daily_file, index=False)

    if master_file.exists():
        old = pd.read_csv(master_file)
        combined = pd.concat([old, df], ignore_index=True)
        combined.drop_duplicates(
            subset=["run_time_utc", "product"],
            keep="last",
            inplace=True,
        )
    else:
        combined = df

    combined.to_csv(master_file, index=False)

    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)

    print(df)
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    scrape()
