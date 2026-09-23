"""Fetch daily FII/DII activity from NSE India.

Official NSE source page:
    https://www.nseindia.com/market-data/fii-dii-activity

NSE endpoint used by that page:
    https://www.nseindia.com/api/fiidii

NSE may change this endpoint or require browser-like session headers. The
client therefore bootstraps a session against the NSE website before calling
the API and keeps the raw response available for troubleshooting.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


LOGGER = logging.getLogger(__name__)


class NSEFIIDataFetcher:
    """Fetch and normalize the FII/DII data displayed by NSE India."""

    BASE_URL = "https://www.nseindia.com"
    SOURCE_PAGE = f"{BASE_URL}/market-data/fii-dii-activity"
    API_URL = f"{BASE_URL}/api/fiidii"

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

        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            raise_on_status=False,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def _bootstrap(self) -> None:
        """Obtain NSE cookies before requesting the API endpoint."""
        response = self.session.get(self.BASE_URL, timeout=self.timeout)
        response.raise_for_status()

    def fetch_raw(self) -> Any:
        """Return the raw JSON response from NSE."""
        self._bootstrap()
        response = self.session.get(self.API_URL, timeout=self.timeout)
        response.raise_for_status()

        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError(
                "NSE returned a non-JSON response. The endpoint may have "
                "changed or access may have been blocked."
            ) from exc

    @staticmethod
    def _records(payload: Any) -> list[dict[str, Any]]:
        """Extract record rows from the response while tolerating NSE wrappers."""
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]

        if isinstance(payload, dict):
            for key in ("data", "records", "rows"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [row for row in value if isinstance(row, dict)]

        raise ValueError("Unexpected NSE FII/DII response format")

    @staticmethod
    def _number(row: dict[str, Any], *keys: str) -> float | None:
        for key in keys:
            if key in row and row[key] not in (None, "", "-"):
                try:
                    return float(str(row[key]).replace(",", ""))
                except (TypeError, ValueError):
                    return None
        return None

    def normalize(self, payload: Any) -> pd.DataFrame:
        """Convert NSE rows to a stable FII/DII schema."""
        normalized: list[dict[str, Any]] = []
        for row in self._records(payload):
            fii_buy = self._number(row, "buyValue", "fiiBuy", "fii_buy")
            fii_sell = self._number(row, "sellValue", "fiiSell", "fii_sell")
            fii_net = self._number(row, "netValue", "fiiNet", "fii_net")
            dii_buy = self._number(row, "buyValueDII", "diiBuy", "dii_buy")
            dii_sell = self._number(row, "sellValueDII", "diiSell", "dii_sell")
            dii_net = self._number(row, "netValueDII", "diiNet", "dii_net")

            normalized.append(
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

        frame = pd.DataFrame(normalized)
        if not frame.empty:
            frame["total_net_cr"] = frame["fii_net_cr"].fillna(0) + frame["dii_net_cr"].fillna(0)
        return frame

    def fetch(self) -> pd.DataFrame:
        return self.normalize(self.fetch_raw())

    @staticmethod
    def save_csv(data: pd.DataFrame, filename: str = "data/fii_dii_daily.csv") -> Path:
        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(path, index=False)
        return path


# Backwards-compatible alias for users of the original scaffold.
FIIDataFetcher = NSEFIIDataFetcher


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetcher = NSEFIIDataFetcher()

    try:
        raw = fetcher.fetch_raw()
        data = fetcher.normalize(raw)
        output = fetcher.save_csv(data)

        # Keep the source and retrieval time visible in the command output.
        print(f"Source page: {fetcher.SOURCE_PAGE}")
        print(f"API endpoint: {fetcher.API_URL}")
        print(f"Retrieved at: {datetime.now(timezone.utc).isoformat()}")
        print(f"Saved {len(data)} row(s) to {output}")
    except (requests.RequestException, RuntimeError, ValueError) as exc:
        LOGGER.error("Unable to fetch NSE FII/DII data: %s", exc)
        raise SystemExit(1) from exc
