import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


APP_TITLE = "Aluminium Index Bulletin"

DATA_DIR = Path("data")
PINK_SHEET_FILE = DATA_DIR / "pink_sheet.csv"
EXCEL_FILE = DATA_DIR / "pink_sheet.xlsx"

FIXED_INDICES = [
    "SMM Aluminum Index (USD/t)",
    "Petroleum Coke Index (USD/t)",
    "Prebaked Anode (USD/t)",
    "Coal Tar Pitch (USD/t)",
]


st.set_page_config(page_title=APP_TITLE, layout="wide")


st.markdown(
    """
    <style>
    .block-container {
        padding: 1rem 1.4rem;
        max-width: 100%;
    }

    html, body, [class*="css"] {
        font-family: "Arial Narrow", Arial, sans-serif;
        font-size: 14px;
    }

    h1 {
        font-size: 28px !important;
        font-weight: 500 !important;
        margin-bottom: 0rem !important;
        line-height: 1.15 !important;
        white-space: normal !important;
    }

    .subtitle {
        color: #666;
        font-size: 14px;
        margin-bottom: 12px;
    }

    .section {
        font-size: 17px;
        font-weight: 500;
        margin-top: 14px;
        margin-bottom: 6px;
        padding-bottom: 4px;
        border-bottom: 1px solid #ddd;
    }

    .card {
        border: 1px solid #ddd;
        background: #fff7fb;
        border-radius: 5px;
        padding: 10px 12px;
        height: 82px;
    }

    .card-title {
        font-size: 12px;
        color: #444;
        height: 26px;
        line-height: 1.1;
        overflow: hidden;
    }

    .card-value {
        font-size: 22px;
        margin-top: 4px;
        color: #111;
        line-height: 1.1;
    }

    .card-sub {
        font-size: 11px;
        color: #666;
        margin-top: 3px;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #ddd;
    }

    .stDownloadButton button {
        border-radius: 4px;
        height: 38px;
        font-size: 14px;
    }
    </style>
    """,
    unsafe_allow_html=True,
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


def display_date(series):
    return pd.to_datetime(series, errors="coerce").dt.strftime("%d/%b/%Y")


def clean_for_display(df):
    out = df.copy()
    out["Date"] = display_date(out["Date"])

    for col in out.columns:
        if col != "Date":
            out[col] = out[col].fillna("").replace({"None": "", "nan": ""})

    return out


def get_value_delta(df, col):
    if col not in df.columns:
        return "-", ""

    tmp = df[["Date", col]].copy()
    tmp[col] = pd.to_numeric(tmp[col], errors="coerce")
    tmp = tmp.dropna(subset=[col]).sort_values("Date", ascending=False)

    if tmp.empty:
        return "-", ""

    latest = tmp.iloc[0][col]

    if len(tmp) < 2:
        return f"{latest:,.2f}", ""

    previous = tmp.iloc[1][col]
    change = latest - previous
    pct = (change / previous * 100) if previous else 0
    sign = "+" if change > 0 else ""

    return f"{latest:,.2f}", f"{sign}{change:,.2f} ({sign}{pct:,.2f}%)"


def make_chart(df, col):
    if col not in df.columns:
        return None

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
        title=col.replace(" (USD/t)", ""),
    )

    fig.update_layout(
        height=280,
        margin=dict(l=10, r=10, t=35, b=10),
        font=dict(family="Arial Narrow", size=11),
        title=dict(font=dict(size=14)),
        xaxis_title="",
        yaxis_title="USD/t",
        plot_bgcolor="white",
        paper_bgcolor="white",
    )

    fig.update_xaxes(showgrid=True, gridcolor="#eeeeee")
    fig.update_yaxes(showgrid=True, gridcolor="#eeeeee")

    return fig


def excel_bytes():
    if EXCEL_FILE.exists():
        return EXCEL_FILE.read_bytes()

    df = load_data()
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        clean_for_display(df).to_excel(writer, index=False, sheet_name="Pink Sheet")

    output.seek(0)
    return output.read()


df = load_data()

st.markdown("<h1>Aluminium Index Bulletin</h1>", unsafe_allow_html=True)
st.markdown('<div class="subtitle">Daily Pink Sheet</div>', unsafe_allow_html=True)

if df.empty:
    st.warning("No data file found.")
    st.stop()

display_df = clean_for_display(df)
latest_date = display_df["Date"].iloc[0]


# -----------------------------
# DOWNLOADS
# -----------------------------
d1, d2, d3 = st.columns([1, 1, 3])

with d1:
    st.download_button(
        "Download Excel",
        data=excel_bytes(),
        file_name="Aluminium_Index_Bulletin.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

with d2:
    st.download_button(
        "Download CSV",
        data=display_df.to_csv(index=False).encode("utf-8"),
        file_name="pink_sheet.csv",
        mime="text/csv",
        use_container_width=True,
    )


# -----------------------------
# OVERVIEW
# -----------------------------
st.markdown('<div class="section">Overview</div>', unsafe_allow_html=True)

o1, o2, o3, o4 = st.columns(4)

with o1:
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title">Latest Date</div>
            <div class="card-value">{latest_date}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with o2:
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title">Captured Days</div>
            <div class="card-value">{len(df)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with o3:
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title">Tracked Indices</div>
            <div class="card-value">{len(df.columns) - 1}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with o4:
    missing = display_df.iloc[0].drop(labels=["Date"], errors="ignore").replace("", pd.NA).isna().sum()
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title">Missing Values</div>
            <div class="card-value">{missing}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------
# KEY BENCHMARKS
# -----------------------------
st.markdown('<div class="section">Key Benchmarks</div>', unsafe_allow_html=True)

cards = st.columns(4)

for i, col in enumerate(FIXED_INDICES):
    value, delta = get_value_delta(df, col)

    with cards[i]:
        st.markdown(
            f"""
            <div class="card">
                <div class="card-title">{col.replace(" (USD/t)", "")}</div>
                <div class="card-value">{value}</div>
                <div class="card-sub">{delta}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# -----------------------------
# TREND VIEW
# -----------------------------
st.markdown('<div class="section">Trend View</div>', unsafe_allow_html=True)

available_indices = [c for c in df.columns if c != "Date"]

t1, t2 = st.columns(2)

with t1:
    selected_index = st.selectbox(
        "Select index",
        available_indices,
        index=available_indices.index(FIXED_INDICES[0]) if FIXED_INDICES[0] in available_indices else 0,
    )

with t2:
    compare_indices = st.multiselect(
        "Compare indices",
        available_indices,
        default=[c for c in FIXED_INDICES if c in df.columns][:2],
        max_selections=5,
    )

g1, g2 = st.columns(2)

with g1:
    fig = make_chart(df, selected_index)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No numeric data available.")

with g2:
    if compare_indices:
        comp = df[["Date"] + compare_indices].copy()

        for c in compare_indices:
            comp[c] = pd.to_numeric(comp[c], errors="coerce")

        comp = comp.sort_values("Date")
        long = comp.melt(id_vars="Date", var_name="Index", value_name="Value").dropna()

        if not long.empty:
            fig = px.line(
                long,
                x="Date",
                y="Value",
                color="Index",
                markers=True,
                title="Comparison",
            )
            fig.update_layout(
                height=280,
                margin=dict(l=10, r=10, t=35, b=10),
                font=dict(family="Arial Narrow", size=11),
                xaxis_title="",
                yaxis_title="USD/t",
                plot_bgcolor="white",
                paper_bgcolor="white",
            )
            fig.update_xaxes(showgrid=True, gridcolor="#eeeeee")
            fig.update_yaxes(showgrid=True, gridcolor="#eeeeee")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No numeric data available.")


# -----------------------------
# RECENT DATA
# -----------------------------
st.markdown('<div class="section">Recent Data</div>', unsafe_allow_html=True)

visible_cols = ["Date"] + [c for c in FIXED_INDICES if c in display_df.columns]
compact_df = display_df[visible_cols].head(15)

st.dataframe(
    compact_df,
    use_container_width=True,
    hide_index=True,
    height=300,
)

with st.expander("Full Pink Sheet"):
    st.dataframe(
        display_df.head(15),
        use_container_width=True,
        hide_index=True,
        height=420,
    )
