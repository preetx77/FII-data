"""Command-line entry point for collecting NSE FII/DII market data.

This script orchestrates fetching, validation, persistence, reporting, alerting,
and notification delivery.
"""

from __future__ import annotations

import logging

from alerts import AlertGenerator
from nse_client import NSEClient
from notifier import AlertNotifier
from report import generate_summary_image, generate_report
from storage import DataStore
from validation import assert_no_duplicates, validate_dataframe

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
        # Analytics, reports, and alerts read from SQLite; keep it in sync with CSV.
        store.append_sqlite(validated)
        logger.info("Data collection complete. Output: %s", output_path)

        report_path = generate_report()
        alerts = alert_gen.run_all_checks()
        if alerts:
            alert_gen.save_alerts()

        image_path, caption = generate_summary_image(alerts=alerts)
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
