"""Validation helpers for NSE FII/DII data.

These checks keep the project resilient when NSE changes field names or
returns partial records. The goal is to fail early with a clear message,
not silently write bad data.
"""

from __future__ import annotations

import logging
from typing import Iterable

import pandas as pd

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {
    "date",
    "fii_buy_cr",
    "fii_sell_cr",
    "fii_net_cr",
    "dii_buy_cr",
    "dii_sell_cr",
    "dii_net_cr",
    "total_net_cr",
}


def validate_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Validate a normalized FII/DII dataframe and return a cleaned copy."""
    if dataframe is None:
        raise ValueError("Dataframe is None")

    if dataframe.empty:
        raise ValueError("No data rows available for validation")

    missing = REQUIRED_COLUMNS - set(dataframe.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    cleaned = dataframe.copy()
    cleaned["date"] = cleaned["date"].astype(str).str.strip()
    cleaned = cleaned[cleaned["date"] != "nan"]
    cleaned = cleaned.dropna(subset=["date"]).copy()

    numeric_columns = [
        "fii_buy_cr",
        "fii_sell_cr",
        "fii_net_cr",
        "dii_buy_cr",
        "dii_sell_cr",
        "dii_net_cr",
        "total_net_cr",
    ]

    for column in numeric_columns:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    cleaned = cleaned.dropna(subset=numeric_columns, how="all").copy()

    if cleaned.empty:
        raise ValueError("No valid rows remained after validation")

    logger.info("Validated %s rows with %s required columns", len(cleaned), len(REQUIRED_COLUMNS))
    return cleaned.sort_values("date").reset_index(drop=True)


def assert_no_duplicates(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Drop duplicate dates while keeping the latest instance."""
    duplicates = dataframe.duplicated(subset=["date"], keep="last")
    if duplicates.any():
        logger.warning("Dropped %s duplicate date rows", int(duplicates.sum()))
        dataframe = dataframe.loc[~duplicates].copy()
    return dataframe


if __name__ == "__main__":
    sample = pd.DataFrame(
        [{
            "date": "2024-01-01",
            "fii_buy_cr": 100,
            "fii_sell_cr": 50,
            "fii_net_cr": 50,
            "dii_buy_cr": 30,
            "dii_sell_cr": 20,
            "dii_net_cr": 10,
            "total_net_cr": 60,
        }]
    )
    print(validate_dataframe(sample))
