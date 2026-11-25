
from pathlib import Path
import pandas as pd
import numpy as np

SYMBOLS = [
    "NIFTY50", "BANKNIFTY", "RELIANCE", "TCS",
    "HDFCBANK", "INFY", "ICICIBANK", "SBIN",
    "ITC", "LT"
]

STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY",
    "ICICIBANK", "SBIN", "ITC", "LT"
]


def load_instrument(project_dir, symbol):

    file_path = (
        Path(project_dir) / "data" / "raw" / f"{symbol}.csv"
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"Historical data file not found: {file_path}"
        )

    df = pd.read_csv(file_path)

    df.columns = [
        str(c).strip().lower() for c in df.columns
    ]

    required = [
        "date", "open", "high", "low", "close", "volume"
    ]

    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(
            f"{symbol}: Missing columns {missing}"
        )

    df["date"] = pd.to_datetime(
        df["date"], errors="coerce"
    )

    numeric_columns = [
        "open", "high", "low", "close", "volume"
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(
            df[col], errors="coerce"
        )

    df = (
        df.dropna(subset=["date", "close"])
        .sort_values("date")
        .drop_duplicates(subset=["date"], keep="last")
        .reset_index(drop=True)
    )

    df["symbol"] = symbol

    return df


def load_all_market_data(project_dir):

    data = {}
    errors = {}

    for symbol in SYMBOLS:
        try:
            data[symbol] = load_instrument(
                project_dir, symbol
            )
        except Exception as exc:
            errors[symbol] = str(exc)

    return data, errors


def add_indicators(df):

    df = df.copy()

    df["daily_return"] = df["close"].pct_change() * 100

    df["ema_20"] = df["close"].ewm(
        span=20, adjust=False
    ).mean()

    df["ema_50"] = df["close"].ewm(
        span=50, adjust=False
    ).mean()

    delta = df["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1/14, adjust=False, min_periods=14
    ).mean()

    avg_loss = loss.ewm(
        alpha=1/14, adjust=False, min_periods=14
    ).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    df["rsi_14"] = 100 - (100 / (1 + rs))

    return df


def get_instrument_summary(df):

    if df.empty:
        return {}

    latest = df.iloc[-1]

    previous_close = (
        df.iloc[-2]["close"] if len(df) >= 2 else np.nan
    )

    change = (
        latest["close"] - previous_close
        if pd.notna(previous_close) else np.nan
    )

    change_pct = (
        change / previous_close * 100
        if pd.notna(previous_close)
        and previous_close != 0
        else np.nan
    )

    return {
        "date": latest["date"],
        "close": latest["close"],
        "previous_close": previous_close,
        "change": change,
        "change_pct": change_pct,
        "volume": latest["volume"],
        "open": latest["open"],
        "high": latest["high"],
        "low": latest["low"],
    }


def calculate_market_breadth(data):

    advances = 0
    declines = 0
    unchanged = 0
    unavailable = 0

    for symbol in STOCKS:

        df = data.get(symbol)

        if df is None or len(df) < 2:
            unavailable += 1
            continue

        change = df.iloc[-1]["close"] - df.iloc[-2]["close"]

        if change > 0:
            advances += 1
        elif change < 0:
            declines += 1
        else:
            unchanged += 1

    return {
        "advances": advances,
        "declines": declines,
        "unchanged": unchanged,
        "unavailable": unavailable,
        "total": len(STOCKS),
    }
