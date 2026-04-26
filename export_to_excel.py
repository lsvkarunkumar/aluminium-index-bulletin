from pathlib import Path
import pandas as pd


DATA_DIR = Path("data")
CSV_FILE = DATA_DIR / "pink_sheet.csv"
EXCEL_FILE = DATA_DIR / "pink_sheet.xlsx"


def main():
    df = pd.read_csv(CSV_FILE)

    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Pink Sheet")

        ws = writer.sheets["Pink Sheet"]

        # Auto column width (compact)
        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter

            for cell in col:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass

            # Set tight width (controlled)
            ws.column_dimensions[col_letter].width = min(max_length + 2, 25)

        # Freeze header
        ws.freeze_panes = "A2"

    print("Excel formatted file created.")


if __name__ == "__main__":
    main()
