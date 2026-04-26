from pathlib import Path
import pandas as pd
from datetime import datetime


DATA_DIR = Path("data")
MASTER_FILE = DATA_DIR / "master_index_list.csv"


def load_master_columns():
    master = pd.read_csv(MASTER_FILE)

    master = master[master["Active"] == True]

    columns = ["Date"] + master["Column Name"].tolist()

    return columns


def fetch_metal_prices():
    today = datetime.today().strftime("%Y-%m-%d")

    columns = load_master_columns()

    row = {col: None for col in columns}
    row["Date"] = today

    return pd.DataFrame([row], columns=columns)
