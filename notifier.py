"""Notification helpers for FII/DII alerts.

This module sends generated alerts through a supported channel and provides
richer delivery options (structured webhook JSON, HTML email with attachments,
and Telegram images).
"""

from __future__ import annotations

import mimetypes
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

    # --- Telegram ---
    def send_telegram(self, text: str) -> bool:
        """Send a message to Telegram using the configured bot."""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            return False

        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        payload = {"chat_id": self.telegram_chat_id, "text": text, "parse_mode": "HTML"}
        response = requests.post(url, data=payload, timeout=15)
        response.raise_for_status()
        return True

    def send_telegram_photo(self, photo_path: str, caption: str) -> bool:
        """Send a generated chart image to Telegram with a short caption."""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            return False

        if not os.path.exists(photo_path):
            return False

        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendPhoto"
        with open(photo_path, "rb") as image_file:
            payload = {"chat_id": self.telegram_chat_id, "caption": caption}
            response = requests.post(
                url,
                data=payload,
                files={"photo": image_file},
                timeout=30,
            )
        response.raise_for_status()
        return True

    # --- Webhook ---
    def send_webhook(self, text: str, alerts: list[dict[str, Any]] | None = None) -> bool:
        """Send alert payload to a generic webhook endpoint (legacy plain-text)."""
        if not self.webhook_url:
            return False

        payload = {"text": text, "alerts": alerts or []}
        response = requests.post(self.webhook_url, json=payload, timeout=15)
        response.raise_for_status()
        return True

    def send_webhook_json(self, summary: str | None, alerts: list[dict[str, Any]] | None = None) -> bool:
        """Send a structured JSON payload to the configured webhook with a summary and alerts."""
        if not self.webhook_url:
            return False

        payload = {
            "summary": summary or "",
            "alerts": alerts or [],
        }
        response = requests.post(self.webhook_url, json=payload, timeout=15)
        response.raise_for_status()
        return True

    # --- Email ---
    def send_email(self, text: str, subject: str = "FII/DII alert") -> bool:
        """Send a plain text email if SMTP configuration is present."""
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

    def send_email_with_attachments(
        self,
        text: str,
        subject: str = "FII/DII alert",
        html: str | None = None,
        attachments: list[str] | None = None,
    ) -> bool:
        """Send an email with optional HTML body and file attachments.

        Attachments are guessed for MIME type using the filename extension.
        """
        if not self.smtp_host or not self.smtp_to:
            return False

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.smtp_from or self.smtp_user or "noreply@example.com"
        msg["To"] = self.smtp_to
        msg.set_content(text)
        if html:
            msg.add_alternative(html, subtype="html")

        attachments = attachments or []
        for path in attachments:
            if not os.path.exists(path):
                continue
            ctype, encoding = mimetypes.guess_type(path)
            if ctype is None:
                ctype = "application/octet-stream"
            maintype, subtype = ctype.split("/", 1)
            with open(path, "rb") as f:
                msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=os.path.basename(path))

        with smtplib.SMTP(self.smtp_host, self.smtp_port or 587, timeout=30) as server:
            if self.smtp_user and self.smtp_password:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)

        return True

    # --- Combined notifier ---
    def notify(self, alerts: list[dict[str, Any]]) -> dict[str, bool]:
        """Send all alerts to whichever channel is configured (backwards-compatible)."""
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

    def notify_enhanced(self, alerts: list[dict[str, Any]], summary: str | None = None, image_path: str | None = None) -> dict[str, bool]:
        """Send alerts with an optional human summary and image attachment.

        Behavior:
        - If image_path is provided and Telegram is configured, send photo to Telegram
          otherwise send plain text message.
        - Post structured JSON (summary + alerts) to webhook if configured.
        - Send HTML/plain email with image attached if SMTP configured.
        """
        if not alerts and not summary and not image_path:
            return {"telegram": False, "webhook": False, "email": False}

        messages = [self.format_alert(alert) for alert in alerts] if alerts else []
        text_body = (summary + "\n\n" + "\n".join(messages)) if summary else "\n".join(messages)

        results = {
            "telegram": False,
            "webhook": False,
            "email": False,
        }

        # Telegram: prefer photo if available
        try:
            if image_path and self.telegram_bot_token and self.telegram_chat_id:
                results["telegram"] = self.send_telegram_photo(image_path, summary or "FII/DII summary")
            elif text_body:
                results["telegram"] = self.send_telegram(text_body)
        except Exception:
            results["telegram"] = False

        # Webhook: structured JSON
        try:
            results["webhook"] = self.send_webhook_json(summary, alerts)
        except Exception:
            results["webhook"] = False

        # Email: attach image when available and send HTML simple body
        try:
            html = None
            if summary:
                html = f"<pre>{summary}</pre>"
            attachments = [image_path] if image_path else []
            results["email"] = self.send_email_with_attachments(text_body or "FII/DII update", subject="FII/DII summary", html=html, attachments=attachments)
        except Exception:
            results["email"] = False

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
