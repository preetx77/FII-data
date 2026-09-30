"""Generate a readable summary report from the stored FII/DII data.

This script reads the SQLite dataset produced by the data pipeline and prints
an analyst-friendly summary, including recent activity, bullish/bearish counts,
and monthly totals.
"""

from __future__ import annotations

from pathlib import Path

from analytics import MarketAnalytics


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
    print(f"Summary written to: {output}")
    print(Path(output).read_text(encoding="utf-8"))
