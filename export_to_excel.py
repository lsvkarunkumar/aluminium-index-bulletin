from pathlib import Path
import pandas as pd
from openpyxl.styles import Font, Alignment, PatternFill


DATA_DIR = Path("data")
CSV_FILE = DATA_DIR / "pink_sheet.csv"
EXCEL_FILE = DATA_DIR / "pink_sheet.xlsx"


def main():
    df = pd.read_csv(CSV_FILE)

    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Pink Sheet")

        ws = writer.sheets["Pink Sheet"]

        fill_even = PatternFill("solid", fgColor="FCE4EC")  # light pink
        fill_odd = PatternFill("solid", fgColor="FFFFFF")   # white

        for col_idx, col in enumerate(ws.columns, start=1):
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = 10

            fill = fill_even if col_idx % 2 == 0 else fill_odd

            for cell in col:
                cell.font = Font(name="Arial Narrow", size=10, bold=False)
                cell.alignment = Alignment(
                    wrap_text=True,
                    vertical="center",
                    horizontal="center"
                )
                cell.fill = fill

        ws.row_dimensions[1].height = 60

        for cell in ws[1]:
            cell.font = Font(name="Arial Narrow", size=10, bold=False)
            cell.alignment = Alignment(
                wrap_text=True,
                vertical="center",
                horizontal="center"
            )

        ws.freeze_panes = "A2"

    print("Excel formatted: Arial Narrow 10, no bold, wrapped header, alternate columns.")


if __name__ == "__main__":
    main()
