"""Storage helpers for NSE FII/DII data.

The project stores historical data in a local dataset folder and uses CSV as
its durable, human-readable format for the first version. This is simpler than
SQLite for a small project and easier to inspect manually in Git or a local
folder.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class DataStore:
    """Persist normalized FII/DII market data to local disk."""

    def __init__(self, base_dir: str = "data") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_csv(self, dataframe: pd.DataFrame, filename: str = "fii_dii_daily.csv") -> Path:
        """Write the dataframe to CSV and return the file path."""
        if dataframe.empty:
            logger.warning("No rows to save for %s", filename)

        path = self.base_dir / filename
        dataframe.to_csv(path, index=False)
        logger.info("Saved %s rows to %s", len(dataframe), path)
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
        if path.exists():
            existing = pd.read_csv(path)
            combined = pd.concat([existing, dataframe], ignore_index=True)
            combined = combined.drop_duplicates(subset=["date"], keep="last")
            combined.to_csv(path, index=False)
            logger.info("Updated dataset at %s with %s rows", path, len(combined))
            return path

        return self.save_csv(dataframe, filename)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    store = DataStore()
    sample = pd.DataFrame(
        [{"date": "2024-01-01", "fii_buy_cr": 100.0, "fii_sell_cr": 50.0, "fii_net_cr": 50.0}] 
    )
    store.save_csv(sample)
