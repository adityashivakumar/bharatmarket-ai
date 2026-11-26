from collections import OrderedDict
from datetime import datetime, time, timedelta
from threading import RLock
from zoneinfo import ZoneInfo
from typing import Optional


IST = ZoneInfo("Asia/Kolkata")

TIMEFRAMES = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
}

MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)

MAX_CANDLES_PER_SYMBOL = 500


class StreamingCandleEngine:
    """
    Thread-safe in-memory intraday candle aggregator.

    Accepts normalized observations from UpstoxLiveFeedService.
    Uses exchange timestamps and cumulative-volume differences.
    """

    def __init__(self, max_candles=MAX_CANDLES_PER_SYMBOL):
        self.lock = RLock()
        self.max_candles = max_candles

        # {(symbol, timeframe): OrderedDict(candle_start -> candle)}
        self.candles = {}

        # Last cumulative volume for each instrument.
        self.last_cumulative_volume = {}

        # Last exchange timestamp for each instrument.
        self.last_exchange_timestamp = {}

        self.accepted_tick_count = 0
        self.ignored_snapshot_count = 0
        self.ignored_out_of_session_count = 0
        self.invalid_tick_count = 0

    @staticmethod
    def _parse_timestamp(timestamp_ms):
        timestamp = datetime.fromtimestamp(
            int(timestamp_ms) / 1000,
            tz=IST
        )
        return timestamp

    @staticmethod
    def _get_candle_start(exchange_time, minutes):
        session_start = exchange_time.replace(
            hour=9,
            minute=15,
            second=0,
            microsecond=0
        )

        elapsed_seconds = (
            exchange_time - session_start
        ).total_seconds()

        bucket_seconds = minutes * 60

        bucket_number = int(
            elapsed_seconds // bucket_seconds
        )

        return session_start + timedelta(
            seconds=bucket_number * bucket_seconds
        )

    def _update_volume_baseline(self, instrument_key, cumulative_volume):
        if cumulative_volume is None:
            return

        try:
            value = float(cumulative_volume)
        except (TypeError, ValueError):
            return

        if value < 0:
            return

        self.last_cumulative_volume[instrument_key] = value

    def update(self, observation):
        """
        Process one normalized feed observation.

        initial_snapshot:
            Seeds volume baseline only.

        feed_update:
            Updates candles and calculates volume delta.
        """

        if not isinstance(observation, dict):
            self.invalid_tick_count += 1
            return False

        symbol = observation.get("symbol")
        instrument_key = observation.get("instrument_key")
        message_kind = observation.get("message_kind")

        if not symbol or not instrument_key:
            self.invalid_tick_count += 1
            return False

        try:
            ltp = float(observation["ltp"])
            exchange_time = self._parse_timestamp(
                observation["exchange_timestamp_ms"]
            )
        except (KeyError, TypeError, ValueError, OverflowError):
            self.invalid_tick_count += 1
            return False

        if ltp <= 0:
            self.invalid_tick_count += 1
            return False

        cumulative_volume = observation.get("cumulative_volume")

        with self.lock:

            # A reconnect baseline must never create a false candle
            # or a false volume delta.
            if message_kind == "initial_snapshot":
                self._update_volume_baseline(
                    instrument_key,
                    cumulative_volume
                )
                self.last_exchange_timestamp[instrument_key] = exchange_time
                self.ignored_snapshot_count += 1
                return False

            if message_kind != "feed_update":
                self.invalid_tick_count += 1
                return False

            # Only accept ticks during the regular NSE session.
            exchange_clock = exchange_time.timetz().replace(tzinfo=None)

            if not (
                MARKET_OPEN <= exchange_clock < MARKET_CLOSE
            ):
                self.ignored_out_of_session_count += 1
                return False

            # Reject out-of-order observations for an instrument.
            previous_time = self.last_exchange_timestamp.get(
                instrument_key
            )

            if previous_time is not None and exchange_time < previous_time:
                self.invalid_tick_count += 1
                return False

            self.last_exchange_timestamp[instrument_key] = exchange_time

            # Calculate cumulative-volume difference.
            volume_delta = None

            if cumulative_volume is not None:
                try:
                    current_volume = float(cumulative_volume)

                    if current_volume >= 0:
                        previous_volume = (
                            self.last_cumulative_volume.get(instrument_key)
                        )

                        if previous_volume is not None:
                            delta = current_volume - previous_volume

                            # Negative delta means a reset or inconsistent
                            # reading. Do not create artificial volume.
                            if delta >= 0:
                                volume_delta = delta

                        # Always move the baseline forward after a valid
                        # reading, including a reset.
                        self.last_cumulative_volume[instrument_key] = (
                            current_volume
                        )

                except (TypeError, ValueError):
                    volume_delta = None

            for timeframe, minutes in TIMEFRAMES.items():

                candle_start = self._get_candle_start(
                    exchange_time,
                    minutes
                )

                candle_end = candle_start + timedelta(
                    minutes=minutes
                )

                key = (symbol, timeframe)

                if key not in self.candles:
                    self.candles[key] = OrderedDict()

                symbol_candles = self.candles[key]

                candle = symbol_candles.get(candle_start)

                if candle is None:
                    candle = {
                        "symbol": symbol,
                        "instrument_key": instrument_key,
                        "timeframe": timeframe,
                        "candle_start": candle_start,
                        "candle_end": candle_end,
                        "open": ltp,
                        "high": ltp,
                        "low": ltp,
                        "close": ltp,
                        "volume": 0.0,
                        "volume_observations": 0,
                        "tick_count": 0,
                        "first_tick_time": exchange_time,
                        "last_tick_time": exchange_time,
                    }

                    symbol_candles[candle_start] = candle

                # High and low are independent of tick arrival order.
                candle["high"] = max(candle["high"], ltp)
                candle["low"] = min(candle["low"], ltp)

                # Preserve chronological open and close.
                if exchange_time < candle["first_tick_time"]:
                    candle["open"] = ltp
                    candle["first_tick_time"] = exchange_time

                if exchange_time >= candle["last_tick_time"]:
                    candle["close"] = ltp
                    candle["last_tick_time"] = exchange_time

                candle["tick_count"] += 1

                if volume_delta is not None:
                    candle["volume"] += volume_delta
                    candle["volume_observations"] += 1

                # Keep memory bounded.
                while len(symbol_candles) > self.max_candles:
                    symbol_candles.popitem(last=False)

            self.accepted_tick_count += 1
            return True

    def get_candles(self, symbol, timeframe="1m", limit=200):
        if timeframe not in TIMEFRAMES:
            raise ValueError(
                f"Unsupported timeframe: {timeframe}"
            )

        if not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")

        with self.lock:
            source = self.candles.get(
                (symbol.upper(), timeframe),
                OrderedDict()
            )

            rows = list(source.values())[-limit:]

            now = datetime.now(IST)
            result = []

            for candle in rows:
                row = candle.copy()

                row["candle_start"] = (
                    row["candle_start"].isoformat()
                )
                row["candle_end"] = (
                    row["candle_end"].isoformat()
                )
                row["first_tick_time"] = (
                    row["first_tick_time"].isoformat()
                )
                row["last_tick_time"] = (
                    row["last_tick_time"].isoformat()
                )

                row["is_complete"] = (
                    now >= candle["candle_end"]
                )

                # If no valid volume differences were observed,
                # report unavailable rather than claiming zero volume.
                if row["volume_observations"] == 0:
                    row["volume"] = None

                result.append(row)

            return result

    def get_snapshot(self):
        with self.lock:
            return {
                "accepted_tick_count": self.accepted_tick_count,
                "ignored_snapshot_count": self.ignored_snapshot_count,
                "ignored_out_of_session_count": (
                    self.ignored_out_of_session_count
                ),
                "invalid_tick_count": self.invalid_tick_count,
                "symbols": sorted({
                    symbol
                    for symbol, _ in self.candles.keys()
                }),
                "timeframes": list(TIMEFRAMES.keys()),
            }


# Shared engine instance for the application.
candle_engine = StreamingCandleEngine()
