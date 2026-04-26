import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import pandas as pd


URL = "https://www.metal.com/Aluminum?currency_type=2"

TARGETS = {
    "SMM Aluminum Index (USD/t)": "SMM Aluminum Index",
    "Petroleum Coke Index (USD/t)": "Petroleum Coke Index",
    "Prebaked Anode (USD/t)": "Prebaked Anode",
    "Coal Tar Pitch (USD/t)": "Coal Tar Pitch",
}


def fetch_page():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    r = requests.get(URL, headers=headers, timeout=30)
    return r.text


def extract_value(text_block):
    match = re.search(r"\d{2,5}\.\d+|\d{2,5}", text_block)
    if match:
        try:
            return float(match.group())
        except:
            return None
    return None


def extract_prices(html):
    soup = BeautifulSoup(html, "html.parser")
    full_text = soup.get_text(" ", strip=True)

    data = {}

    for col_name, keyword in TARGETS.items():
        value = None

        try:
            idx = full_text.lower().find(keyword.lower())

            if idx != -1:
                snippet = full_text[idx: idx + 120]
                value = extract_value(snippet)

        except:
            pass

        data[col_name] = value

    return data


def main():
    html = fetch_page()
    prices = extract_prices(html)

    today = datetime.today().strftime("%Y-%m-%d")

    row = {"Date": today}
    row.update(prices)

    df = pd.DataFrame([row])

    print("\nCaptured Data:")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
