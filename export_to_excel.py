from pathlib import Path
import pandas as pd
from openpyxl.styles import Font, Alignment


DATA_DIR = Path("data")
CSV_FILE = DATA_DIR / "pink_sheet.csv"
EXCEL_FILE = DATA_DIR / "pink_sheet.xlsx"


def main():
    df = pd.read_csv(CSV_FILE)

    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Pink Sheet")

        ws = writer.sheets["Pink Sheet"]

        # -----------------------------
        # 1. FIXED COLUMN WIDTH
        # -----------------------------
        for col in ws.columns:
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = 10

        # -----------------------------
        # 2. APPLY FONT + WRAP TO ALL
        # -----------------------------
        for row in ws.iter_rows():
            for cell in row:
                cell.font = Font(name="Arial", size=10)
                cell.alignment = Alignment(
                    wrap_text=True,
                    vertical="center",
                    horizontal="center"
                )

        # -----------------------------
        # 3. HEADER ROW FORMAT ONLY
        # -----------------------------
        ws.row_dimensions[1].height = 60  # only header row

        for cell in ws[1]:
            cell.font = Font(name="Arial", size=10, bold=True)
            cell.alignment = Alignment(
                wrap_text=True,
                vertical="center",
                horizontal="center"
            )

        # -----------------------------
        # 4. FREEZE HEADER
        # -----------------------------
        ws.freeze_panes = "A2"

    print("✅ Excel formatted perfectly (Pink Sheet style)")


if __name__ == "__main__":
    main()
