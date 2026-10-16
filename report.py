"""Generate a readable summary report from the stored FII/DII data.

This script reads the SQLite dataset produced by the data pipeline and prints
an analyst-friendly summary, including recent activity, bullish/bearish counts,
and monthly totals. It also can embed a short alert summary into the image
caption if alerts are provided.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analytics import MarketAnalytics


def _summarize_alerts(alerts: Iterable[dict] | None) -> str:
    if not alerts:
        return ""
    alerts = list(alerts)
    count = len(alerts)
    # severity ranking
    rank = {"high": 3, "medium": 2, "low": 1, "info": 0}
    top = max(alerts, key=lambda a: rank.get(a.get("severity", "info"), 0))
    top_msg = top.get("message", "")
    return f"{count} alert(s): {top_msg}"


def generate_summary_image(
    db_path: str = "data/fii_dii_daily.db",
    output_path: str = "data/summary.png",
    days: int = 30,
    alerts: Iterable[dict] | None = None,
) -> tuple[str | None, str]:
    """Create a compact chart image and a one-line market summary caption.

    If `alerts` is provided, a short alert summary is appended to the caption.
    """
    analytics = MarketAnalytics(db_path=db_path)
    df = analytics.load()

    if df.empty:
        return None, "No data available. Run the collector first."

    chart_df = df.tail(days).copy()
    chart_df["rolling_7d"] = chart_df["total_net_cr"].rolling(window=7, min_periods=1).mean()

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(chart_df["date"], chart_df["total_net_cr"], label="Total net (cr)", color="#1f77b4", linewidth=2)
    ax.plot(chart_df["date"], chart_df["rolling_7d"], label="7-day avg", color="#ff7f0e", linewidth=2)
    ax.axhline(0, color="gray", linestyle="--", linewidth=1, alpha=0.7)
    ax.set_title("FII/DII net flow")
    ax.set_ylabel("Crore")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()
    fig.savefig(target, dpi=180)
    plt.close(fig)

    latest = chart_df.iloc[-1]
    base_caption = (
        f"Latest date: {latest['date'].strftime('%Y-%m-%d')} | "
        f"Total net: {float(latest['total_net_cr']):,.0f} cr | "
        f"7-day avg: {float(chart_df['rolling_7d'].iloc[-1]):,.0f} cr"
    )

    alert_summary = _summarize_alerts(alerts)
    caption = f"{base_caption}"
    if alert_summary:
        caption = f"{caption} | {alert_summary}"

    return str(target), caption


def generate_report(db_path: str = "data/fii_dii_daily.db", output_path: str = "data/market_summary.txt") -> str:
    """Generate a text summary for the current FII/DII dataset."""
    analytics = MarketAnalytics(db_path=db_path)
    df = analytics.load()

    report_lines = [
        "NSE FII/DII Market Summary",
        "=" * 28,
    ]

    if df.empty:
        report_lines.append("No data available. Run the collector first.")
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
        return str(target)

    latest = analytics.latest_summary(rows=10)
    counts = analytics.bullish_bearish_counts()
    monthly = analytics.monthly_summary().tail(6)
    rolling = analytics.rolling_7day().tail(10)

    latest_net = float(df["total_net_cr"].iloc[-1]) if not df.empty else 0.0
    last_7_avg = float(rolling.iloc[-1]) if not rolling.empty else 0.0
    latest_date = df["date"].max().strftime("%Y-%m-%d")

    report_lines.extend(
        [
            f"Records: {len(df)}",
            f"Latest date: {latest_date}",
            f"Latest total net: {latest_net:,.2f} crore",
            f"7-day average total net: {last_7_avg:,.2f} crore",
            f"Bullish days: {counts['bullish']}",
            f"Bearish days: {counts['bearish']}",
            f"Neutral days: {counts['neutral']}",
            "",
            "Recent activity:",
            latest[["date", "fii_net_cr", "dii_net_cr", "total_net_cr"]].to_string(index=False),
            "",
            "Recent monthly summary:",
            monthly.to_string(index=False),
        ]
    )

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return str(target)


if __name__ == "__main__":
    output = generate_report()
    image_path, caption = generate_summary_image()
    print(f"Summary written to: {output}")
    print(Path(output).read_text(encoding="utf-8"))
    if image_path:
        print(f"Chart written to: {image_path}")
        print(f"Caption: {caption}")
