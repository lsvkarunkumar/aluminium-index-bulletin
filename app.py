import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


APP_TITLE = "Aluminium Market Index Bulletin – Daily Pink Sheet"

DATA_DIR = Path("data")
PINK_SHEET_FILE = DATA_DIR / "pink_sheet.csv"
EXCEL_FILE = DATA_DIR / "pink_sheet.xlsx"

FIXED_INDICES = [
    "SMM Aluminum Index (USD/t)",
    "Petroleum Coke Index (USD/t)",
    "Prebaked Anode (USD/t)",
    "Coal Tar Pitch (USD/t)",
]


st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
)


def load_data():
    if not PINK_SHEET_FILE.exists():
        return pd.DataFrame()

    df = pd.read_csv(PINK_SHEET_FILE)

    if "Date" not in df.columns:
        return pd.DataFrame()

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    df = df.sort_values("Date", ascending=False)

    return df


def to_numeric_series(df, col):
    return pd.to_numeric(df[col], errors="coerce")


def make_chart(df, col, title):
    chart_df = df[["Date", col]].copy()
    chart_df[col] = pd.to_numeric(chart_df[col], errors="coerce")
    chart_df = chart_df.dropna(subset=[col]).sort_values("Date")

    if chart_df.empty:
        return None

    fig = px.line(
        chart_df,
        x="Date",
        y=col,
        markers=True,
        title=title,
    )
    fig.update_layout(height=330, margin=dict(l=20, r=20, t=50, b=20))
    return fig


def excel_download_bytes():
    if EXCEL_FILE.exists():
        return EXCEL_FILE.read_bytes()

    output = io.BytesIO()
    df = load_data()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Pink Sheet")
    output.seek(0)
    return output.read()


df = load_data()

st.title(APP_TITLE)
st.caption("Phase 2: Dashboard Analytics | Fixed graphs + dropdown analytics")

if df.empty:
    st.warning("No Pink Sheet data found yet.")
    st.stop()

latest = df.iloc[0]

st.divider()

st.subheader("Fixed Benchmark Panel")

cols = st.columns(4)

for i, index_name in enumerate(FIXED_INDICES):
    with cols[i]:
        if index_name in df.columns:
            value = pd.to_numeric(latest[index_name], errors="coerce")
            st.metric(index_name.replace(" (USD/t)", ""), "-" if pd.isna(value) else f"{value:,.2f}")
        else:
            st.metric(index_name.replace(" (USD/t)", ""), "Not found")

st.divider()

st.subheader("Fixed Graphs")

graph_cols_1 = st.columns(2)

for i, index_name in enumerate(FIXED_INDICES[:2]):
    with graph_cols_1[i]:
        if index_name in df.columns:
            fig = make_chart(df, index_name, index_name)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"No numeric data available for {index_name}")
        else:
            st.warning(f"Missing column: {index_name}")

graph_cols_2 = st.columns(2)

for i, index_name in enumerate(FIXED_INDICES[2:]):
    with graph_cols_2[i]:
        if index_name in df.columns:
            fig = make_chart(df, index_name, index_name)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"No numeric data available for {index_name}")
        else:
            st.warning(f"Missing column: {index_name}")

st.divider()

st.subheader("Last 15 Days Pink Sheet")
st.dataframe(
    df.head(15),
    use_container_width=True,
    hide_index=True,
    height=420,
)

st.divider()

st.subheader("Dropdown Analytics")

available_indices = [c for c in df.columns if c != "Date"]

selected_index = st.selectbox(
    "Single Index Trend",
    available_indices,
)

fig = make_chart(df, selected_index, f"Trend: {selected_index}")
if fig:
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No numeric data available for selected index.")

comparison_indices = st.multiselect(
    "Multi-Index Comparison",
    available_indices,
    default=[x for x in FIXED_INDICES if x in available_indices][:2],
    max_selections=5,
)

if comparison_indices:
    comp_df = df[["Date"] + comparison_indices].copy()
    for col in comparison_indices:
        comp_df[col] = pd.to_numeric(comp_df[col], errors="coerce")

    comp_df = comp_df.sort_values("Date")
    long_df = comp_df.melt(id_vars="Date", var_name="Index", value_name="Value").dropna()

    if not long_df.empty:
        fig = px.line(
            long_df,
            x="Date",
            y="Value",
            color="Index",
            markers=True,
            title="Multi-Index Comparison",
        )
        fig.update_layout(height=420, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No numeric data available for selected comparison indices.")

st.divider()

st.subheader("Download")

st.download_button(
    label="Download Formatted Excel Pink Sheet",
    data=excel_download_bytes(),
    file_name="Aluminium_Market_Index_Bulletin.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

st.download_button(
    label="Download Raw CSV",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="pink_sheet.csv",
    mime="text/csv",
)
