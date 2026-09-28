# NSE FII/DII Data Collector

A modular Python project for collecting daily FII (Foreign Institutional Investor) and DII (Domestic Institutional Investor) activity data from NSE India.

## Official NSE Source

- **NSE FII/DII Dashboard**: https://www.nseindia.com/market-data/fii-dii-activity
- **API Endpoint**: https://www.nseindia.com/api/fiidii

The data is collected directly from NSE's official JSON API. The client handles browser-like session setup, field normalization, validation, and local CSV storage.

## Project Structure

```
FII-data/
├── nse_client.py       # NSE session bootstrap and data normalization
├── storage.py          # CSV persistence and file I/O
├── validation.py       # Data quality checks and cleaning
├── historical.py       # Backfill multi-date datasets
├── scheduler.py        # Daily automation wrapper
├── main.py             # CLI entry point
└── data/
    └── fii_dii_daily.csv   # Output dataset (auto-created)
```

## Quick Start

### Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Fetch Current Data

```bash
python main.py
```

Output:
```
2026-09-28 17:15:23,456 - INFO - Starting NSE FII/DII data collection...
2026-09-28 17:15:24,789 - INFO - Fetched 1 rows from NSE
2026-09-28 17:15:24,890 - INFO - Validation passed. 1 rows retained
2026-09-28 17:15:24,950 - INFO - Data collection complete. Output: data/fii_dii_daily.csv

✓ Successfully saved 1 rows to data/fii_dii_daily.csv
```

### Backfill Historical Data

```python
from historical import HistoricalPipeline

pipeline = HistoricalPipeline()
data = pipeline.backfill(days=30)  # Last 30 days
print(f"Backfilled {len(data)} rows")
```

### Run Daily Collection (Scheduled)

```python
from scheduler import DailyScheduler

scheduler = DailyScheduler()
scheduler.run_once()  # Run one collection cycle
```

To schedule daily execution, use a cron job:

```bash
# Linux/macOS: Run daily at 9:30 AM IST (after NSE data publication)
30 3 * * * cd /path/to/FII-data && /path/to/.venv/bin/python main.py >> logs/daily.log 2>&1
```

Or with GitHub Actions (add `.github/workflows/daily.yml`):

```yaml
name: Daily FII/DII Collection
on:
  schedule:
    - cron: '30 3 * * 1-5'  # 9:00 AM IST, Mon-Fri

jobs:
  collect:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python main.py
      - uses: stefanzweifel/git-auto-commit-action@v4
        with:
          commit_message: "Auto: daily FII/DII collection"
```

## Output Schema

The collected CSV contains:

| Column | Type | Unit | Description |
| --- | --- | --- | --- |
| `date` | string | - | Date in DD-MMM-YYYY format (e.g., `28-Sep-2026`) |
| `fii_buy_cr` | float | ₹ crore | FII purchases |
| `fii_sell_cr` | float | ₹ crore | FII sales |
| `fii_net_cr` | float | ₹ crore | FII net activity (buy - sell) |
| `dii_buy_cr` | float | ₹ crore | DII purchases |
| `dii_sell_cr` | float | ₹ crore | DII sales |
| `dii_net_cr` | float | ₹ crore | DII net activity (buy - sell) |
| `total_net_cr` | float | ₹ crore | Total market net (FII + DII) |

### Sample Data

```csv
date,fii_buy_cr,fii_sell_cr,fii_net_cr,dii_buy_cr,dii_sell_cr,dii_net_cr,total_net_cr
28-Sep-2026,8500.50,8200.25,300.25,6100.00,6050.00,50.00,350.25
27-Sep-2026,8100.00,8050.00,50.00,5900.00,5950.00,-50.00,0.00
```

## Data Quality & Validation

The pipeline includes automatic validation:

- ✓ Checks for required columns
- ✓ Converts numeric fields and handles formatting
- ✓ Removes empty rows and null dates
- ✓ Deduplicates by date, keeping latest
- ✓ Logs warnings for failed validations
- ✓ Skips invalid dates during historical backfill

Failed rows are logged but do not stop execution. This keeps the pipeline resilient to NSE API changes.

## Development Workflow

Each component was developed incrementally and kept separate:

1. **NSE Client** (`nse_client.py`) — Session setup and normalization
2. **Storage** (`storage.py`) — CSV file I/O with deduplication
3. **Validation** (`validation.py`) — Data quality checks
4. **Historical** (`historical.py`) — Multi-date backfill
5. **Scheduler** (`scheduler.py`) — Daily automation wrapper
6. **Main** (`main.py`) — CLI orchestration

This modular design makes it easy to:
- Test each component independently
- Replace storage (CSV → SQLite → Parquet)
- Add new data sources
- Extend with analytics or dashboards

## Common Tasks

### View collected data

```bash
head -20 data/fii_dii_daily.csv
```

### Check validation logs

```bash
python -c "from validation import validate_dataframe; import pandas as pd; df = pd.read_csv('data/fii_dii_daily.csv'); print(validate_dataframe(df))"
```

### Backfill 90 days

```bash
python -c "from historical import HistoricalPipeline; HistoricalPipeline().backfill(days=90)"
```

### Reset data (start fresh)

```bash
rm data/fii_dii_daily.csv
```

## Troubleshooting

### "NSE returned a non-JSON response"

NSE may have changed the API format or blocked access. Possible causes:
- NSE website is down or under maintenance
- Firewall or ISP blocking (try a VPN)
- API endpoint changed (check NSE website)

**Fix**: Wait a few minutes and retry. NSE API is not stable.

### "Dataframe is None" or validation errors

The NSE API returned data but it doesn't match expected schema. This happens when:
- NSE changes response field names
- Server returns partial data
- Network connection is interrupted

**Fix**: Update `nse_client.py:normalize()` to map new field names.

### "No data rows available"

NSE returned an empty dataset. Possible reasons:
- No trading data available (weekend/holiday)
- NSE API endpoint is unavailable
- All rows failed validation

**Fix**: Check that today is a trading day and NSE is online.

## Future Enhancements

- [ ] SQLite backend for larger datasets
- [ ] Parquet export for analytics
- [ ] FII/DII sector-wise breakdown
- [ ] Trend analysis and alerts
- [ ] Correlation with Nifty index
- [ ] Web dashboard
- [ ] Push to GitHub/cloud storage

## Requirements

- Python 3.10+
- pandas
- requests

See `requirements.txt` for exact versions.

## License

MIT

## Notes

- This project is not affiliated with NSE India.
- NSE API is not officially documented and may change without notice.
- Data is provided as-is for informational purposes only.
- Respect NSE terms of service and do not abuse the API.
