
"""
BharatMarket AI
Intraday Candle and Indicator Pipeline

Processes normalized Upstox V3 market feed observations.

Supported timeframes:
    1 minute
    5 minutes
    15 minutes

Important:
    Initial snapshots are excluded from candle construction.
    Only genuine feed updates contribute price observations.
    Index volume is unavailable and remains NaN.
    Equity volume is observed cumulative-volume increments,
    not guaranteed complete exchange candle volume.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from upstox_integration.live.indicator_engine import (
    calculate_indicators
)

IST = "Asia/Kolkata"

TIMEFRAMES = {
    "1min": "1m",
    "5min": "5m",
    "15min": "15m",
}

REQUIRED_COLUMNS = [
    "symbol",
    "instrument_key",
    "ltp",
    "exchange_timestamp_ms",
    "message_kind",
    "cumulative_volume",
]


# ==========================================================
# 1. LOAD AND VALIDATE NORMALIZED TICKS
# ==========================================================

def load_ticks(file_path):
    """
    Load normalized Upstox observations.

    Converts exchange timestamps into Indian Standard Time.
    Removes invalid and exact duplicate observations.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Tick file not found: {file_path}"
        )

    df = pd.read_csv(file_path)

    missing = set(REQUIRED_COLUMNS) - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required tick columns: {missing}"
        )

    df = df.copy()

    df["ltp"] = pd.to_numeric(
        df["ltp"],
        errors="coerce"
    )

    df["exchange_timestamp_ms"] = pd.to_numeric(
        df["exchange_timestamp_ms"],
        errors="coerce"
    )

    df["cumulative_volume"] = pd.to_numeric(
        df["cumulative_volume"],
        errors="coerce"
    )

    df = df.dropna(
        subset=[
            "symbol",
            "instrument_key",
            "ltp",
            "exchange_timestamp_ms",
        ]
    ).copy()

    if df.empty:
        return df

    df["exchange_time"] = pd.to_datetime(
        df["exchange_timestamp_ms"],
        unit="ms",
        utc=True
    ).dt.tz_convert(IST)

    df["session_date"] = (
        df["exchange_time"].dt.date
    )

    df = df.sort_values(
        [
            "instrument_key",
            "exchange_time",
            "ltp",
        ]
    )

    # Remove exact duplicate observations.
    df = df.drop_duplicates(
        subset=[
            "instrument_key",
            "exchange_timestamp_ms",
            "ltp",
        ],
        keep="last"
    )

    return df.reset_index(drop=True)


# ==========================================================
# 2. PREPARE GENUINE MARKET UPDATES
# ==========================================================

def prepare_live_updates(df):
    """
    Calculate cumulative-volume increments.

    Initial snapshots establish the volume baseline.
    Only feed_update observations are used for candles.
    """

    if df.empty:
        return df.copy()

    df = df.copy()

    df = df.sort_values(
        [
            "instrument_key",
            "session_date",
            "exchange_time",
        ]
    )

    df["observed_volume_delta"] = (
        df.groupby(
            [
                "instrument_key",
                "session_date",
            ]
        )["cumulative_volume"].diff()
    )

    # Negative differences can indicate volume resets.
    # Do not convert them into artificial positive volume.
    df.loc[
        df["observed_volume_delta"] < 0,
        "observed_volume_delta"
    ] = np.nan

    # Exclude initial snapshots.
    updates = df[
        df["message_kind"] == "feed_update"
    ].copy()

    if updates.empty:
        return updates

    # NSE regular market session: 09:15 to 15:30 IST.
    session_time = updates["exchange_time"].dt.time

    start_time = pd.Timestamp(
        "09:15"
    ).time()

    end_time = pd.Timestamp(
        "15:30"
    ).time()

    updates = updates[
        (session_time >= start_time)
        & (session_time < end_time)
    ].copy()

    return updates.reset_index(drop=True)


# ==========================================================
# 3. BUILD OHLC CANDLES
# ==========================================================

def build_candles(ticks, timeframe):
    """
    Build OHLC candles separately for each instrument
    and trading session.

    Supported timeframe arguments:
        1min
        5min
        15min
    """

    if timeframe not in TIMEFRAMES:
        raise ValueError(
            f"Unsupported timeframe: {timeframe}"
        )

    if ticks.empty:
        return pd.DataFrame()

    required = {
        "symbol",
        "instrument_key",
        "session_date",
        "exchange_time",
        "ltp",
        "observed_volume_delta",
    }

    missing = required - set(ticks.columns)

    if missing:
        raise ValueError(
            f"Missing candle input columns: {missing}"
        )

    results = []

    grouped = ticks.groupby(
        [
            "symbol",
            "instrument_key",
            "session_date",
        ],
        sort=True
    )

    for (
        symbol,
        instrument_key,
        session_date
    ), group in grouped:

        group = group.copy()

        group = group.sort_values(
            "exchange_time"
        )

        group = group.set_index(
            "exchange_time"
        )

        is_index = str(
            instrument_key
        ).startswith("NSE_INDEX|")

        # Index volume is not supplied as traded volume.
        if is_index:
            group["observed_volume_delta"] = np.nan

        candles = group.resample(
            timeframe,
            origin="start_day",
            offset="15min",
            label="left",
            closed="left"
        ).agg(
            open=("ltp", "first"),
            high=("ltp", "max"),
            low=("ltp", "min"),
            close=("ltp", "last"),
            tick_count=("ltp", "count"),
            observed_volume=(
                "observed_volume_delta",
                lambda x: x.sum(min_count=1)
            )
        )

        candles = candles.dropna(
            subset=[
                "open",
                "high",
                "low",
                "close",
            ]
        )

        if candles.empty:
            continue

        candles["symbol"] = symbol

        candles["instrument_key"] = (
            instrument_key
        )

        candles["session_date"] = str(
            session_date
        )

        candles["timeframe"] = timeframe

        candles["candle_start"] = candles.index

        candles["candle_end"] = (
            candles.index
            + pd.Timedelta(timeframe)
        )

        candles["is_index"] = is_index

        if is_index:
            candles["observed_volume"] = np.nan

        # Indicator engine requires a volume column.
        # This represents observed volume increments only.
        candles["volume"] = (
            candles["observed_volume"]
        )

        candles = candles.reset_index(
            drop=True
        )

        results.append(candles)

    if not results:
        return pd.DataFrame()

    return pd.concat(
        results,
        ignore_index=True
    )


# ==========================================================
# 4. MARK COMPLETE AND INCOMPLETE CANDLES
# ==========================================================

def mark_candle_completion(candles):
    """
    Mark a candle complete only after its interval ends.

    Uses the current Indian Standard Time.
    """

    if candles.empty:
        return candles

    candles = candles.copy()

    now = pd.Timestamp.now(
        tz=IST
    )

    candle_end = pd.to_datetime(
        candles["candle_end"],
        utc=True
    ).dt.tz_convert(IST)

    candles["is_complete"] = (
        candle_end <= now
    )

    return candles


# ==========================================================
# 5. BUILD INDICATORS AND SAVE OUTPUTS
# ==========================================================

def process_intraday_file(
    file_path,
    output_dir
):
    """
    Complete processing pipeline for one normalized
    Upstox tick CSV file.

    Returns:
        Dictionary containing candle and indicator
        DataFrames for each timeframe.
    """

    file_path = Path(file_path)

    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    print("=" * 60)
    print("BHARATMARKET AI - INTRADAY PIPELINE")
    print("=" * 60)

    print("Input:", file_path)

    ticks = load_ticks(file_path)

    updates = prepare_live_updates(ticks)

    print("\nDATA VALIDATION")

    print(
        "Normalized observations:",
        len(ticks)
    )

    print(
        "Actual feed updates:",
        len(updates)
    )

    print(
        "Instruments with updates:",
        updates["symbol"].nunique()
    )

    if updates.empty:

        print(
            "\nNo genuine intraday updates available."
        )

        print(
            "Snapshot-only records will not be "
            "converted into candles."
        )

        return {}

    session_id = file_path.stem

    results = {}

    for timeframe, label in TIMEFRAMES.items():

        print(
            f"\nPROCESSING {label.upper()} CANDLES"
        )

        candles = build_candles(
            updates,
            timeframe
        )

        if candles.empty:

            print(
                f"No {label} candles generated."
            )

            continue

        candles = mark_candle_completion(
            candles
        )

        # Calculate indicators separately by symbol
        # and timeframe.
        indicators = calculate_indicators(
            candles
        )

        candle_path = (
            output_dir
            / f"candles_{label}_{session_id}.csv"
        )

        indicator_path = (
            output_dir
            / f"indicators_{label}_{session_id}.csv"
        )

        # Preserve generated output as separate files.
        candles.to_csv(
            candle_path,
            index=False
        )

        indicators.to_csv(
            indicator_path,
            index=False
        )

        results[label] = {
            "candles": candles,
            "indicators": indicators,
            "candle_file": candle_path,
            "indicator_file": indicator_path,
        }

        print(
            f"{label}: {len(candles)} candles"
        )

        print(
            "Instruments:",
            candles["symbol"].nunique()
        )

        print(
            "Complete candles:",
            int(candles["is_complete"].sum())
        )

        print(
            "Incomplete candles:",
            int((~candles["is_complete"]).sum())
        )

        print(
            "Candle output:",
            candle_path
        )

        print(
            "Indicator output:",
            indicator_path
        )

    print("\n" + "=" * 60)
    print("INTRADAY PROCESSING FINISHED")
    print("=" * 60)

    return results


# ==========================================================
# 6. QUICK DATASET SUMMARY
# ==========================================================

def summarize_intraday_results(results):
    """
    Create a compact summary of generated candle files.
    """

    rows = []

    for timeframe, result in results.items():

        candles = result["candles"]

        if candles.empty:
            continue

        for symbol, group in candles.groupby("symbol"):

            rows.append({
                "symbol": symbol,
                "timeframe": timeframe,
                "candles": len(group),
                "complete_candles": int(
                    group["is_complete"].sum()
                ),
                "latest_close": group.iloc[-1]["close"],
                "latest_candle": str(
                    group.iloc[-1]["candle_start"]
                ),
            })

    return pd.DataFrame(rows)
