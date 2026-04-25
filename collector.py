import pandas as pd
from datetime import datetime


def fetch_metal_prices():
    """
    Phase 1: Placeholder collector

    Replace this later with:
    - requests + BeautifulSoup OR
    - API (if subscription available)
    """

    today = datetime.today().strftime("%Y-%m-%d")

    # TEMP SAMPLE VALUES (replace later)
    data = {
        "Date": today,
        "A00 Aluminium (USD/t)": None,
        "CPC (USD/t)": None,
        "Prebaked Anode (USD/t)": None,
        "Pitch (USD/t)": None,
    }

    return pd.DataFrame([data])
