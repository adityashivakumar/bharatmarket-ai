
"""
BharatMarket AI - Upstox V3 Live Feed Service

One persistent WebSocket connection.
Thread-safe in-memory market state.
Normalized tick CSV logging.
Snapshot and subsequent updates are distinguished.
"""

import csv
import os
import threading
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import upstox_client
from dotenv import load_dotenv


IST = ZoneInfo("Asia/Kolkata")

PROJECT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_DIR / ".env"

TICK_DIR = (
    PROJECT_DIR
    / "upstox_integration"
    / "live"
    / "ticks"
)

MAPPING_FILE = (
    PROJECT_DIR
    / "upstox_integration"
    / "data"
    / "instrument_mapping.csv"
)

MODE = "full"

INSTRUMENTS = {
    "NIFTY50": "NSE_INDEX|Nifty 50",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
    "RELIANCE": "NSE_EQ|INE002A01018",
    "TCS": "NSE_EQ|INE467B01029",
    "HDFCBANK": "NSE_EQ|INE040A01034",
    "INFY": "NSE_EQ|INE009A01021",
    "ICICIBANK": "NSE_EQ|INE090A01021",
    "SBIN": "NSE_EQ|INE062A01020",
    "ITC": "NSE_EQ|INE154A01025",
    "LT": "NSE_EQ|INE018A01030",
}

CSV_COLUMNS = [
    "symbol",
    "instrument_key",
    "ltp",
    "exchange_timestamp_ms",
    "message_kind",
    "cumulative_volume",
    "received_at",
]


class UpstoxLiveFeedService:

    def __init__(self):

        self.lock = threading.RLock()

        self.streamer = None
        self.api_client = None
        self.thread = None

        self.connected = False
        self.started = False
        self.last_error = None
        self.last_message_time = None

        self.latest = {}
        self.seen_instruments = set()

        self.message_count = 0
        self.update_count = 0
        self.valid_observation_count = 0
        self.duplicate_observation_count = 0
        self.invalid_observation_count = 0
        self.last_update_time = None
        self.last_update_exchange_time = None
        self.last_observation_signature = {}

        self.stop_requested = False

        TICK_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        self.tick_file = (
            TICK_DIR
            / f"normalized_ticks_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.csv"
        )

        self._initialize_tick_file()

    # ------------------------------------------------------
    # CSV INITIALIZATION
    # ------------------------------------------------------

    def _initialize_tick_file(self):

        with self.tick_file.open(
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=CSV_COLUMNS
            )

            writer.writeheader()

    # ------------------------------------------------------
    # TOKEN AND API CLIENT
    # ------------------------------------------------------

    def _create_api_client(self):

        load_dotenv(
            ENV_FILE,
            override=True
        )

        token = os.getenv(
            "UPSTOX_ACCESS_TOKEN"
        )

        if not token:
            raise RuntimeError(
                "UPSTOX_ACCESS_TOKEN missing from .env"
            )

        configuration = (
            upstox_client.Configuration()
        )

        configuration.access_token = token

        return upstox_client.ApiClient(
            configuration
        )

    # ------------------------------------------------------
    # CONNECTION START
    # ------------------------------------------------------

    def start(self):

        with self.lock:

            if self.started:
                return {
                    "status": "already_started",
                    "connected": self.connected,
                }

            self.stop_requested = False
            self.last_error = None

            self.api_client = (
                self._create_api_client()
            )

            self.streamer = (
                upstox_client.MarketDataStreamerV3(
                    self.api_client,
                    list(INSTRUMENTS.values()),
                    MODE
                )
            )

            self.streamer.auto_reconnect(
                True,
                5,
                20
            )

            self.streamer.on(
                "open",
                self._on_open
            )

            self.streamer.on(
                "message",
                self._on_message
            )

            self.streamer.on(
                "error",
                self._on_error
            )

            self.streamer.on(
                "close",
                self._on_close
            )

            self.streamer.on(
                "reconnecting",
                self._on_reconnecting
            )

            self.streamer.on(
                "autoReconnectStopped",
                self._on_reconnect_stopped
            )

            self.thread = threading.Thread(
                target=self._run_connection,
                name="BharatMarket-Upstox-Feed",
                daemon=True
            )

            self.started = True

            self.thread.start()

            return {
                "status": "starting",
                "connected": False,
            }

    def _run_connection(self):

        try:
            self.streamer.connect()

        except Exception as error:

            with self.lock:
                self.last_error = str(error)
                self.connected = False
                self.started = False

    # ------------------------------------------------------
    # CONNECTION EVENTS
    # ------------------------------------------------------

    def _on_open(self):

        with self.lock:

            self.connected = True
            self.started = True
            self.last_error = None

            self.seen_instruments.clear()
            self.last_observation_signature.clear()

        print(
            "[UPSTOX] WebSocket connected"
        )

    def _on_close(
        self,
        *args
    ):

        with self.lock:

            self.connected = False

        print(
            "[UPSTOX] WebSocket closed:",
            args
        )

    def _on_error(
        self,
        error
    ):

        with self.lock:

            self.last_error = str(error)

        print(
            "[UPSTOX] ERROR:",
            error
        )

    def _on_reconnecting(
        self,
        message
    ):

        with self.lock:

            self.connected = False

        print(
            "[UPSTOX] RECONNECTING:",
            message
        )

    def _on_reconnect_stopped(
        self,
        message
    ):

        with self.lock:

            self.connected = False
            self.last_error = str(message)
            self.started = False

        print(
            "[UPSTOX] RECONNECT STOPPED:",
            message
        )

    # ------------------------------------------------------
    # SAFE NESTED DICTIONARY ACCESS
    # ------------------------------------------------------

    @staticmethod
    def _get(data, *keys, default=None):

        current = data

        for key in keys:

            if not isinstance(current, dict):
                return default

            current = current.get(key)

            if current is None:
                return default

        return current

    # ------------------------------------------------------
    # EXTRACT LIVE FEED FIELDS
    # ------------------------------------------------------

    def _extract_feed(self, instrument_key, feed):

        symbol = next(
            (
                name
                for name, key in INSTRUMENTS.items()
                if key == instrument_key
            ),
            instrument_key
        )

        full_feed = feed.get(
            "fullFeed",
            {}
        )

        market_feed = full_feed.get(
            "marketFF",
            {}
        )

        index_feed = full_feed.get(
            "indexFF",
            {}
        )

        # Equities and indices use different full-feed branches.
        branch = (
            market_feed
            if market_feed
            else index_feed
        )

        ltpc = (
            branch.get("ltpc")
            or feed.get("ltpc")
            or {}
        )

        ltp = ltpc.get("ltp")

        if ltp is None:
            return None

        exchange_timestamp_ms = ltpc.get("ltt")

        if exchange_timestamp_ms is None:
            return None

        try:
            exchange_timestamp_ms = int(
                exchange_timestamp_ms
            )
        except (TypeError, ValueError):
            return None

        try:
            ltp = float(ltp)
        except (TypeError, ValueError):
            return None

        if ltp <= 0:
            return None

        cumulative_volume = (
            market_feed.get("vtt")
        )

        if cumulative_volume is None:
            cumulative_volume = (
                branch.get("vtt")
            )

        try:
            cumulative_volume = (
                float(cumulative_volume)
                if cumulative_volume is not None
                else None
            )
        except (TypeError, ValueError):
            cumulative_volume = None

        return {
            "symbol": symbol,
            "instrument_key": instrument_key,
            "ltp": ltp,
            "exchange_timestamp_ms": exchange_timestamp_ms,
            "cumulative_volume": cumulative_volume,
            "previous_close": ltpc.get("cp"),
            "last_trade_quantity": ltpc.get("ltq"),
        }

    # ------------------------------------------------------
    # APPEND NORMALIZED TICK
    # ------------------------------------------------------

    def _append_tick(self, row):

        with self.tick_file.open(
            "a",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=CSV_COLUMNS
            )

            writer.writerow({
                key: row.get(key)
                for key in CSV_COLUMNS
            })

    # ------------------------------------------------------
    # MESSAGE CALLBACK
    # ------------------------------------------------------

    def _on_message(self, message):

        if not isinstance(message, dict):
            return

        feeds = message.get(
            "feeds",
            {}
        )

        if not isinstance(feeds, dict):
            return

        with self.lock:

            self.message_count += 1

            self.last_message_time = (
                datetime.now(IST).isoformat()
            )

            for instrument_key, feed in feeds.items():

                if not isinstance(feed, dict):
                    continue

                row = self._extract_feed(
                    instrument_key,
                    feed
                )

                if row is None:
                    self.invalid_observation_count += 1
                    continue

                signature = (
                    row["exchange_timestamp_ms"],
                    row["ltp"],
                    row.get("cumulative_volume"),
                )
                previous_signature = self.last_observation_signature.get(instrument_key)

                if previous_signature == signature:
                    self.duplicate_observation_count += 1
                    continue

                self.last_observation_signature[instrument_key] = signature
                received_at = datetime.now(IST).isoformat()

                # First distinct valid observation per instrument
                # after connection/reconnection is a baseline.
                if instrument_key not in self.seen_instruments:
                    message_kind = "initial_snapshot"
                    self.seen_instruments.add(instrument_key)
                else:
                    message_kind = "feed_update"
                    self.update_count += 1
                    self.last_update_time = received_at
                    self.last_update_exchange_time = pd.to_datetime(
                        row["exchange_timestamp_ms"], unit="ms", utc=True
                    ).tz_convert(IST).isoformat()

                self.valid_observation_count += 1
                row["message_kind"] = message_kind
                row["received_at"] = received_at

                self.latest[row["symbol"]] = row.copy()
                self._append_tick(row)

    # ------------------------------------------------------
    # GET LATEST MARKET DATA
    # ------------------------------------------------------

    def get_snapshot(self):

        with self.lock:

            rows = [
                value.copy()
                for value in self.latest.values()
            ]

            status = {
                "connected": self.connected,
                "started": self.started,
                "last_error": self.last_error,
                "last_message_time": self.last_message_time,
                "message_count": self.message_count,
                "update_count": self.update_count,
                "valid_observation_count": self.valid_observation_count,
                "duplicate_observation_count": self.duplicate_observation_count,
                "invalid_observation_count": self.invalid_observation_count,
                "last_update_time": self.last_update_time,
                "last_update_exchange_time": self.last_update_exchange_time,
                "tick_file": str(self.tick_file),
            }

        df = pd.DataFrame(rows)

        if not df.empty:

            df["exchange_time"] = pd.to_datetime(
                df["exchange_timestamp_ms"],
                unit="ms",
                utc=True
            ).dt.tz_convert(IST)

            df["previous_close"] = pd.to_numeric(
                df["previous_close"],
                errors="coerce"
            )

            df["change"] = (
                df["ltp"] - df["previous_close"]
            )

            df["change_pct"] = (
                df["change"]
                / df["previous_close"]
                * 100
            )

        return {
            "data": df,
            "status": status,
        }

    # ------------------------------------------------------
    # STOP CONNECTION
    # ------------------------------------------------------

    def stop(self):

        with self.lock:

            if not self.streamer:
                return

            self.stop_requested = True

            try:
                self.streamer.disconnect()
            except Exception as error:
                self.last_error = str(error)

            self.connected = False
            self.started = False

        print(
            "[UPSTOX] Disconnect requested"
        )


# ----------------------------------------------------------
# SINGLE PROCESS-WIDE SERVICE INSTANCE
# ----------------------------------------------------------

_SERVICE = None
_SERVICE_LOCK = threading.Lock()


def get_service():

    global _SERVICE

    with _SERVICE_LOCK:

        if _SERVICE is None:
            _SERVICE = UpstoxLiveFeedService()

        return _SERVICE
