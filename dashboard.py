"""Streamlit dashboard for the NSE FII/DII data project.

This dashboard reads the SQLite-backed dataset and shows:
- summary metrics
- total net flow trend
- FII vs DII comparison
- monthly totals
- recent daily activity
- generated alerts
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from analytics import MarketAnalytics


def load_data(db_path: str = "data/fii_dii_daily.db") -> pd.DataFrame:
    """Load and prepare the dataset for visualization."""
    analytics = MarketAnalytics(db_path=db_path)
    df = analytics.load()
    if df.empty:
        return df

    df = df.sort_values("date").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return df


def load_alerts(alerts_path: str = "data/alerts.json") -> pd.DataFrame:
    """Load alert records if available."""
    path = Path(alerts_path)
    if not path.exists():
        return pd.DataFrame(columns=["timestamp", "type", "severity", "message"])

    try:
        data = pd.read_json(path)
    except ValueError:
        return pd.DataFrame(columns=["timestamp", "type", "severity", "message"])

    if data.empty:
        return pd.DataFrame(columns=["timestamp", "type", "severity", "message"])

    return data[["timestamp", "type", "severity", "message"]].copy()


st.set_page_config(page_title="FII/DII Dashboard", layout="wide")
st.title("NSE FII/DII Market Dashboard")

try:
    df = load_data()
except FileNotFoundError:
    st.warning("No database found. Run the collector first to generate `data/fii_dii_daily.db`.")
    st.stop()

if df.empty:
    st.info("No FII/DII records available yet.")
    st.stop()

plot_df = df.copy()
plot_df["date"] = pd.to_datetime(plot_df["date"])

latest = plot_df.iloc[-1]
latest_date = latest["date"].strftime("%Y-%m-%d")
latest_total = float(latest["total_net_cr"])
last_7_avg = float(plot_df["total_net_cr"].tail(7).mean())

col1, col2, col3, col4 = st.columns(4)
col1.metric("Records", len(plot_df))
col2.metric("Latest Date", latest_date)
col3.metric("Latest Net", f"{latest_total:,.2f} Cr")
col4.metric("7-Day Avg", f"{last_7_avg:,.2f} Cr")

st.subheader("Total Net Flow")
line_data = plot_df[["date", "fii_net_cr", "dii_net_cr", "total_net_cr"]].copy()
line_data = line_data.rename(columns={
    "fii_net_cr": "FII Net",
    "dii_net_cr": "DII Net",
    "total_net_cr": "Total Net",
})
st.line_chart(line_data.set_index("date"))

monthly = (
    plot_df.assign(month=plot_df["date"].dt.to_period("M").astype(str))
    .groupby("month")
    .agg(
        fii_net_cr=("fii_net_cr", "sum"),
        dii_net_cr=("dii_net_cr", "sum"),
        total_net_cr=("total_net_cr", "sum"),
    )
    .reset_index()
)

st.subheader("Monthly Summary")
st.bar_chart(monthly.set_index("month")[["fii_net_cr", "dii_net_cr", "total_net_cr"]])

left_col, right_col = st.columns(2)
with left_col:
    bullish_days = int((plot_df["total_net_cr"] > 0).sum())
    bearish_days = int((plot_df["total_net_cr"] < 0).sum())
    neutral_days = int((plot_df["total_net_cr"] == 0).sum())
    st.subheader("Trend Counts")
    st.write({
        "Bullish days": bullish_days,
        "Bearish days": bearish_days,
        "Neutral days": neutral_days,
    })

with right_col:
    st.subheader("Recent Alerts")
    alerts = load_alerts()
    if alerts.empty:
        st.info("No alerts generated yet.")
    else:
        st.dataframe(alerts.tail(10), use_container_width=True)

st.subheader("Recent Activity")
recent = plot_df.tail(10)[["date", "fii_net_cr", "dii_net_cr", "total_net_cr"]].copy()
recent = recent.rename(columns={
    "fii_net_cr": "FII Net",
    "dii_net_cr": "DII Net",
    "total_net_cr": "Total Net",
})
st.dataframe(recent, use_container_width=True)

st.sidebar.header("Filters")
start_date = st.sidebar.date_input("Start date", value=pd.to_datetime(plot_df["date"].min()).date())
end_date = st.sidebar.date_input("End date", value=pd.to_datetime(plot_df["date"].max()).date())

filtered = plot_df[
    (plot_df["date"] >= pd.Timestamp(start_date)) & (plot_df["date"] <= pd.Timestamp(end_date))
]
if not filtered.empty:
    st.sidebar.subheader("Filtered Summary")
    st.sidebar.metric("Filtered total", f"{filtered['total_net_cr'].sum():,.2f} Cr")
    st.sidebar.metric("Filtered avg", f"{filtered['total_net_cr'].mean():,.2f} Cr")
