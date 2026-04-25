import io
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


APP_TITLE = "Aluminium Market Index Bulletin – Daily Pink Sheet"
DATA_DIR = Path("data")
PINK_SHEET_FILE = DATA_DIR / "pink_sheet.csv"


st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
)


def ensure_files():
    DATA_DIR.mkdir(exist_ok=True)

    if not PINK_SHEET_FILE.exists():
        df = pd.DataFrame(
            columns=[
                "Date",
                "A00 Aluminium (USD/t)",
                "CPC (USD/t)",
                "Prebaked Anode (USD/t)",
                "Pitch (USD/t)",
            ]
        )
        df.to_csv(PINK_SHEET_FILE, index=False)


def load_pink_sheet():
    ensure_files()
    df = pd.read_csv(PINK_SHEET_FILE)

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values("Date", ascending=False)
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")

    return df


def make_excel_download(df):
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="01_Pink_Sheet")

        last_15 = df.head(15)
        last_15.to_excel(writer, index=False, sheet_name="02_Last_15_Days")

        workbook = writer.book

        for sheet_name in workbook.sheetnames:
            ws = workbook[sheet_name]

            ws.insert_rows(1, 5)

            max_col = ws.max_column

            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_col)
            ws.cell(row=1, column=1).value = APP_TITLE

            ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max_col)
            ws.cell(row=2, column=1).value = "Official Daily Price Sheet – Aluminium Value Chain"

            ws.cell(row=3, column=1).value = "Last Updated:"
            ws.cell(row=3, column=2).value = datetime.now().strftime("%Y-%m-%d %H:%M")

            ws.cell(row=4, column=1).value = "Data Mode:"
            ws.cell(row=4, column=2).value = "Phase 1 – Data Collection Only"

            ws.cell(row=5, column=1).value = "Source:"
            ws.cell(row=5, column=2).value = "Metal.com / SMM"

            ws.freeze_panes = "A7"

            for col in ws.columns:
                max_length = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                ws.column_dimensions[col_letter].width = min(max_length + 3, 35)

    output.seek(0)
    return output


ensure_files()
df = load_pink_sheet()

st.title(APP_TITLE)
st.caption("Phase 1: Data Collection Only | One row per day | Latest date on top")

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Captured Days", len(df))

with col2:
    latest_date = df["Date"].iloc[0] if not df.empty else "-"
    st.metric("Latest Date", latest_date)

with col3:
    st.metric("Fixed Benchmark Columns", 4)

st.subheader("Latest Pink Sheet Row")

if not df.empty:
    st.dataframe(df.head(1), use_container_width=True, hide_index=True)
else:
    st.warning("No data available yet.")

st.subheader("Last 15 Days – Scrollable Pink Sheet")
st.dataframe(df.head(15), use_container_width=True, hide_index=True, height=420)

st.subheader("Download Data")

excel_file = make_excel_download(df)

st.download_button(
    label="Download Excel Bulletin",
    data=excel_file,
    file_name="Aluminium_Market_Index_Bulletin.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

csv_file = df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download Pink Sheet CSV",
    data=csv_file,
    file_name="pink_sheet.csv",
    mime="text/csv",
)
