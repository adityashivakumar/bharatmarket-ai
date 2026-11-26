import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd

import research_service as research


def sample_frame(n=140):
    dates = pd.bdate_range("2025-01-01", periods=n)
    close = 100 * np.exp(np.linspace(0, 0.25, n) + 0.015*np.sin(np.arange(n)/5))
    return pd.DataFrame({
        "date": dates, "open": close * 0.998, "high": close * 1.01,
        "low": close * 0.99, "close": close, "volume": np.full(n, 100000),
    })


class ResearchServiceTests(unittest.TestCase):
    def test_indicators_have_expected_columns(self):
        result = research.indicators(sample_frame())
        self.assertTrue({"ema_9", "ema_21", "ema_50", "rsi_14", "atr_14", "macd"} <= set(result.columns))
        self.assertTrue(pd.notna(result.iloc[-1]["ema_50"]))

    def test_forecast_is_transparent_baseline(self):
        with patch.object(research, "load_daily", return_value=sample_frame()):
            result = research.forecast("RELIANCE")
        self.assertEqual(result["method"], "60-session historical mean-return drift baseline")
        self.assertEqual([x["horizon_trading_days"] for x in result["forecasts"]], [1, 5, 10])
        self.assertIn("not an ML model", result["limitations"])

    def test_backtest_shifts_signal_and_reports_costs(self):
        with patch.object(research, "load_daily", return_value=sample_frame()):
            result = research.backtest("RELIANCE", 10, 30, 10)
        self.assertGreater(result["observations"], 0)
        self.assertEqual(result["cost_bps_per_turnover"], 10)
        self.assertIn("look-ahead", result["disclaimer"])

    def test_risk_metrics_are_finite(self):
        with patch.object(research, "load_daily", return_value=sample_frame()):
            result = research.risk("RELIANCE")
        self.assertEqual(result["observations"], 139)
        self.assertTrue(np.isfinite(result["annualized_volatility_pct"]))

    def test_unavailable_symbol_rejected(self):
        with patch.object(research, "RAW", research.ROOT / "path_that_does_not_exist"):
            with self.assertRaises(FileNotFoundError):
                research.load_daily("RELIANCE")

    def test_invalid_symbol_rejected(self):
        with self.assertRaises(ValueError):
            research.load_daily("NOT_A_SYMBOL")


if __name__ == "__main__":
    unittest.main()
