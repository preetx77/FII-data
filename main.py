"""Command-line entry point for collecting NSE FII/DII market data.

This script is intentionally small and orchestrates the project layers:
- fetch raw data from NSE
- normalize into a dataframe
- append the new data to the local CSV store
- print a concise summary for easy debugging

The logic is deliberately simple so the project remains easy to extend with
historical fetching, validation, and scheduled collection.
"""

from __future__ import annotations

import logging

from nse_client import NSEClient
from storage import DataStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the current-day NSE FII/DII ingestion workflow."""
    client = NSEClient()
    store = DataStore()

    logger.info("Starting current NSE FII/DII fetch...")
    dataframe = client.fetch_current_data()

    if dataframe.empty:
        logger.warning("NSE returned no rows. No data was saved.")
        return

    output_path = store.append_csv(dataframe, filename="fii_dii_daily.csv")
    logger.info("Completed fetch. Saved file: %s", output_path)
    logger.info("Rows saved: %s", len(dataframe))

    print(f"Saved {len(dataframe)} rows to {output_path}")


if __name__ == "__main__":
    main()
