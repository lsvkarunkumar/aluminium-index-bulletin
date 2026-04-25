from pathlib import Path
import pandas as pd
from collector import fetch_metal_prices, MASTER_COLUMNS


DATA_DIR = Path("data")
PINK_SHEET_FILE = DATA_DIR / "pink_sheet.csv"


def ensure_data_file():
    DATA_DIR.mkdir(exist_ok=True)

    if not PINK_SHEET_FILE.exists():
        df = pd.DataFrame(columns=MASTER_COLUMNS)
        df.to_csv(PINK_SHEET_FILE, index=False)


def load_existing_data():
    ensure_data_file()
    df = pd.read_csv(PINK_SHEET_FILE)

    # 🔴 If old structure exists, upgrade it
    for col in MASTER_COLUMNS:
        if col not in df.columns:
            df[col] = None

    return df[MASTER_COLUMNS]


def save_data(df):
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.sort_values("Date", ascending=False)
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    df.to_csv(PINK_SHEET_FILE, index=False)


def main():
    existing_df = load_existing_data()
    new_df = fetch_metal_prices()

    for _, row in new_df.iterrows():
        existing_df = existing_df[existing_df["Date"] != row["Date"]]
        existing_df = pd.concat([pd.DataFrame([row]), existing_df], ignore_index=True)

    save_data(existing_df)
    print("Updated with full index structure.")


if __name__ == "__main__":
    main()
