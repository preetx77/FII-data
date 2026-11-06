# NSE FII/DII Data Collection & Analytics Pipeline

A Python pipeline for collecting, storing, analyzing, and monitoring FII/DII flows from NSE, with a Streamlit dashboard, alert generation, and optional Telegram, webhook, and email notifications.

## Run with Docker Compose

Requirements: Docker with the Compose plugin.

Start the dashboard:

```bash
docker compose up --build dashboard
```

Open <http://localhost:8501>. The `fii_data` named volume preserves the data directory between container runs.

Run the collector on demand (it fetches NSE data, writes the data files, and exits):

```bash
docker compose --profile collector run --rm collector
```

To enable notifications, export the relevant environment variables before running the collector. You can also put them in a local `.env` file (do not commit it):

```bash
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
export ALERT_WEBHOOK_URL="https://..."
export SMTP_HOST="smtp.example.com"
export SMTP_PORT="587"
export SMTP_USER="..."
export SMTP_PASSWORD="..."
export SMTP_TO="..."
export SMTP_FROM="..."
```

The collector and dashboard share the same persistent volume. Run the collector at least once to populate the store before opening the dashboard. Stop the dashboard with `Ctrl+C`.

## Run locally

```bash
python -m pip install -r requirements.txt
python main.py
streamlit run dashboard.py
```
