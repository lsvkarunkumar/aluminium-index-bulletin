import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

ITEMS = {
    "SMM A00 Aluminum Ingot": "https://www.metal.com/aluminum/201102250311",
    "SMM Tianjin A00 Aluminum Ingot": "https://www.metal.com/aluminum/201102250521",
}

HEADERS = {"User-Agent": "Mozilla/5.0"}


def scrape_page(name, url):
    html = requests.get(url, headers=HEADERS, timeout=30).text
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)

    return {
        "run_time_utc": datetime.now(timezone.utc).isoformat(),
        "product": name,
        "url": url,
        "unit": "USD/tonne" if "USD/tonne" in text else None,
        "price_status": "LOGIN_REQUIRED" if "Sign in to view" in text else "UNKNOWN",
        "page_date_found": "Apr 27, 2026" if "Apr 27, 2026" in text else None,
        "status": "OK",
    }


rows = []
errors = []

for name, url in ITEMS.items():
    try:
        rows.append(scrape_page(name, url))
    except Exception as e:
        errors.append(f"{name}: {e}")

df = pd.DataFrame(rows)

today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
df.to_csv(OUTPUT_DIR / f"smm_status_{today}.csv", index=False)
df.to_csv(OUTPUT_DIR / "smm_status_master.csv", index=False)

with open(OUTPUT_DIR / "status.json", "w", encoding="utf-8") as f:
    json.dump(
        {
            "success": len(rows) > 0,
            "items_found": len(rows),
            "errors": errors,
            "note": "SMM price values require login/subscription and are not visible in public HTML.",
        },
        f,
        indent=2,
    )

print(df)
