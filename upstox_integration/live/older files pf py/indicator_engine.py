
import numpy as np
import pandas as pd


def calculate_rsi(series, period=14):
    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    rsi = rsi.mask(
        (avg_gain == 0) & (avg_loss == 0), 50
    )

    rsi = rsi.mask(
        (avg_loss == 0) & (avg_gain > 0), 100
    )

    return rsi


def calculate_atr(df, period=14):
    previous_close = df["close"].shift(1)

    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs()
        ],
        axis=1
    ).max(axis=1)

    return true_range.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()


def calculate_indicators(candles):

    if candles.empty:
        return pd.DataFrame()

    required = {
        "symbol", "timeframe", "candle_start",
        "open", "high", "low", "close", "volume"
    }

    missing = required - set(candles.columns)

    if missing:
        raise ValueError(
            f"Missing candle columns: {missing}"
        )

    outputs = []

    for (symbol, timeframe), group in candles.groupby(
        ["symbol", "timeframe"]
    ):

        df = group.copy()

        df["candle_start"] = pd.to_datetime(
            df["candle_start"]
        )

        df = df.sort_values(
            "candle_start"
        ).reset_index(drop=True)

        close = df["close"]

        # Exponential moving averages
        df["ema_9"] = close.ewm(
            span=9, adjust=False, min_periods=9
        ).mean()

        df["ema_21"] = close.ewm(
            span=21, adjust=False, min_periods=21
        ).mean()

        df["ema_50"] = close.ewm(
            span=50, adjust=False, min_periods=50
        ).mean()

        # RSI
        df["rsi_14"] = calculate_rsi(close, 14)

        # MACD
        ema_12 = close.ewm(
            span=12, adjust=False, min_periods=12
        ).mean()

        ema_26 = close.ewm(
            span=26, adjust=False, min_periods=26
        ).mean()

        df["macd"] = ema_12 - ema_26

        df["macd_signal"] = df["macd"].ewm(
            span=9, adjust=False, min_periods=9
        ).mean()

        df["macd_histogram"] = (
            df["macd"] - df["macd_signal"]
        )

        # ATR
        df["atr_14"] = calculate_atr(df, 14)

        df["atr_percentage"] = (
            df["atr_14"] / close.replace(0, np.nan)
        ) * 100

        # Bollinger Bands
        rolling_mean = close.rolling(20).mean()
        rolling_std = close.rolling(20).std(ddof=0)

        df["bb_middle"] = rolling_mean
        df["bb_upper"] = rolling_mean + 2 * rolling_std
        df["bb_lower"] = rolling_mean - 2 * rolling_std

        df["bb_width"] = (
            (df["bb_upper"] - df["bb_lower"])
            / rolling_mean.replace(0, np.nan)
        ) * 100

        df["bb_position"] = (
            (close - df["bb_lower"])
            / (df["bb_upper"] - df["bb_lower"]).replace(
                0, np.nan
            )
        )

        # Session VWAP
        df["typical_price"] = (
            df["high"] + df["low"] + df["close"]
        ) / 3

        df["vwap"] = np.nan

        volume = pd.to_numeric(
            df["volume"], errors="coerce"
        )

        valid_volume = volume.notna() & (volume >= 0)

        if valid_volume.any():

            session_key = df["candle_start"].dt.date

            weighted_price = (
                df["typical_price"]
                * volume.where(valid_volume)
            )

            cumulative_pv = weighted_price.groupby(
                session_key
            ).cumsum()

            cumulative_volume = volume.where(
                valid_volume
            ).groupby(session_key).cumsum()

            df["vwap"] = (
                cumulative_pv
                / cumulative_volume.replace(0, np.nan)
            )

            df.loc[~valid_volume, "vwap"] = np.nan

        df["symbol"] = symbol
        df["timeframe"] = timeframe

        outputs.append(df)

    return pd.concat(outputs, ignore_index=True)
