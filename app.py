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


# -----------------------------
# GLOBAL STYLE
# -----------------------------
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 1rem;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
        max-width: 100%;
    }

    html, body, [class*="css"] {
        font-family: "Arial Narrow", Arial, sans-serif;
    }

    h1 {
        font-size: 30px !important;
        font-weight: 500 !important;
        margin-bottom: 0.2rem !important;
    }

    h2, h3 {
        font-weight: 500 !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.4rem !important;
    }

    .section-title {
        font-size: 18px;
        font-weight: 500;
        margin-top: 16px;
        margin-bottom: 8px;
        border-bottom: 1px solid #d9d9d9;
        padding-bottom: 4px;
    }

    .top-caption {
        font-size: 12px;
        color: #666;
        margin-bottom: 12px;
    }

    .metric-card {
        border: 1px solid #d9d9d9;
        background: #fff7fb;
        padding: 10px 12px;
        height: 92px;
        border-radius: 4px;
    }

    .metric-title {
        font-size: 12px;
        color: #444;
        line-height: 1.1;
        height: 30px;
        overflow: hidden;
    }

    .metric-value {
        font-size: 22px;
        color: #111;
        margin-top: 6px;
        line-height: 1.1;
    }

    .metric-delta {
        font-size: 11px;
        color: #666;
        margin-top: 4px;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #d9d9d9;
    }

    .download-box {
        border: 1px solid #d9d9d9;
        background: #fafafa;
        padding: 12px;
        border-radius: 4px;
    }

    .stAlert {
        padding: 0.35rem 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# DATA FUNCTIONS
# -----------------------------
def format_date_for_display(series):
    return pd.to_datetime(series, errors="coerce").dt.strftime("%d/%b/%Y")


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


def clean_display_df(df):
    out = df.copy()
    out["Date"] = format_date_for_display(out["Date"])

    for col in out.columns:
        if col != "Date":
            out[col] = out[col].replace({None: "", "None": "", "nan": ""})
            out[col] = out[col].fillna("")

    return out


def numeric_col(df, col):
    if col not in df.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(df[col], errors="coerce")


def latest_value_and_delta(df, col):
    if col not in df.columns:
        return "-", "-"

    temp = df[["Date", col]].copy()
    temp[col] = pd.to_numeric(temp[col], errors="coerce")
    temp = temp.dropna(subset=[col]).sort_values("Date", ascending=False)

    if temp.empty:
        return "-", "No value"

    latest = temp.iloc[0][col]

    if len(temp) >= 2:
        previous = temp.iloc[1][col]
        change = latest - previous
        pct = (change / previous * 100) if previous != 0 else None

        sign = "+" if change > 0 else ""
        if pct is None:
            delta = f"{sign}{change:,.2f}"
        else:
            delta = f"{sign}{change:,.2f} ({sign}{pct:,.2f}%)"
    else:
        delta = "First value"

    return f"{latest:,.2f}", delta


def make_chart(df, col, title):
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
        title=title.replace(" (USD/t)", ""),
    )

    fig.update_layout(
        height=260,
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


def excel_download_bytes():
    if EXCEL_FILE.exists():
        return EXCEL_FILE.read_bytes()

    df = load_data()
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        clean_display_df(df).to_excel(writer, index=False, sheet_name="Pink Sheet")
    output.seek(0)
    return output.read()


# -----------------------------
# LOAD
# -----------------------------
df = load_data()

st.markdown(f"<h1>{APP_TITLE}</h1>", unsafe_allow_html=True)
st.markdown(
    '<div class="top-caption">Phase 2 Dashboard | Fixed benchmark panel | Last 15 days Pink Sheet | Dropdown analytics</div>',
    unsafe_allow_html=True,
)

if df.empty:
    st.warning("No Pink Sheet data found yet.")
    st.stop()

display_df = clean_display_df(df)

latest_date = display_df["Date"].iloc[0] if not display_df.empty else "-"

# -----------------------------
# STATUS STRIP
# -----------------------------
st.markdown('<div class="section-title">Daily Bulletin Status</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1])

with c1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Latest Date</div>
            <div class="metric-value">{latest_date}</div>
            <div class="metric-delta">Date format: dd/mmm/yyyy</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Captured Days</div>
            <div class="metric-value">{len(df)}</div>
            <div class="metric-delta">Latest row on top</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Total Indices</div>
            <div class="metric-value">{len(df.columns) - 1}</div>
            <div class="metric-delta">Master-driven columns</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c4:
    missing_values_today = display_df.iloc[0].replace("", pd.NA).isna().sum() - 0
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Missing Values Latest Row</div>
            <div class="metric-value">{missing_values_today}</div>
            <div class="metric-delta">Blank values retained</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------
# FIXED BENCHMARK PANEL
# -----------------------------
st.markdown('<div class="section-title">Fixed Benchmark Panel</div>', unsafe_allow_html=True)

fixed_cols = st.columns(4)

for i, index_name in enumerate(FIXED_INDICES):
    value, delta = latest_value_and_delta(df, index_name)

    with fixed_cols[i]:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">{index_name.replace(" (USD/t)", "")}</div>
                <div class="metric-value">{value}</div>
                <div class="metric-delta">{delta}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# -----------------------------
# FIXED GRAPHS
# -----------------------------
st.markdown('<div class="section-title">Fixed Graphs</div>', unsafe_allow_html=True)

g1, g2 = st.columns(2)

with g1:
    fig = make_chart(df, FIXED_INDICES[0], FIXED_INDICES[0])
    st.plotly_chart(fig, use_container_width=True) if fig else st.info(f"No numeric data available for {FIXED_INDICES[0]}")

with g2:
    fig = make_chart(df, FIXED_INDICES[1], FIXED_INDICES[1])
    st.plotly_chart(fig, use_container_width=True) if fig else st.info(f"No numeric data available for {FIXED_INDICES[1]}")

g3, g4 = st.columns(2)

with g3:
    fig = make_chart(df, FIXED_INDICES[2], FIXED_INDICES[2])
    st.plotly_chart(fig, use_container_width=True) if fig else st.info(f"No numeric data available for {FIXED_INDICES[2]}")

with g4:
    fig = make_chart(df, FIXED_INDICES[3], FIXED_INDICES[3])
    st.plotly_chart(fig, use_container_width=True) if fig else st.info(f"No numeric data available for {FIXED_INDICES[3]}")


# -----------------------------
# LAST 15 DAYS TABLE
# -----------------------------
st.markdown('<div class="section-title">Last 15 Days Pink Sheet</div>', unsafe_allow_html=True)

st.dataframe(
    display_df.head(15),
    use_container_width=True,
    hide_index=True,
    height=360,
)


# -----------------------------
# DROPDOWN ANALYTICS
# -----------------------------
st.markdown('<div class="section-title">Dropdown Analytics</div>', unsafe_allow_html=True)

available_indices = [c for c in df.columns if c != "Date"]

left, right = st.columns([1, 1])

with left:
    selected_index = st.selectbox(
        "Single Index Trend",
        available_indices,
        index=available_indices.index(FIXED_INDICES[0]) if FIXED_INDICES[0] in available_indices else 0,
    )

    fig = make_chart(df, selected_index, selected_index)

    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No numeric data available for selected index.")

with right:
    default_comp = [x for x in FIXED_INDICES if x in available_indices][:2]

    comparison_indices = st.multiselect(
        "Multi-Index Comparison",
        available_indices,
        default=default_comp,
        max_selections=5,
    )

    if comparison_indices:
        comp_df = df[["Date"] + comparison_indices].copy()

        for col in comparison_indices:
            comp_df[col] = pd.to_numeric(comp_df[col], errors="coerce")

        comp_df = comp_df.sort_values("Date")
        long_df = comp_df.melt(
            id_vars="Date",
            var_name="Index",
            value_name="Value",
        ).dropna()

        if not long_df.empty:
            fig = px.line(
                long_df,
                x="Date",
                y="Value",
                color="Index",
                markers=True,
                title="Multi-Index Comparison",
            )
            fig.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=35, b=10),
                font=dict(family="Arial Narrow", size=11),
                title=dict(font=dict(size=14)),
                xaxis_title="",
                yaxis_title="USD/t",
                plot_bgcolor="white",
                paper_bgcolor="white",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No numeric data available for selected comparison indices.")


# -----------------------------
# DOWNLOAD
# -----------------------------
st.markdown('<div class="section-title">Download</div>', unsafe_allow_html=True)

d1, d2 = st.columns([1, 1])

with d1:
    st.download_button(
        label="Download Formatted Excel Pink Sheet",
        data=excel_download_bytes(),
        file_name="Aluminium_Market_Index_Bulletin.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

with d2:
    st.download_button(
        label="Download Raw CSV",
        data=display_df.to_csv(index=False).encode("utf-8"),
        file_name="pink_sheet.csv",
        mime="text/csv",
    )
