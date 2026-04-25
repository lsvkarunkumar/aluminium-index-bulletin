from datetime import datetime
import pandas as pd


PINK_SHEET_COLUMNS = [
    "Date",
    "A00 Aluminium (USD/t)",
    "CPC (USD/t)",
    "Prebaked Anode (USD/t)",
    "Pitch (USD/t)",
]


def fetch_metal_prices():
    """
    Phase 1 collector.

    Current status:
    - System-ready structure
    - Placeholder values until real Metal.com extraction is added
    - Keeps columns stable for Pink Sheet

    Next step:
    - Replace None values with parsed values from Metal.com / authorized source.
    """

    today = datetime.today().strftime("%Y-%m-%d")

    row = {
        "Date": today,
        "A00 Aluminium (USD/t)": None,
        "CPC (USD/t)": None,
        "Prebaked Anode (USD/t)": None,
        "Pitch (USD/t)": None,
    }

    return pd.DataFrame([row], columns=PINK_SHEET_COLUMNS)
