"""Storage helpers for NSE FII/DII data.

The project stores daily market data in a local data folder. It supports:
- CSV export for quick inspection and Git tracking
- SQLite persistence for a more robust local database layer

SQLite is used as the durable historical store while CSV remains available as
an easy-to-read export format.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class DataStore:
    """Persist normalized FII/DII market data to local disk."""

    DEFAULT_COLUMNS = [
        "date",
        "fii_buy_cr",
        "fii_sell_cr",
        "fii_net_cr",
        "dii_buy_cr",
        "dii_sell_cr",
        "dii_net_cr",
        "total_net_cr",
    ]

    def __init__(
        self,
        base_dir: str = "data",
        csv_filename: str = "fii_dii_daily.csv",
        db_filename: str = "fii_dii_daily.db",
        table_name: str = "fii_dii_daily",
    ) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.base_dir / csv_filename
        self.db_path = self.base_dir / db_filename
        self.table_name = table_name

    def _normalize_columns(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Ensure expected columns exist before persistence."""
        missing = [column for column in self.DEFAULT_COLUMNS if column not in dataframe.columns]
        if missing:
            raise ValueError(f"Missing required columns for storage: {missing}")
        return dataframe[self.DEFAULT_COLUMNS].copy()

    def save_csv(self, dataframe: pd.DataFrame, filename: str = "fii_dii_daily.csv") -> Path:
        """Write the dataframe to CSV and return the file path."""
        ordered = self._normalize_columns(dataframe)
        if ordered.empty:
            logger.warning("No rows to save for %s", filename)

        path = self.base_dir / filename
        ordered.to_csv(path, index=False)
        logger.info("Saved %s rows to %s", len(ordered), path)
        return path

    def read_csv(self, filename: str = "fii_dii_daily.csv") -> pd.DataFrame:
        """Read a stored dataset back into memory."""
        path = self.base_dir / filename
        if not path.exists():
            logger.warning("Dataset not found at %s", path)
            return pd.DataFrame()

        return pd.read_csv(path)

    def append_csv(self, dataframe: pd.DataFrame, filename: str = "fii_dii_daily.csv") -> Path:
        """Append or create a CSV dataset while preserving previous history."""
        path = self.base_dir / filename
        ordered = self._normalize_columns(dataframe)

        if path.exists():
            existing = pd.read_csv(path)
            combined = pd.concat([existing, ordered], ignore_index=True)
            combined = combined.drop_duplicates(subset=["date"], keep="last")
            combined = combined[self.DEFAULT_COLUMNS]
            combined.to_csv(path, index=False)
            logger.info("Updated dataset at %s with %s rows", path, len(combined))
            return path

        return self.save_csv(ordered, filename)

    def read_sqlite(self, table_name: str | None = None) -> pd.DataFrame:
        """Read the SQLite dataset into a dataframe."""
        target_table = table_name or self.table_name
        db_path = str(self.db_path)

        if not self.db_path.exists():
            logger.warning("SQLite dataset not found at %s", db_path)
            return pd.DataFrame()

        with sqlite3.connect(db_path) as conn:
            return pd.read_sql_query(f"SELECT * FROM {target_table}", conn)

    def save_sqlite(self, dataframe: pd.DataFrame, table_name: str | None = None) -> Path:
        """Persist a dataframe into SQLite while merging duplicate dates."""
        ordered = self._normalize_columns(dataframe)
        target_table = table_name or self.table_name

        existing = self.read_sqlite(target_table)
        combined = ordered if existing.empty else pd.concat([existing, ordered], ignore_index=True)
        combined = combined.drop_duplicates(subset=["date"], keep="last")
        combined = combined[self.DEFAULT_COLUMNS]

        with sqlite3.connect(self.db_path) as conn:
            combined.to_sql(target_table, conn, if_exists="replace", index=False)

        logger.info("Saved %s rows to SQLite database %s", len(combined), self.db_path)
        return self.db_path

    def append_sqlite(self, dataframe: pd.DataFrame, table_name: str | None = None) -> Path:
        """Append new rows to the SQLite dataset while keeping the latest entry per date."""
        ordered = self._normalize_columns(dataframe)
        target_table = table_name or self.table_name

        existing = self.read_sqlite(target_table)
        combined = ordered if existing.empty else pd.concat([existing, ordered], ignore_index=True)
        combined = combined.drop_duplicates(subset=["date"], keep="last")
        combined = combined[self.DEFAULT_COLUMNS]

        with sqlite3.connect(self.db_path) as conn:
            combined.to_sql(target_table, conn, if_exists="replace", index=False)

        logger.info("Updated SQLite table %s with %s rows", target_table, len(combined))
        return self.db_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    store = DataStore()
    sample = pd.DataFrame(
        [{
            "date": "2024-01-01",
            "fii_buy_cr": 100.0,
            "fii_sell_cr": 50.0,
            "fii_net_cr": 50.0,
            "dii_buy_cr": 30.0,
            "dii_sell_cr": 20.0,
            "dii_net_cr": 10.0,
            "total_net_cr": 60.0,
        }]
    )
    store.save_csv(sample)
    store.save_sqlite(sample)
