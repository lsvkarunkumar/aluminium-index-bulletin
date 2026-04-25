from pathlib import Path

import pandas as pd

from collector import fetch_metal_prices, PINK_SHEET_COLUMNS


DATA_DIR = Path("data")
PINK_SHEET_FILE = DATA_DIR / "pink_sheet.csv"


def ensure_data_file():
    DATA_DIR.mkdir(exist_ok=True)

    if not PINK_SHEET_FILE.exists():
        df = pd.DataFrame(columns=PINK_SHEET_COLUMNS)
        df.to_csv(PINK_SHEET_FILE, index=False)


def load_existing_data():
    ensure_data_file()
    return pd.read_csv(PINK_SHEET_FILE)


def save_data(df):
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.sort_values("Date", ascending=False)
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    df.to_csv(PINK_SHEET_FILE, index=False)


def main():
    existing_df = load_existing_data()
    new_df = fetch_metal_prices()

    for _, row in new_df.iterrows():
        capture_date = row["Date"]

        existing_df = existing_df[existing_df["Date"] != capture_date]
        existing_df = pd.concat(
            [pd.DataFrame([row]), existing_df],
            ignore_index=True,
        )

    save_data(existing_df)
    print("Daily capture completed successfully.")


if __name__ == "__main__":
    main()
