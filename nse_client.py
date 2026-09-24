"""NSE data access layer for FII and DII activity.

This module is intentionally isolated from the CLI entry point so the raw
NSE API access logic is easier to test, replace, and evolve over time.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class NSEClient:
    """Handle browser-like session setup and FII/DII data retrieval from NSE.

    NSE exposes the FII/DII data through a browser-backed endpoint. The client
    first loads the website home page to obtain cookies before requesting the
    JSON payload. This mimics a normal browser and improves compatibility.
    """

    BASE_URL = "https://www.nseindia.com"
    SOURCE_PAGE = f"{BASE_URL}/market-data/fii-dii-activity"
    FIIDII_API_URL = f"{BASE_URL}/api/fiidii"

    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": self.SOURCE_PAGE,
                "Connection": "keep-alive",
            }
        )

        retry_policy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            raise_on_status=False,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry_policy))

    def bootstrap_session(self) -> None:
        """Open the NSE home page to initialize cookies and session state."""
        logger.info("Bootstrapping NSE session...")
        response = self.session.get(self.BASE_URL, timeout=self.timeout)
        response.raise_for_status()

    def fetch_raw_data(self) -> Any:
        """Return the untouched JSON payload from the NSE FII/DII endpoint."""
        self.bootstrap_session()
        logger.info("Fetching NSE FII/DII API data...")
        response = self.session.get(self.FIIDII_API_URL, timeout=self.timeout)
        response.raise_for_status()

        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError(
                "NSE returned a non-JSON response. The endpoint may have changed "
                "or access may be blocked."
            ) from exc

    @staticmethod
    def _as_float(value: Any) -> float | None:
        """Convert common NSE numeric strings to floats."""
        if value in (None, "", "-"):
            return None

        try:
            return float(str(value).replace(",", ""))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_records(payload: Any) -> list[dict[str, Any]]:
        """Locate the list-like payload that contains the row data."""
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]

        if isinstance(payload, dict):
            for key in ("data", "records", "rows"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [row for row in value if isinstance(row, dict)]

        raise ValueError("Unsupported NSE FII/DII payload structure")

    def normalize(self, payload: Any) -> pd.DataFrame:
        """Normalize the NSE response into a consistent dataframe schema."""
        records: list[dict[str, Any]] = []

        for row in self._extract_records(payload):
            fii_buy = self._as_float(row.get("buyValue"))
            fii_sell = self._as_float(row.get("sellValue"))
            fii_net = self._as_float(row.get("netValue"))
            dii_buy = self._as_float(row.get("buyValueDII"))
            dii_sell = self._as_float(row.get("sellValueDII"))
            dii_net = self._as_float(row.get("netValueDII"))

            records.append(
                {
                    "date": row.get("date") or row.get("dateTime"),
                    "fii_buy_cr": fii_buy,
                    "fii_sell_cr": fii_sell,
                    "fii_net_cr": fii_net,
                    "dii_buy_cr": dii_buy,
                    "dii_sell_cr": dii_sell,
                    "dii_net_cr": dii_net,
                }
            )

        dataframe = pd.DataFrame(records)

        if not dataframe.empty:
            dataframe["total_net_cr"] = (
                dataframe["fii_net_cr"].fillna(0)
                + dataframe["dii_net_cr"].fillna(0)
            )

        return dataframe

    def fetch_current_data(self) -> pd.DataFrame:
        """Fetch and normalize the latest available NSE FII/DII data."""
        return self.normalize(self.fetch_raw_data())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = NSEClient()
    data = client.fetch_current_data()
    print(data.head())
