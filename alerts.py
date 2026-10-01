"""Alert system for significant FII/DII flow events.

This module monitors the stored dataset for market-moving FII/DII activity and
generates alerts when thresholds are breached. Alerts can be:

- Daily extreme flows (large single-day net moves)
- Weekly trend reversals (bullish to bearish or vice versa)
- Monthly cumulative flows (sustained buying or selling)

Alerts are stored as structured JSON events for downstream processing (email,
Slack, webhook, etc.).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from analytics import MarketAnalytics

logger = logging.getLogger(__name__)


class AlertThresholds:
    """Configuration for alert triggers."""

    def __init__(
        self,
        daily_extreme_cr: float = 500.0,
        weekly_bullish_days: int = 4,
        weekly_bearish_days: int = 4,
        monthly_net_cr: float = 2000.0,
    ) -> None:
        self.daily_extreme_cr = daily_extreme_cr
        self.weekly_bullish_days = weekly_bullish_days
        self.weekly_bearish_days = weekly_bearish_days
        self.monthly_net_cr = monthly_net_cr


class AlertGenerator:
    """Generate alerts for significant FII/DII activity."""

    def __init__(
        self,
        db_path: str = "data/fii_dii_daily.db",
        thresholds: AlertThresholds | None = None,
    ) -> None:
        self.analytics = MarketAnalytics(db_path=db_path)
        self.thresholds = thresholds or AlertThresholds()
        self.alerts: list[dict[str, Any]] = []

    def _add_alert(self, alert_type: str, severity: str, message: str, data: dict[str, Any] | None = None) -> None:
        """Add an alert to the internal list."""
        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": alert_type,
            "severity": severity,
            "message": message,
            "data": data or {},
        }
        self.alerts.append(alert)
        logger.info("Alert: [%s] %s - %s", severity.upper(), alert_type, message)

    def check_daily_extremes(self) -> None:
        """Detect single-day extreme FII/DII flows."""
        df = self.analytics.load()
        if df.empty:
            return

        latest = df.iloc[-1]
        abs_total_net = abs(float(latest["total_net_cr"]))

        if abs_total_net > self.thresholds.daily_extreme_cr:
            direction = "BUYING" if latest["total_net_cr"] > 0 else "SELLING"
            self._add_alert(
                alert_type="DAILY_EXTREME",
                severity="high",
                message=f"Extreme {direction} activity: {abs_total_net:,.0f} crore net",
                data={
                    "date": str(latest["date"]),
                    "fii_net": float(latest["fii_net_cr"]),
                    "dii_net": float(latest["dii_net_cr"]),
                    "total_net": float(latest["total_net_cr"]),
                },
            )

    def check_weekly_trend(self) -> None:
        """Detect weekly bullish or bearish trends."""
        df = self.analytics.load()
        if len(df) < 7:
            return

        last_week = df.tail(7)
        bullish_count = int((last_week["total_net_cr"] > 0).sum())
        bearish_count = int((last_week["total_net_cr"] < 0).sum())
        weekly_total = float(last_week["total_net_cr"].sum())

        if bullish_count >= self.thresholds.weekly_bullish_days:
            self._add_alert(
                alert_type="WEEKLY_BULLISH_TREND",
                severity="medium",
                message=f"Strong weekly buying: {bullish_count} bullish days, {weekly_total:,.0f} crore net",
                data={
                    "bullish_days": bullish_count,
                    "bearish_days": bearish_count,
                    "weekly_net": weekly_total,
                    "week_start": str(last_week.iloc[0]["date"]),
                    "week_end": str(last_week.iloc[-1]["date"]),
                },
            )

        if bearish_count >= self.thresholds.weekly_bearish_days:
            self._add_alert(
                alert_type="WEEKLY_BEARISH_TREND",
                severity="medium",
                message=f"Strong weekly selling: {bearish_count} bearish days, {weekly_total:,.0f} crore net",
                data={
                    "bullish_days": bullish_count,
                    "bearish_days": bearish_count,
                    "weekly_net": weekly_total,
                    "week_start": str(last_week.iloc[0]["date"]),
                    "week_end": str(last_week.iloc[-1]["date"]),
                },
            )

    def check_monthly_cumulative(self) -> None:
        """Detect strong monthly cumulative flows."""
        df = self.analytics.load()
        if df.empty:
            return

        current_month = df["date"].max().to_period("M")
        month_data = df[df["date"].dt.to_period("M") == current_month]

        if month_data.empty:
            return

        monthly_net = float(month_data["total_net_cr"].sum())
        abs_monthly_net = abs(monthly_net)
        days_in_month = len(month_data)

        if abs_monthly_net > self.thresholds.monthly_net_cr:
            direction = "BUYING" if monthly_net > 0 else "SELLING"
            avg_daily = monthly_net / days_in_month if days_in_month > 0 else 0

            self._add_alert(
                alert_type="MONTHLY_CUMULATIVE",
                severity="high",
                message=f"Strong monthly {direction}: {abs_monthly_net:,.0f} crore net ({days_in_month} days, avg {avg_daily:,.0f}/day)",
                data={
                    "month": str(current_month),
                    "monthly_net": monthly_net,
                    "trading_days": days_in_month,
                    "avg_daily": avg_daily,
                },
            )

    def check_trend_reversal(self) -> None:
        """Detect reversal from bullish to bearish or vice versa."""
        df = self.analytics.load()
        if len(df) < 2:
            return

        latest_net = float(df.iloc[-1]["total_net_cr"])
        prev_net = float(df.iloc[-2]["total_net_cr"])

        latest_sign = "bullish" if latest_net > 0 else ("bearish" if latest_net < 0 else "neutral")
        prev_sign = "bullish" if prev_net > 0 else ("bearish" if prev_net < 0 else "neutral")

        if latest_sign != prev_sign and latest_sign != "neutral" and prev_sign != "neutral":
            self._add_alert(
                alert_type="TREND_REVERSAL",
                severity="medium",
                message=f"Trend reversal: {prev_sign.upper()} → {latest_sign.upper()}",
                data={
                    "previous_date": str(df.iloc[-2]["date"]),
                    "previous_net": prev_net,
                    "latest_date": str(df.iloc[-1]["date"]),
                    "latest_net": latest_net,
                },
            )

    def run_all_checks(self) -> list[dict[str, Any]]:
        """Execute all alert checks and return the list of triggered alerts."""
        self.alerts = []
        self.check_daily_extremes()
        self.check_weekly_trend()
        self.check_monthly_cumulative()
        self.check_trend_reversal()
        return self.alerts

    def save_alerts(self, output_path: str = "data/alerts.json") -> Path:
        """Save triggered alerts to a JSON file."""
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.alerts, indent=2), encoding="utf-8")
        logger.info("Saved %d alerts to %s", len(self.alerts), target)
        return target


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    generator = AlertGenerator()
    alerts = generator.run_all_checks()
    generator.save_alerts()
    print(f"Generated {len(alerts)} alert(s)")
    for alert in alerts:
        print(f"  - [{alert['severity'].upper()}] {alert['type']}: {alert['message']}")
