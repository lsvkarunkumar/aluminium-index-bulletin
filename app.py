import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


APP_TITLE = "Aluminium Index Bulletin"
APP_SUBTITLE = "Daily Pink Sheet"
DATA_DIR = Path("data")
PINK_SHEET_FILE = DATA_DIR / "pink_sheet.csv"
MASTER_FILE = DATA_DIR / "master_index_list.csv"
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
        padding-top: 0.8rem;
        padding-left: 1.2rem;
        padding-right: 1.2rem;
        max-width: 100%;
    }

    html, body, [class*="css"] {
        font-family: "Arial Narrow", Arial, sans-serif;
    }

    .app-header {
        border: 1px solid #d9d9d9;
        background: linear-gradient(90deg, #fff2f7, #ffffff);
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
    }

    .app-title {
        font-size: 28px;
        font-weight: 500;
        color: #111;
        line-height: 1.1;
    }

    .app-subtitle {
        font-size: 13px;
        color: #555;
        margin-top: 4px;
    }

    .section-title {
        font-size: 16px;
        font-weight: 500;
        margin-top: 12px;
        margin-bottom: 6px;
        border-bottom: 1px solid #d9d9d9;
        padding-bottom: 4px;
    }

    .metric-card {
        border: 1px solid #d9d9d9;
        background: #fffafc;
        padding: 10px 12px;
        min-height: 86px;
        border-radius: 5px;
    }

    .metric-title {
        font-size: 12px;
        color: #444;
        line-height: 1.15;
        height: 28px;
        overflow: hidden;
    }

    .metric-value {
        font-size: 22px;
        color: #111;
        margin-top: 5px;
        line-height: 1.1;
    }

    .metric-delta {
        font-size: 11px;
        color: #666;
        margin-top: 4px;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #d9d9d9;
        border-radius: 4px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
    }

    .stTabs [data-baseweb="tab"] {
        border: 1px solid #d9d9d9;
        border-radius: 4px 4px 0 0;
        padding: 8px 12px;
        background: #fafafa;
    }

    .stTabs [aria-selected="true"] {
        background: #fff2f7 !important;
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


def load_master():
    if not MASTER_FILE.exists():
        return pd.DataFrame()

    master = pd.read_csv(MASTER_FILE)
    return master


def display_date(series):
    return pd.to_datetime(series, errors="coerce").dt.strftime("%d/%b/%Y")


def clean_display_df(df):
    out = df.copy()
    out["Date"] = display_date(out["Date"])

    for col in out.columns:
        if col != "Date":
            out[col] = out[col].fillna("")
            out[col] = out[col].replace({"None": "", "nan": ""})

    return out


def latest_value_and_delta(df, col):
    if col not in df.columns:
        return "-", "Column missing"

    temp = df[["Date", col]].copy()
    temp[col] = pd.to_numeric(temp[col], errors="coerce")
    temp = temp.dropna(subset=[col]).sort_values("Date", ascending=False)

    if temp.empty:
        return "-", "No value"

    latest = temp.iloc[0][col]

    if len(temp) < 2:
        return f"{latest:,.2f}", "First value"

    previous = temp.iloc[1][col]
    change = latest - previous
    pct = (change / previous * 100) if previous != 0 else None
    sign = "+" if change > 0 else ""

    if pct is None:
        delta = f"{sign}{change:,.2f}"
    else:
        delta = f"{sign}{change:,.2f} ({sign}{pct:,.2f}%)"

    return f"{latest:,.2f}", delta


def make_chart(df, col, title):
    if col not in df.columns:
        return None

    chart_df = df[["Date", col]].copy()
    chart_df[col] = pd.to_numeric(chart_df[col], errors="coerce")
    chart_df = chart_df.dropna(subset=[col]).sort_values("Date")

    if chart_df.empty:
        return None

    fig = px.line(chart_df, x="Date", y=col, markers=True, title=title.replace(" (USD/t)", ""))

    fig.update_layout(
        height=280,
        margin=dict(l=10, r=10, t=36, b=10),
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


df = load_data()
master = load_master()

st.markdown(
    f"""
    <div class="app-header">
        <div class="app-title">{APP_TITLE}</div>
        <div class="app-subtitle">{APP_SUBTITLE} | Daily aluminium market index capture | Latest row on top</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if df.empty:
    st.warning("No Pink Sheet data found.")
    st.stop()

display_df = clean_display_df(df)
available_indices = [c for c in df.columns if c != "Date"]
latest_date = display_df["Date"].iloc[0] if not display_df.empty else "-"

# Top controls
top1, top2, top3, top4 = st.columns([1, 1, 1, 2])

with top1:
    st.download_button(
        "Download Excel",
        data=excel_download_bytes(),
        file_name="Aluminium_Index_Bulletin.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

with top2:
    st.download_button(
        "Download CSV",
        data=display_df.to_csv(index=False).encode("utf-8"),
        file_name="pink_sheet.csv",
        mime="text/csv",
        use_container_width=True,
    )

with top3:
    st.metric("Latest Date", latest_date)

with top4:
    st.caption("CSV stores raw data only. Excel stores formatted Pink Sheet view.")

tab_overview, tab_sheet, tab_analytics, tab_master = st.tabs(
    ["Overview", "Pink Sheet", "Analytics", "Master Index"]
)

with tab_overview:
    st.markdown('<div class="section-title">Status</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Captured Days</div>
                <div class="metric-value">{len(df)}</div>
                <div class="metric-delta">One row per day</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Total Indices</div>
                <div class="metric-value">{len(available_indices)}</div>
                <div class="metric-delta">Master-driven</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        missing_latest = display_df.iloc[0].drop(labels=["Date"], errors="ignore").replace("", pd.NA).isna().sum()
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Missing Values Latest Row</div>
                <div class="metric-value">{missing_latest}</div>
                <div class="metric-delta">Blank retained</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Display Date Format</div>
                <div class="metric-value">{latest_date}</div>
                <div class="metric-delta">dd/mmm/yyyy</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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

with tab_sheet:
    st.markdown('<div class="section-title">Last 15 Days Pink Sheet Browser</div>', unsafe_allow_html=True)

    default_cols = ["Date"] + [c for c in FIXED_INDICES if c in display_df.columns]

    selected_cols = st.multiselect(
        "Choose columns to display",
        options=display_df.columns.tolist(),
        default=default_cols,
    )

    if not selected_cols:
        selected_cols = default_cols

    compact_df = display_df[selected_cols].head(15)

    column_config = {}
    for col in compact_df.columns:
        column_config[col] = st.column_config.TextColumn(
            col,
            width="small",
        )

    st.dataframe(
        compact_df,
        use_container_width=True,
        hide_index=True,
        height=430,
        column_config=column_config,
    )

with tab_analytics:
    st.markdown('<div class="section-title">Fixed Graphs</div>', unsafe_allow_html=True)

    g1, g2 = st.columns(2)

    with g1:
        fig = make_chart(df, FIXED_INDICES[0], FIXED_INDICES[0])
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No numeric data available for {FIXED_INDICES[0]}")

    with g2:
        fig = make_chart(df, FIXED_INDICES[1], FIXED_INDICES[1])
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No numeric data available for {FIXED_INDICES[1]}")

    g3, g4 = st.columns(2)

    with g3:
        fig = make_chart(df, FIXED_INDICES[2], FIXED_INDICES[2])
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No numeric data available for {FIXED_INDICES[2]}")

    with g4:
        fig = make_chart(df, FIXED_INDICES[3], FIXED_INDICES[3])
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No numeric data available for {FIXED_INDICES[3]}")

    st.markdown('<div class="section-title">Dropdown Analytics</div>', unsafe_allow_html=True)

    left, right = st.columns(2)

    with left:
        selected_index = st.selectbox(
            "Single Index",
            available_indices,
            index=available_indices.index(FIXED_INDICES[0]) if FIXED_INDICES[0] in available_indices else 0,
        )

        fig = make_chart(df, selected_index, selected_index)

        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No numeric data available for selected index.")

    with right:
        default_comp = [x for x in FIXED_INDICES if x in available_indices][:2]

        comparison_indices = st.multiselect(
            "Compare Indices",
            available_indices,
            default=default_comp,
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
                    title="Comparison",
                )
                fig.update_layout(
                    height=300,
                    margin=dict(l=10, r=10, t=36, b=10),
                    font=dict(family="Arial Narrow", size=11),
                    title=dict(font=dict(size=14)),
                    xaxis_title="",
                    yaxis_title="USD/t",
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                )
                fig.update_xaxes(showgrid=True, gridcolor="#eeeeee")
                fig.update_yaxes(showgrid=True, gridcolor="#eeeeee")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No numeric data available for selected comparison indices.")

with tab_master:
    st.markdown('<div class="section-title">Master Index List</div>', unsafe_allow_html=True)

    if master.empty:
        st.info("Master index file not found.")
    else:
        section_options = ["All"] + sorted(master["Section"].dropna().astype(str).unique().tolist()) if "Section" in master.columns else ["All"]
        selected_section = st.selectbox("Filter by section", section_options)

        view = master.copy()
        if selected_section != "All" and "Section" in view.columns:
            view = view[view["Section"].astype(str) == selected_section]

        st.dataframe(
            view,
            use_container_width=True,
            hide_index=True,
            height=520,
        )
