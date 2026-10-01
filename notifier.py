"""Notification helpers for FII/DII alerts.

This module sends generated alerts through a supported channel:

- Telegram bot message
- generic webhook POST
- SMTP email (optional)

It is intentionally small and configurable through environment variables so it can
be plugged into scheduled jobs without changing the data pipeline.
"""

from __future__ import annotations

import json
import os
import smtplib
from email.message import EmailMessage
from typing import Any

import requests


class AlertNotifier:
    """Send alert payloads to Telegram, webhooks, or email."""

    def __init__(
        self,
        telegram_bot_token: str | None = None,
        telegram_chat_id: str | None = None,
        webhook_url: str | None = None,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        smtp_to: str | None = None,
        smtp_from: str | None = None,
    ) -> None:
        self.telegram_bot_token = telegram_bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.webhook_url = webhook_url or os.getenv("ALERT_WEBHOOK_URL")
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.smtp_to = smtp_to or os.getenv("SMTP_TO")
        self.smtp_from = smtp_from or os.getenv("SMTP_FROM")

    def format_alert(self, alert: dict[str, Any]) -> str:
        """Render a single alert as a readable message."""
        severity = alert.get("severity", "info").upper()
        alert_type = alert.get("type", "ALERT")
        message = alert.get("message", "No message")
        data = alert.get("data", {})

        if data:
            extras = ", ".join(f"{key}={value}" for key, value in data.items())
            return f"[{severity}] {alert_type}: {message} | {extras}"
        return f"[{severity}] {alert_type}: {message}"

    def send_telegram(self, text: str) -> bool:
        """Send a message to Telegram using the configured bot."""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            return False

        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        payload = {"chat_id": self.telegram_chat_id, "text": text, "parse_mode": "HTML"}
        response = requests.post(url, data=payload, timeout=15)
        response.raise_for_status()
        return True

    def send_webhook(self, text: str, alerts: list[dict[str, Any]] | None = None) -> bool:
        """Send alert payload to a generic webhook endpoint."""
        if not self.webhook_url:
            return False

        payload = {"text": text, "alerts": alerts or []}
        response = requests.post(self.webhook_url, json=payload, timeout=15)
        response.raise_for_status()
        return True

    def send_email(self, text: str, subject: str = "FII/DII alert") -> bool:
        """Send an email if SMTP configuration is present."""
        if not self.smtp_host or not self.smtp_to:
            return False

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.smtp_from or self.smtp_user or "noreply@example.com"
        msg["To"] = self.smtp_to
        msg.set_content(text)

        with smtplib.SMTP(self.smtp_host, self.smtp_port or 587, timeout=15) as server:
            if self.smtp_user and self.smtp_password:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)

        return True

    def notify(self, alerts: list[dict[str, Any]]) -> dict[str, bool]:
        """Send all alerts to whichever channel is configured."""
        if not alerts:
            return {"telegram": False, "webhook": False, "email": False}

        messages = [self.format_alert(alert) for alert in alerts]
        text = "\n".join(messages)

        results = {
            "telegram": self.send_telegram(text),
            "webhook": self.send_webhook(text, alerts),
            "email": self.send_email(text, subject="FII/DII alert"),
        }
        return results

    def send_json_file(self, alerts: list[dict[str, Any]], output_path: str = "data/alerts.json") -> str:
        """Persist alert payloads to JSON for later delivery or auditing."""
        import json
        from pathlib import Path

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(alerts, indent=2), encoding="utf-8")
        return str(path)


if __name__ == "__main__":
    notifier = AlertNotifier()
    sample = [
        {
            "type": "WEEKLY_BULLISH_TREND",
            "severity": "medium",
            "message": "Strong weekly buying bias detected",
            "data": {"weekly_net": 4200, "bullish_days": 5},
        }
    ]
    print(notifier.notify(sample))
