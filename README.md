# NSE FII/DII Data Collection & Analytics Pipeline

A complete end-to-end system for collecting, storing, analyzing, and monitoring Foreign Institutional Investor (FII) and Domestic Institutional Investor (DII) flows from the National Stock Exchange (NSE).

## Features

- Data collection from NSE FII/DII API
- SQLite-backed persistence with CSV export
- Data validation and deduplication
- Trend analytics and monthly summaries
- Alert generation for significant market events
- Multi-channel notifications (Telegram, webhook, email)
- Streamlit dashboard for live monitoring
- Daily automation through GitHub Actions

## Project Structure

```text
FII-data/
├── main.py            # entry point for collection
├── nse_client.py      # NSE API client and normalization
├── storage.py         # SQLite + CSV persistence
├── validation.py      # validation and dedupe logic
├── analytics.py       # trend and summary metrics
├── alerts.py          # market alerts generator
├── notifier.py        # Telegram/webhook/email notifier
├── report.py          # plain-text market summary output
├── dashboard.py       # Streamlit dashboard
├── historical.py      # backfill support
├── scheduler.py       # automation helper
├── requirements.txt   # Python dependencies
├── README.md          # project documentation
├── data/
│   ├── fii_dii_daily.db
│   ├── fii_dii_daily.csv
│   ├── alerts.json
│   └── market_summary.txt
└── .github/workflows/
    └── daily.yml      # scheduled run
```

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the collector

```bash
python main.py
```

This fetches the latest FII/DII flow data and saves it to the SQLite database and CSV export in the `data/` folder.

### 3. Launch the dashboard

```bash
streamlit run dashboard.py
```

Open the local URL shown in the terminal.

### 4. Generate a summary report

```bash
python report.py
```

## Module overview

### `main.py`
Runs the current-day collection workflow: fetch -> validate -> store.

### `nse_client.py`
Fetches NSE data and normalizes it into a pandas dataframe.

### `storage.py`
Persists data into SQLite and CSV. It also keeps a single latest record per `date` to avoid duplicate daily entries.

### `validation.py`
Ensures the dataset contains valid columns, numeric values, and no duplicate dates.

### `analytics.py`
Computes a few useful market metrics:
- 7-day rolling average
- bullish vs bearish days
- latest activity summary
- monthly totals

### `alerts.py`
Checks for notable movements such as:
- extreme daily moves
- weekly bullish/bearish accumulation
- monthly cumulative FII/DII imbalance
- trend reversals

### `notifier.py`
Sends generated alerts through configured channels:
- Telegram bot
- webhook payload
- SMTP email

### `report.py`
Builds a readable summary text report saved to `data/market_summary.txt`.

### `dashboard.py`
Interactive Streamlit dashboard to view:
- latest net values
- total flow trend
- monthly aggregates
- recent activity
- alert log
- date-filtered summaries

## Data schema

The dataset stores the following columns:

- `date`
- `fii_buy_cr`
- `fii_sell_cr`
- `fii_net_cr`
- `dii_buy_cr`
- `dii_sell_cr`
- `dii_net_cr`
- `total_net_cr`

These are values in crore units.

## Alerts and notifications

Set these environment variables to enable notifications:

```bash
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
export ALERT_WEBHOOK_URL="https://..."
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="user@gmail.com"
export SMTP_PASSWORD="app_password"
export SMTP_TO="recipient@example.com"
```

Then run:

```python
from alerts import AlertGenerator
from notifier import AlertNotifier

gen = AlertGenerator()
alerts = gen.run_all_checks()
notifier = AlertNotifier()
notifier.notify(alerts)
```

## Daily automation

This repo includes a GitHub Actions workflow to run the collector automatically during weekdays.

Workflow file:
- `.github/workflows/daily.yml`

It runs the project on a schedule and automatically commits updated market data if it changed.

## Local development notes

- The project expects the `data/` folder to exist.
- If the dataset is missing, run `python main.py` first.
- Streamlit reads `data/fii_dii_daily.db` directly.

## Future enhancements

Planned improvements:
- Nifty correlation analysis
- sector-wise breakdown
- predictive modeling
- richer charts and dashboard tabs
- alert delivery into Slack/Teams/Discord

## License

MIT

## Disclaimer

This project is for educational and informational use only. It pulls public NSE data and should not be considered financial advice.
