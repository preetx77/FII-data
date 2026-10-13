from pathlib import Path

import pandas as pd

from notifier import AlertNotifier
from report import generate_summary_image
from storage import DataStore
from validation import assert_no_duplicates, validate_dataframe


def test_validate_dataframe_accepts_expected_schema():
    df = pd.DataFrame(
        [{
            "date": "2024-01-01",
            "fii_buy_cr": 100.0,
            "fii_sell_cr": 50.0,
            "fii_net_cr": 50.0,
            "dii_buy_cr": 30.0,
            "dii_sell_cr": 20.0,
            "dii_net_cr": 10.0,
            "total_net_cr": 60.0,
        }]
    )

    result = validate_dataframe(df)

    assert list(result.columns) == [
        "date",
        "fii_buy_cr",
        "fii_sell_cr",
        "fii_net_cr",
        "dii_buy_cr",
        "dii_sell_cr",
        "dii_net_cr",
        "total_net_cr",
    ]
    assert len(result) == 1


def test_assert_no_duplicates_keeps_latest_record():
    df = pd.DataFrame(
        [
            {
                "date": "2024-01-01",
                "fii_buy_cr": 100.0,
                "fii_sell_cr": 50.0,
                "fii_net_cr": 50.0,
                "dii_buy_cr": 30.0,
                "dii_sell_cr": 20.0,
                "dii_net_cr": 10.0,
                "total_net_cr": 60.0,
            },
            {
                "date": "2024-01-01",
                "fii_buy_cr": 200.0,
                "fii_sell_cr": 100.0,
                "fii_net_cr": 100.0,
                "dii_buy_cr": 80.0,
                "dii_sell_cr": 60.0,
                "dii_net_cr": 20.0,
                "total_net_cr": 120.0,
            },
        ]
    )

    result = assert_no_duplicates(df)

    assert len(result) == 1
    assert result.iloc[0]["total_net_cr"] == 120.0


def test_data_store_appends_unique_dates(tmp_path):
    store = DataStore(base_dir=str(tmp_path / "data"))

    first = pd.DataFrame([
        {
            "date": "2024-01-01",
            "fii_buy_cr": 100.0,
            "fii_sell_cr": 50.0,
            "fii_net_cr": 50.0,
            "dii_buy_cr": 30.0,
            "dii_sell_cr": 20.0,
            "dii_net_cr": 10.0,
            "total_net_cr": 60.0,
        }
    ])
    second = pd.DataFrame([
        {
            "date": "2024-01-02",
            "fii_buy_cr": 90.0,
            "fii_sell_cr": 40.0,
            "fii_net_cr": 50.0,
            "dii_buy_cr": 20.0,
            "dii_sell_cr": 15.0,
            "dii_net_cr": 5.0,
            "total_net_cr": 55.0,
        }
    ])

    store.append_csv(first)
    store.append_csv(second)

    saved = store.read_csv()
    assert len(saved) == 2
    assert list(saved["date"]) == ["2024-01-01", "2024-01-02"]


def test_generate_summary_image_creates_png(tmp_path):
    db_path = tmp_path / "fii_dii_daily.db"

    store = DataStore(base_dir=str(tmp_path), db_filename="fii_dii_daily.db")
    history = pd.DataFrame(
        [
            {
                "date": "2024-01-01",
                "fii_buy_cr": 100.0,
                "fii_sell_cr": 50.0,
                "fii_net_cr": 50.0,
                "dii_buy_cr": 30.0,
                "dii_sell_cr": 20.0,
                "dii_net_cr": 10.0,
                "total_net_cr": 60.0,
            },
            {
                "date": "2024-01-02",
                "fii_buy_cr": 200.0,
                "fii_sell_cr": 100.0,
                "fii_net_cr": 100.0,
                "dii_buy_cr": 50.0,
                "dii_sell_cr": 30.0,
                "dii_net_cr": 20.0,
                "total_net_cr": 120.0,
            },
        ]
    )
    store.save_sqlite(history)

    output = tmp_path / "summary.png"
    image_path, caption = generate_summary_image(db_path=str(db_path), output_path=str(output))

    assert Path(image_path).exists()
    assert output.exists()
    assert "Latest date:" in caption


def test_alert_notifier_without_config_returns_false():
    notifier = AlertNotifier()

    assert notifier.send_telegram_photo("missing.png", "hello") is False
