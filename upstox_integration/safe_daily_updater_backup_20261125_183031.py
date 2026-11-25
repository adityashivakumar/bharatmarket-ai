
from pathlib import Path
from datetime import datetime, timedelta
import shutil
import logging
import uuid
import os

import pandas as pd

from upstox_integration.config import settings
from upstox_integration import daily_updater


# =====================================================
# CONFIGURATION
# =====================================================

CSV_COLUMNS = [
    "date", "adj_close", "close",
    "high", "low", "open", "volume"
]

PRICE_COLUMNS = ["open", "high", "low", "close"]

# Always begin safely.
DRY_RUN = True

# =====================================================
# LOGGING
# =====================================================

logger = logging.getLogger("bharatmarket_safe_updater")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.FileHandler(
        settings.LOG_DIR / "safe_daily_updater.log",
        encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    ))
    logger.addHandler(handler)


# =====================================================
# DATE UTILITIES
# =====================================================

def parse_dates(series):
    return daily_updater.parse_dates(series)


# =====================================================
# PREPARE ONE INSTRUMENT
# =====================================================

def prepare_instrument(symbol, instrument_key):

    raw_file = settings.RAW_DIR / f"{symbol}.csv"

    if not raw_file.exists():
        raise FileNotFoundError(raw_file)

    original = pd.read_csv(raw_file)

    if list(original.columns) != CSV_COLUMNS:
        raise ValueError(f"{symbol}: Unexpected CSV schema.")

    original_dates = parse_dates(original["date"])

    if original_dates.duplicated().any():
        raise ValueError(f"{symbol}: Duplicate dates in original CSV.")

    latest_date = original_dates.max().date()

    to_date = datetime.now().date() - timedelta(days=1)
    from_date = latest_date - timedelta(days=7)

    if from_date > to_date:
        raise ValueError(f"{symbol}: Invalid requested date range.")

    downloaded = daily_updater.fetch_candles(
        symbol,
        instrument_key,
        from_date,
        to_date
    )

    if downloaded.empty:
        return {
            "symbol": symbol,
            "status": "NO DATA",
            "original": original,
            "prepared": None,
            "new_rows": 0,
            "changed_rows": 0,
            "raw_file": raw_file
        }

    downloaded["date"] = pd.to_datetime(
        downloaded["date"]
    ).dt.normalize()

    downloaded = (
        downloaded
        .sort_values("date")
        .drop_duplicates("date", keep="last")
        .reset_index(drop=True)
    )

    daily_updater.validate_candles(downloaded, symbol)

    if downloaded["date"].min().date() < from_date:
        raise ValueError(f"{symbol}: Candle before requested range.")

    if downloaded["date"].max().date() > to_date:
        raise ValueError(f"{symbol}: Candle after requested range.")

    existing_dates = set(original_dates)
    downloaded_dates = set(downloaded["date"])

    new_dates = downloaded_dates - existing_dates
    overlap_dates = downloaded_dates & existing_dates

    old_index = original.copy()
    old_index["_parsed_date"] = original_dates
    old_index = old_index.set_index("_parsed_date")

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

    if changed_dates:
        raise ValueError(
            f"{symbol}: {len(changed_dates)} existing dates have "
            "different OHLC values. Manual review required."
        )

    new_data = downloaded[
        downloaded["date"].isin(new_dates)
    ].copy()

    if new_data.empty:
        return {
            "symbol": symbol,
            "status": "UP TO DATE",
            "original": original,
            "prepared": None,
            "new_rows": 0,
            "changed_rows": 0,
            "raw_file": raw_file
        }

    # Preserve all original records and their date strings.
    # Newly added dates use ISO YYYY-MM-DD format.
    new_data["date"] = pd.to_datetime(
        new_data["date"]
    ).dt.strftime("%Y-%m-%d")

    new_data = new_data[CSV_COLUMNS]

    combined = pd.concat(
        [original, new_data],
        ignore_index=True
    )

    combined["_sort_date"] = parse_dates(combined["date"])

    combined = (
        combined
        .sort_values("_sort_date")
        .drop(columns="_sort_date")
        .reset_index(drop=True)
    )

    combined_dates = parse_dates(combined["date"])

    if combined_dates.duplicated().any():
        raise ValueError(f"{symbol}: Duplicate dates after preparation.")

    if len(combined) != len(original) + len(new_data):
        raise ValueError(f"{symbol}: Unexpected prepared row count.")

    return {
        "symbol": symbol,
        "status": "NEW DATA READY",
        "original": original,
        "prepared": combined,
        "new_rows": len(new_data),
        "changed_rows": 0,
        "raw_file": raw_file
    }


# =====================================================
# VERIFY PREPARED CSV
# =====================================================

def verify_prepared_file(file_path, symbol, expected_rows):

    check = pd.read_csv(file_path)

    if list(check.columns) != CSV_COLUMNS:
        raise ValueError(f"{symbol}: Prepared schema mismatch.")

    dates = parse_dates(check["date"])

    if dates.duplicated().any():
        raise ValueError(f"{symbol}: Prepared file has duplicate dates.")

    if len(check) != expected_rows:
        raise ValueError(f"{symbol}: Prepared row count mismatch.")

    check[PRICE_COLUMNS] = check[PRICE_COLUMNS].apply(
        pd.to_numeric,
        errors="raise"
    )

    daily_updater.validate_candles(
        check.assign(date=dates),
        symbol
    )

    return True


# =====================================================
# TRANSACTION CONTROLLER
# =====================================================

def run_safe_update(dry_run=True):

    transaction_id = (
        datetime.now().strftime("%Y%m%d_%H%M%S")
        + "_"
        + uuid.uuid4().hex[:6]
    )

    transaction_dir = (
        settings.UPSTOX_DIR
        / "transactions"
        / transaction_id
    )

    staged_dir = transaction_dir / "staged"
    backup_dir = transaction_dir / "backups"

    staged_dir.mkdir(parents=True, exist_ok=True)

    mapping = daily_updater.load_mapping()

    prepared_items = []
    results = []
    errors = []

    print("TRANSACTION:", transaction_id)
    print("DRY RUN:", dry_run)

    # -------------------------------------------------
    # PHASE 1: FETCH AND PREPARE ALL TEN INSTRUMENTS
    # -------------------------------------------------

    for _, item in mapping.iterrows():

        symbol = item["BharatMarket_Symbol"]
        key = item["Upstox_Instrument_Key"]

        print(f"\nPreflight: {symbol}")

        try:

            result = prepare_instrument(symbol, key)
            prepared_items.append(result)

            results.append({
                "Instrument": symbol,
                "Status": result["status"],
                "New_Rows": result["new_rows"],
                "Changed_Rows": result["changed_rows"]
            })

            if result["prepared"] is not None:

                staged_file = staged_dir / f"{symbol}.csv"

                result["prepared"].to_csv(
                    staged_file,
                    index=False
                )

                verify_prepared_file(
                    staged_file,
                    symbol,
                    len(result["prepared"])
                )

                result["staged_file"] = staged_file

        except Exception as error:

            errors.append({
                "Instrument": symbol,
                "Error": str(error)
            })

            logger.exception(
                "%s preflight failed.",
                symbol
            )

    report = pd.DataFrame(results)

    print("\n========== PREFLIGHT SUMMARY ==========")

    if not report.empty:
        print(report.to_string(index=False))

    print("\nPrepared instruments:", len(prepared_items))
    print("Preflight errors:", len(errors))

    # No files are modified if even one instrument fails.
    if errors or len(prepared_items) != len(settings.INSTRUMENTS):

        print("\nTRANSACTION ABORTED.")
        print("No original CSV files were modified.")

        return report, errors, transaction_id

    updates = [
        item for item in prepared_items
        if item["prepared"] is not None
    ]

    total_new_rows = sum(
        item["new_rows"] for item in updates
    )

    # -------------------------------------------------
    # PHASE 2: DRY RUN
    # -------------------------------------------------

    if dry_run:

        print("\nDRY RUN SUCCESSFUL.")
        print("New rows detected:", total_new_rows)
        print("Original CSV files modified: NO")
        print("Backups created: NO")

        return report, errors, transaction_id

    # -------------------------------------------------
    # PHASE 3: NO-OP IF THERE IS NOTHING TO UPDATE
    # -------------------------------------------------

    if not updates:

        print("\nALL INSTRUMENTS ALREADY UP TO DATE.")
        print("No backups or writes required.")

        return report, errors, transaction_id

    # -------------------------------------------------
    # PHASE 4: BACKUP ALL AFFECTED FILES
    # -------------------------------------------------

    backup_dir.mkdir(parents=True, exist_ok=True)

    backups = {}

    try:

        for item in updates:

            symbol = item["symbol"]
            raw_file = item["raw_file"]

            backup_file = backup_dir / f"{symbol}.csv"

            shutil.copy2(raw_file, backup_file)

            # Verify backup exists and has the same bytes.
            if (
                not backup_file.exists()
                or backup_file.read_bytes() != raw_file.read_bytes()
            ):
                raise RuntimeError(
                    f"{symbol}: Backup verification failed."
                )

            backups[symbol] = backup_file

    except Exception:

        print("\nBACKUP PHASE FAILED.")
        print("No original CSV files have been replaced.")

        raise

    # -------------------------------------------------
    # PHASE 5: COMMIT
    # -------------------------------------------------

    committed = []

    try:

        for item in updates:

            symbol = item["symbol"]
            raw_file = item["raw_file"]
            staged_file = item["staged_file"]

            # Recheck staged file before replacement.
            verify_prepared_file(
                staged_file,
                symbol,
                len(item["prepared"])
            )

            os.replace(staged_file, raw_file)

            committed.append(symbol)

            logger.info(
                "%s committed with %s new rows.",
                symbol,
                item["new_rows"]
            )

    except Exception as commit_error:

        logger.exception("Transaction commit failed. Rolling back.")

        rollback_errors = []

        for symbol in reversed(committed):

            try:

                shutil.copy2(
                    backups[symbol],
                    settings.RAW_DIR / f"{symbol}.csv"
                )

            except Exception as rollback_error:

                rollback_errors.append({
                    "Instrument": symbol,
                    "Error": str(rollback_error)
                })

        if rollback_errors:

            print("\nCRITICAL: ROLLBACK NEEDS MANUAL REVIEW.")
            print(pd.DataFrame(rollback_errors).to_string(index=False))

        else:
            print("\nROLLBACK COMPLETED.")

        raise RuntimeError(
            "Transaction failed: " + str(commit_error)
        )

    # -------------------------------------------------
    # PHASE 6: FINAL REPORT
    # -------------------------------------------------

    print("\nTRANSACTION COMMITTED SUCCESSFULLY.")
    print("Updated instruments:", len(committed))
    print("New rows added:", total_new_rows)
    print("Backups:", backup_dir)

    logger.info(
        "Transaction %s committed. New rows: %s",
        transaction_id,
        total_new_rows
    )

    return report, errors, transaction_id
'''

UPDATER_FILE = (
    PROJECT_DIR / "upstox_integration" / "safe_daily_updater.py"
)

UPDATER_FILE.write_text(
    source_code.strip() + "\n",
    encoding="utf-8"
)

print("SAFE UPDATER CREATED")
print("Location:", UPDATER_FILE)
print("Size:", UPDATER_FILE.stat().st_size, "bytes")
