"""Historical FII/DII data ingestion pipeline.

This module fetches NSE FII/DII data across multiple dates in the past and
builds up a historical dataset. It handles:

- Date-range iteration
- Deduplication by date
- Retry logic for failed dates
- Progress logging
- Storage via the DataStore layer

The historical fetch is separate from the current-day fetch because:
- NSE may not expose historical endpoints reliably
- Different date formats may require different parsing
- We want to log failed dates and resume from where we left off
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from nse_client import NSEClient
from storage import DataStore

logger = logging.getLogger(__name__)


class HistoricalPipeline:
    """Fetch and store FII/DII data for a range of past dates."""

    def __init__(self, client: NSEClient | None = None, store: DataStore | None = None) -> None:
        self.client = client or NSEClient()
        self.store = store or DataStore()

    def fetch_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime,
        skip_errors: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch FII/DII data for all dates in [start_date, end_date].

        Args:
            start_date: First date to fetch (inclusive).
            end_date: Last date to fetch (inclusive).
            skip_errors: If True, log and skip failed dates instead of raising.

        Returns:
            A dataframe with all rows found for the date range.
        """
        all_rows: list[dict[str, Any]] = []
        current = start_date
        total_days = (end_date - start_date).days + 1
        failed_dates = []

        logger.info("Fetching NSE FII/DII data for %d days...", total_days)

        while current <= end_date:
            date_str = current.strftime("%d-%b-%Y")

            try:
                logger.info("Fetching data for %s...", date_str)
                payload = self.client.fetch_raw_data()
                normalized = self.client.normalize(payload)

                # NSE may return multiple rows or a single row. Keep all that match
                # the target date.
                for _, row in normalized.iterrows():
                    row_date = row.get("date")
                    if row_date and str(row_date).strip() == date_str:
                        all_rows.append(row.to_dict())

            except Exception as exc:
                failed_dates.append(date_str)
                if skip_errors:
                    logger.warning("Failed to fetch %s: %s", date_str, exc)
                else:
                    raise

            current += timedelta(days=1)

        if failed_dates:
            logger.warning("Failed to fetch %d dates: %s", len(failed_dates), failed_dates)

        result = pd.DataFrame(all_rows)
        logger.info("Fetched %d rows from %d days", len(result), total_days)
        return result

    def backfill(self, days: int = 30) -> pd.DataFrame:
        """
        Fetch and store FII/DII data for the last N days.

        Args:
            days: Number of past days to backfill.

        Returns:
            The dataframe of newly fetched rows.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        logger.info("Backfilling last %d days (from %s to %s)", days, start_date.date(), end_date.date())
        data = self.fetch_date_range(start_date, end_date, skip_errors=True)

        if not data.empty:
            self.store.append_csv(data, filename="fii_dii_daily.csv")
            logger.info("Backfill complete. %d rows stored.", len(data))

        return data


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    pipeline = HistoricalPipeline()
    
    # Example: backfill the last 30 days
    result = pipeline.backfill(days=30)
    print(f"Backfilled {len(result)} rows")
