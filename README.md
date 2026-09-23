# NSE FII/DII Data

A small Python client for collecting the daily FII (Foreign Institutional Investor) and DII (Domestic Institutional Investor) activity published by NSE India.

## Official source

- NSE FII/DII activity page: <https://www.nseindia.com/market-data/fii-dii-activity>
- NSE endpoint used by that page: <https://www.nseindia.com/api/fiidii>

The client first opens an NSE session to obtain cookies and then requests the API. NSE can change or restrict this endpoint, so the code reports a clear error instead of silently writing placeholder data.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python main.py
```

A successful run writes the normalized result to `data/fii_dii_daily.csv`.

## Output columns

| Column | Description |
| --- | --- |
| `date` | Date supplied by NSE |
| `fii_buy_cr` | FII purchases in ₹ crore |
| `fii_sell_cr` | FII sales in ₹ crore |
| `fii_net_cr` | FII net activity in ₹ crore |
| `dii_buy_cr` | DII purchases in ₹ crore |
| `dii_sell_cr` | DII sales in ₹ crore |
| `dii_net_cr` | DII net activity in ₹ crore |
| `total_net_cr` | FII net plus DII net in ₹ crore |

## Development steps

1. Fetch and normalize the current NSE response.
2. Add durable daily storage and duplicate-date handling.
3. Add historical ingestion with retries and progress logging.
4. Add automated tests and scheduled collection.

The repository intentionally completes these steps incrementally so changes can be verified independently.
