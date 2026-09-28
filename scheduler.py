"""Scheduler for daily NSE FII/DII collection.

This module is intentionally lightweight and can be run via a cron job or a
continuous scheduler. The goal is to keep the ingestion simple and predictable:

- fetch current-day data
- validate it
- save it to CSV
- log execution status

For a production system, you may later replace this with APScheduler, cron, or
an external orchestrator.
"""

from __future__ import annotations

import logging
from datetime import datetime

from nse_client import NSEClient
from storage import DataStore
from validation import assert_no_duplicates, validate_dataframe

logger = logging.getLogger(__name__)


class DailyScheduler:
    """Run the daily NSE FII/DII collection workflow."""

    def __init__(self, client: NSEClient | None = None, store: DataStore | None = None) -> None:
        self.client = client or NSEClient()
        self.store = store or DataStore()

    def run_once(self) -> str:
        """One execution of the daily workflow."""
        logger.info("Daily scheduler started at %s", datetime.utcnow().isoformat())

        dataframe = self.client.fetch_current_data()
        validated = validate_dataframe(dataframe)
        validated = assert_no_duplicates(validated)

        output = self.store.append_csv(validated, filename="fii_dii_daily.csv")
        logger.info("Daily scheduler complete. Output: %s", output)
        return str(output)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    scheduler = DailyScheduler()
    scheduler.run_once()
