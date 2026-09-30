"""Basic analytics for NSE FII/DII market data.

This module reads the stored SQLite database and computes a few simple market
signals that are useful for trend tracking:

- rolling 7-day average net flow
- current monthly summary
- bullish vs bearish count
- last N records

It is intentionally lightweight and designed to be extended later with charts,
sector analysis, or correlation with the Nifty.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


class MarketAnalytics:
    """Compute simple analytics from the SQLite-backed FII/DII dataset."""

    def __init__(self, db_path: str = "data/fii_dii_daily.db") -> None:
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        return sqlite3.connect(self.db_path)

    def load(self) -> pd.DataFrame:
        """Load the data from SQLite into a pandas dataframe."""
        with self._connect() as conn:
            df = pd.read_sql_query("SELECT * FROM fii_dii_daily ORDER BY date", conn)
        if df.empty:
            return df

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for column in [
            "fii_buy_cr",
            "fii_sell_cr",
            "fii_net_cr",
            "dii_buy_cr",
            "dii_sell_cr",
            "dii_net_cr",
            "total_net_cr",
        ]:
            df[column] = pd.to_numeric(df[column], errors="coerce")

        return df.dropna(subset=["date"]).reset_index(drop=True)

    def rolling_7day(self) -> pd.Series:
        """Return the rolling 7-day average of total net flow."""
        df = self.load()
        if df.empty:
            return pd.Series(dtype=float)
        return df["total_net_cr"].rolling(window=7, min_periods=1).mean()

    def latest_summary(self, rows: int = 10) -> pd.DataFrame:
        """Return the most recent rows in the dataset."""
        df = self.load()
        if df.empty:
            return df
        return df.tail(rows).reset_index(drop=True)

    def bullish_bearish_counts(self) -> dict[str, int]:
        """Count bullish vs bearish days based on total net flow."""
        df = self.load()
        if df.empty:
            return {"bullish": 0, "bearish": 0, "neutral": 0}

        bullish = int((df["total_net_cr"] > 0).sum())
        bearish = int((df["total_net_cr"] < 0).sum())
        neutral = int((df["total_net_cr"] == 0).sum())
        return {"bullish": bullish, "bearish": bearish, "neutral": neutral}

    def monthly_summary(self) -> pd.DataFrame:
        """Aggregate by month."""
        df = self.load()
        if df.empty:
            return pd.DataFrame(columns=["month", "fii_net_cr", "dii_net_cr", "total_net_cr"])

        monthly = df.groupby(df["date"].dt.to_period("M")).agg(
            fii_net_cr=("fii_net_cr", "sum"),
            dii_net_cr=("dii_net_cr", "sum"),
            total_net_cr=("total_net_cr", "sum"),
        ).reset_index()
        monthly["month"] = monthly["date"].astype(str)
        return monthly[["month", "fii_net_cr", "dii_net_cr", "total_net_cr"]]


if __name__ == "__main__":
    analytics = MarketAnalytics()
    print(analytics.latest_summary(5))
    print(analytics.bullish_bearish_counts())
    print(analytics.monthly_summary())
