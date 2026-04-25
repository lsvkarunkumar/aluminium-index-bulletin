import pandas as pd
from datetime import datetime


# 🔴 TEMP MASTER INDEX LIST (we will refine later from site)
MASTER_COLUMNS = [
    "Date",
    "A00 Aluminium (USD/t)",
    "A00 Premium (USD/t)",
    "Alumina Shanxi (USD/t)",
    "Alumina Henan (USD/t)",
    "Alumina Shandong (USD/t)",
    "Bauxite Index (USD/t)",
    "CPC (USD/t)",
    "Prebaked Anode (USD/t)",
    "Pitch (USD/t)",
    "Scrap ADC12 (USD/t)",
    "Import Arbitrage (USD/t)",
]


def fetch_metal_prices():
    today = datetime.today().strftime("%Y-%m-%d")

    row = {col: None for col in MASTER_COLUMNS}
    row["Date"] = today

    return pd.DataFrame([row], columns=MASTER_COLUMNS)
