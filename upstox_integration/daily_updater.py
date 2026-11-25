import shutil
import logging
from datetime import datetime, timedelta
from urllib.parse import quote

import pandas as pd
import requests

from upstox_integration.config import settings


PRICE_COLUMNS = ["open", "high", "low", "close"]

CSV_COLUMNS = [
    "date", "adj_close", "close",
    "high", "low", "open", "volume"
]


# --------------------------------------------------
# LOGGING
# --------------------------------------------------

settings.LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("bharatmarket_daily_updater")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.FileHandler(
        settings.LOG_DIR / "daily_updater.log",
        encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    ))
    logger.addHandler(handler)


# --------------------------------------------------
# DATE PARSING
# --------------------------------------------------

def parse_dates(series):

    values = series.astype(str).str.strip()

    parsed = pd.to_datetime(
        values,
        format="%Y-%m-%d",
        errors="coerce"
    )

    failed = parsed.isna()

    if failed.any():
        parsed.loc[failed] = pd.to_datetime(
            values.loc[failed],
            format="%d-%m-%Y",
            errors="coerce"
        )

    if parsed.isna().any():
        raise ValueError("Unparseable dates found.")

    return parsed.dt.normalize()


# --------------------------------------------------
# LOAD INSTRUMENT MAPPING
# --------------------------------------------------

def load_mapping():

    mapping = pd.read_csv(settings.MAPPING_FILE)

    required = [
        "BharatMarket_Symbol",
        "Upstox_Instrument_Key"
    ]

    if not all(col in mapping.columns for col in required):
        raise ValueError("Invalid instrument mapping columns.")

    mapping = mapping[required].copy()

    if mapping.isna().any().any():
        raise ValueError("Missing instrument mapping values.")

    if mapping["BharatMarket_Symbol"].duplicated().any():
        raise ValueError("Duplicate instrument mappings.")

    if set(mapping["BharatMarket_Symbol"]) != set(settings.INSTRUMENTS):
        raise ValueError("Instrument mapping is incomplete.")

    return mapping


# --------------------------------------------------
# FETCH DAILY CANDLES
# --------------------------------------------------

def fetch_candles(symbol, instrument_key, from_date, to_date):

    encoded_key = quote(instrument_key, safe="")

    url = (
        f"{settings.HISTORICAL_CANDLE_URL}/"
        f"{encoded_key}/days/1/{to_date}/{from_date}"
    )

    response = requests.get(
        url,
        headers=settings.API_HEADERS,
        timeout=30
    )

    response.raise_for_status()

    payload = response.json()

    if payload.get("status") != "success":
        raise RuntimeError(
            f"{symbol}: Upstox returned an unsuccessful response."
        )

    candles = payload.get("data", {}).get("candles", [])

    records = []

    for candle in candles:

        timestamp = pd.to_datetime(candle[0], utc=True)

        local_date = (
            timestamp
            .tz_convert("Asia/Kolkata")
            .date()
        )

        records.append({
            "date": pd.Timestamp(local_date),
            "adj_close": float("nan"),
            "close": float(candle[4]),
            "high": float(candle[2]),
            "low": float(candle[3]),
            "open": float(candle[1]),
            "volume": (
                int(candle[5])
                if candle[5] is not None
                else float("nan")
            )
        })

    return pd.DataFrame(records, columns=CSV_COLUMNS)


# --------------------------------------------------
# VALIDATE DOWNLOADED DATA
# --------------------------------------------------

def validate_candles(df, symbol):

    if df.empty:
        return

    if df["date"].duplicated().any():
        raise ValueError(f"{symbol}: Duplicate candle dates.")

    if df[PRICE_COLUMNS].isna().any().any():
        raise ValueError(f"{symbol}: Missing OHLC values.")

    if (df[PRICE_COLUMNS] <= 0).any().any():
        raise ValueError(f"{symbol}: Non-positive OHLC prices.")

    valid = (
        (df["high"] >= df["low"]) &
        (df["high"] >= df["open"]) &
        (df["high"] >= df["close"]) &
        (df["low"] <= df["open"]) &
        (df["low"] <= df["close"])
    )

    if not valid.all():
        raise ValueError(f"{symbol}: OHLC validation failed.")


# --------------------------------------------------
# UPDATE ONE INSTRUMENT
# --------------------------------------------------

def update_instrument(symbol, instrument_key, dry_run=True):

    raw_file = settings.RAW_DIR / f"{symbol}.csv"

    if not raw_file.exists():
        raise FileNotFoundError(raw_file)

    original = pd.read_csv(raw_file)

    if list(original.columns) != CSV_COLUMNS:
        raise ValueError(
            f"{symbol}: Unexpected CSV schema or column order."
        )

    original["date"] = parse_dates(original["date"])

    if original["date"].duplicated().any():
        raise ValueError(
            f"{symbol}: Original CSV contains duplicate dates."
        )

    latest_date = original["date"].max().date()

    # Overlap recent dates to detect revised candles.
    to_date = datetime.now().date() - timedelta(days=1)
    from_date = latest_date - timedelta(days=7)

    if from_date > to_date:
        raise ValueError(
            f"{symbol}: Invalid date range {from_date} to {to_date}"
        )

    downloaded = fetch_candles(
        symbol,
        instrument_key,
        from_date,
        to_date
    )

    if downloaded.empty:
        return {
            "Instrument": symbol,
            "Status": "NO DATA",
            "New_Rows": 0,
            "Changed_Rows": 0
        }

    downloaded["date"] = pd.to_datetime(downloaded["date"]).dt.normalize()

    downloaded = (
        downloaded
        .sort_values("date")
        .drop_duplicates("date", keep="last")
        .reset_index(drop=True)
    )

    validate_candles(downloaded, symbol)

    if downloaded["date"].min().date() < from_date:
        raise ValueError(f"{symbol}: API returned dates before requested range.")

    if downloaded["date"].max().date() > to_date:
        raise ValueError(f"{symbol}: API returned future dates.")

    existing_dates = set(original["date"])
    downloaded_dates = set(downloaded["date"])

    new_dates = downloaded_dates - existing_dates
    overlap_dates = downloaded_dates & existing_dates

    old_index = original.set_index("date")
    new_index = downloaded.set_index("date")

    changed_dates = []

    for date in overlap_dates:

        old = old_index.loc[date]
        new = new_index.loc[date]

        if any(
            round(float(old[col]), 2) != round(float(new[col]), 2)
            for col in PRICE_COLUMNS
        ):
            changed_dates.append(date)

    new_data = downloaded[
        downloaded["date"].isin(new_dates)
    ].copy()

    if changed_dates:

        logger.warning(
            "%s: %s historical dates require review.",
            symbol,
            len(changed_dates)
        )

        return {
            "Instrument": symbol,
            "Status": "REVIEW REQUIRED",
            "New_Rows": len(new_data),
            "Changed_Rows": len(changed_dates)
        }

    if dry_run:

        return {
            "Instrument": symbol,
            "Status": "DRY RUN",
            "New_Rows": len(new_data),
            "Changed_Rows": 0,
            "Latest_Existing_Date": latest_date,
            "Latest_API_Date": downloaded["date"].max().date()
        }

    if new_data.empty:

        return {
            "Instrument": symbol,
            "Status": "UP TO DATE",
            "New_Rows": 0,
            "Changed_Rows": 0
        }

    # Create backup before modifying the original.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_dir = settings.BACKUP_DIR / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_file = backup_dir / f"{symbol}.csv"

    shutil.copy2(raw_file, backup_file)

    # Append only genuinely new dates.
    updated = pd.concat(
        [original, new_data],
        ignore_index=True
    )

    updated = (
        updated
        .sort_values("date")
        .drop_duplicates("date", keep="first")
        .reset_index(drop=True)
    )

    updated = updated[CSV_COLUMNS]

    updated.to_csv(raw_file, index=False)

    logger.info(
        "%s: Added %s new trading dates.",
        symbol,
        len(new_data)
    )

    return {
        "Instrument": symbol,
        "Status": "UPDATED",
        "New_Rows": len(new_data),
        "Changed_Rows": 0,
        "Backup": str(backup_file)
    }


# --------------------------------------------------
# RUN ALL INSTRUMENTS
# --------------------------------------------------

def run_daily_update(dry_run=True):

    mapping = load_mapping()

    results = []
    errors = []

    for _, item in mapping.iterrows():

        symbol = item["BharatMarket_Symbol"]
        instrument_key = item["Upstox_Instrument_Key"]

        print(f"\nProcessing {symbol}...")

        try:

            result = update_instrument(
                symbol,
                instrument_key,
                dry_run=dry_run
            )

            results.append(result)
            print(result)

        except Exception as error:

            errors.append({
                "Instrument": symbol,
                "Error": str(error)
            })

            logger.exception("%s update failed.", symbol)

            print("FAILED:", error)

    report = pd.DataFrame(results)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    report_file = (
        settings.LOG_DIR /
        f"update_report_{timestamp}.csv"
    )

    report.to_csv(report_file, index=False)

    print("\n========== UPDATE SUMMARY ==========")
    print("Processed:", len(results))
    print("Failed:", len(errors))
    print("Dry run:", dry_run)

    if not report.empty:
        print(report.to_string(index=False))

    if errors:
        print("\nERRORS:")
        print(pd.DataFrame(errors).to_string(index=False))

    print("\nReport saved:", report_file)

    return report, errors
