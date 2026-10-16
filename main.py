"""Command-line entry point for collecting NSE FII/DII market data.

This script is intentionally small and orchestrates the project layers:
- fetch raw data from NSE
- normalize into a dataframe
- validate data quality
- append the new data to the local CSV store
- print a concise summary for easy debugging

The logic is deliberately simple so the project remains easy to extend with
historical fetching, validation, and scheduled collection.
"""

from __future__ import annotations

import logging

from nse_client import NSEClient
from notifier import AlertNotifier
from report import generate_summary_image, generate_report
from storage import DataStore
from validation import assert_no_duplicates, validate_dataframe
from alerts import AlertGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the current-day NSE FII/DII ingestion workflow."""
    logger.info("Starting NSE FII/DII data collection...")

    client = NSEClient()
    store = DataStore()
    notifier = AlertNotifier()
    alert_gen = AlertGenerator()

    try:
        dataframe = client.fetch_current_data()
        logger.info("Fetched %d rows from NSE", len(dataframe))

        validated = validate_dataframe(dataframe)
        logger.info("Validation passed. %d rows retained", len(validated))

        validated = assert_no_duplicates(validated)

        output_path = store.append_csv(validated, filename="fii_dii_daily.csv")
        logger.info("Data collection complete. Output: %s", output_path)

        # Generate textual report and chart image
        report_path = generate_report()
        image_path, caption = generate_summary_image()

        # Generate structured alerts
        alerts = alert_gen.run_all_checks()
        if alerts:
            # persist alerts locally for audit
            alert_gen.save_alerts()

        # Use the enhanced notifier to deliver summary, alerts, and image together
        delivery = notifier.notify_enhanced(alerts, summary=caption, image_path=image_path)
        logger.info("Notification delivery results: %s", delivery)

        print(f"\n✓ Successfully saved {len(validated)} rows to {output_path}")
        print(f"✓ Report written to: {report_path}")
        if image_path:
            print(f"✓ Summary image: {image_path}")

    except Exception as exc:
        logger.error("Data collection failed: %s", exc, exc_info=True)
        print(f"\n✗ Error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
