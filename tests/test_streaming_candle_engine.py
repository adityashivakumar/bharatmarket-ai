import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from upstox_integration.live.streaming_candle_engine import (
    StreamingCandleEngine,
)


IST = ZoneInfo("Asia/Kolkata")


def make_tick(
    seconds,
    ltp,
    volume,
    kind="feed_update",
    symbol="RELIANCE",
    instrument="NSE_EQ|INE002A01018",
):
    timestamp = datetime(
        2026, 11, 26, 9, 15, seconds,
        tzinfo=IST
    )

    return {
        "symbol": symbol,
        "instrument_key": instrument,
        "ltp": ltp,
        "exchange_timestamp_ms": int(
            timestamp.timestamp() * 1000
        ),
        "message_kind": kind,
        "cumulative_volume": volume,
    }


class TestStreamingCandleEngine(unittest.TestCase):

    def setUp(self):
        self.engine = StreamingCandleEngine()

    def test_initial_snapshot_only_sets_baseline(self):
        result = self.engine.update(
            make_tick(0, 100.0, 1000, "initial_snapshot")
        )

        self.assertFalse(result)
        self.assertEqual(
            self.engine.last_cumulative_volume[
                "NSE_EQ|INE002A01018"
            ],
            1000
        )
        self.assertEqual(
            self.engine.get_candles("RELIANCE", "1m"),
            []
        )

    def test_one_minute_ohlc_and_volume(self):
        self.engine.update(
            make_tick(0, 100.0, 1000, "initial_snapshot")
        )

        self.engine.update(make_tick(10, 101.0, 1010))
        self.engine.update(make_tick(30, 105.0, 1025))
        self.engine.update(make_tick(50, 102.0, 1040))

        candles = self.engine.get_candles(
            "RELIANCE", "1m"
        )

        self.assertEqual(len(candles), 1)

        candle = candles[0]

        self.assertEqual(candle["open"], 101.0)
        self.assertEqual(candle["high"], 105.0)
        self.assertEqual(candle["low"], 101.0)
        self.assertEqual(candle["close"], 102.0)
        self.assertEqual(candle["volume"], 40.0)
        self.assertEqual(candle["tick_count"], 3)

    def test_five_and_fifteen_minute_candles(self):
        self.engine.update(
            make_tick(0, 100.0, 1000, "initial_snapshot")
        )

        self.engine.update(make_tick(10, 101.0, 1010))

        timestamp = datetime(
            2026, 11, 26, 9, 20, 10,
            tzinfo=IST
        )

        tick = make_tick(10, 110.0, 1020)
        tick["exchange_timestamp_ms"] = int(
            timestamp.timestamp() * 1000
        )

        self.engine.update(tick)

        self.assertEqual(
            len(self.engine.get_candles("RELIANCE", "1m")),
            2
        )
        self.assertEqual(
            len(self.engine.get_candles("RELIANCE", "5m")),
            2
        )
        self.assertEqual(
            len(self.engine.get_candles("RELIANCE", "15m")),
            1
        )

    def test_volume_reset_does_not_create_negative_volume(self):
        self.engine.update(
            make_tick(0, 100.0, 100, "initial_snapshot")
        )

        self.engine.update(make_tick(10, 101.0, 90))
        self.engine.update(make_tick(20, 102.0, 95))

        candle = self.engine.get_candles(
            "RELIANCE", "1m"
        )[0]

        self.assertEqual(candle["volume"], 5.0)
        self.assertEqual(candle["volume_observations"], 1)

    def test_out_of_session_tick_is_rejected(self):
        self.engine.update(
            make_tick(0, 100.0, 1000, "initial_snapshot")
        )

        timestamp = datetime(
            2026, 11, 26, 8, 59, 10,
            tzinfo=IST
        )

        tick = make_tick(10, 101.0, 1010)
        tick["exchange_timestamp_ms"] = int(
            timestamp.timestamp() * 1000
        )

        result = self.engine.update(tick)

        self.assertFalse(result)
        self.assertEqual(
            self.engine.get_candles("RELIANCE", "1m"),
            []
        )

    def test_invalid_timeframe_is_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.get_candles(
                "RELIANCE", "30m"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
