import io
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from collector import fetch_metal_prices


APP_TITLE = "Aluminium Market Index Bulletin – Daily Pink Sheet"
DATA_DIR = Path("data")
PINK_SHEET_FILE = DATA_DIR / "pink_sheet.csv"


st.set_page_config(page_title=APP_TITLE, layout="wide")


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


def load_data():
    ensure_files()
    df = pd.read_csv(PINK_SHEET_FILE)

    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values("Date", ascending=False)
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")

    return df


def save_data(df):
    df_copy = df.copy()
    df_copy["Date"] = pd.to_datetime(df_copy["Date"], errors="coerce")
    df_copy = df_copy.sort_values("Date", ascending=False)
    df_copy.to_csv(PINK_SHEET_FILE, index=False)


def make_excel(df):
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="01_Pink_Sheet")
        df.head(15).to_excel(writer, index=False, sheet_name="02_Last_15_Days")

    output.seek(0)
    return output


df = load_data()

st.title(APP_TITLE)
st.caption("Phase 1: Data Collection Only")

st.divider()


# --------------------------
# AUTOMATION BUTTON
# --------------------------
st.subheader("Automated Capture")

if st.button("Run Daily Capture (Manual Trigger)"):
    new_df = fetch_metal_prices()

    for _, new_row in new_df.iterrows():
        df = df[df["Date"] != new_row["Date"]]
        df = pd.concat([pd.DataFrame([new_row]), df], ignore_index=True)

    save_data(df)

    st.success("Automated capture completed.")
    st.rerun()


# --------------------------
# MANUAL ENTRY (KEEP)
# --------------------------
st.subheader("Enter Daily Prices")

with st.form("data_entry_form"):
    col1, col2, col3 = st.columns(3)

    with col1:
        date = st.date_input("Date", datetime.today())

    with col2:
        a00 = st.number_input("A00 Aluminium (USD/t)", value=0.0)

    with col3:
        cpc = st.number_input("CPC (USD/t)", value=0.0)

    col4, col5 = st.columns(2)

    with col4:
        anode = st.number_input("Prebaked Anode (USD/t)", value=0.0)

    with col5:
        pitch = st.number_input("Pitch (USD/t)", value=0.0)

    submit = st.form_submit_button("Add / Update Entry")

    if submit:
        new_row = {
            "Date": date.strftime("%Y-%m-%d"),
            "A00 Aluminium (USD/t)": a00,
            "CPC (USD/t)": cpc,
            "Prebaked Anode (USD/t)": anode,
            "Pitch (USD/t)": pitch,
        }

        df = df[df["Date"] != new_row["Date"]]
        df = pd.concat([pd.DataFrame([new_row]), df], ignore_index=True)

        save_data(df)

        st.success("Data saved successfully.")
        st.rerun()


# --------------------------
# DISPLAY
# --------------------------
st.divider()

st.subheader("Latest Entry")
if not df.empty:
    st.dataframe(df.head(1), use_container_width=True, hide_index=True)

st.subheader("Last 15 Days")
st.dataframe(df.head(15), use_container_width=True, hide_index=True, height=400)


# --------------------------
# DOWNLOAD
# --------------------------
st.divider()

st.subheader("Download")

excel = make_excel(df)

st.download_button(
    "Download Excel",
    data=excel,
    file_name="Aluminium_Market_Index_Bulletin.xlsx",
)

st.download_button(
    "Download CSV",
    data=df.to_csv(index=False),
    file_name="pink_sheet.csv",
)
