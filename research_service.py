"""Read-only research analytics built from validated local daily OHLCV CSVs.

Forecasts are transparent statistical drift baselines, not trained ML predictions.
All analytics are historical research and do not place broker orders.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
UNIVERSE = [
    ("NIFTY50", "NIFTY 50", "index"),
    ("RELIANCE", "Reliance Industries", "equity"),
    ("TCS", "Tata Consultancy Services", "equity"),
    ("HDFCBANK", "HDFC Bank", "equity"),
    ("ICICIBANK", "ICICI Bank", "equity"),
    ("INFY", "Infosys", "equity"),
    ("ITC", "ITC Limited", "equity"),
    ("LT", "Larsen & Toubro", "equity"),
    ("SBIN", "State Bank of India", "equity"),
    ("BHARTIARTL", "Bharti Airtel", "equity"),
    ("KOTAKBANK", "Kotak Mahindra Bank", "equity"),
    ("AXISBANK", "Axis Bank", "equity"),
    ("MARUTI", "Maruti Suzuki", "equity"),
    ("SUNPHARMA", "Sun Pharmaceutical", "equity"),
    ("TITAN", "Titan Company", "equity"),
    ("ASIANPAINT", "Asian Paints", "equity"),
    ("ULTRACEMCO", "UltraTech Cement", "equity"),
    ("BAJFINANCE", "Bajaj Finance", "equity"),
    ("WIPRO", "Wipro", "equity"),
    ("ONGC", "ONGC", "equity"),
    ("NTPC", "NTPC", "equity"),
]
UNIVERSE_MAP = {s: {"symbol": s, "name": n, "type": t} for s, n, t in UNIVERSE}


def load_daily(symbol: str) -> pd.DataFrame:
    symbol = symbol.strip().upper()
    if symbol not in UNIVERSE_MAP:
        raise ValueError("Unsupported research symbol")
    path = RAW / f"{symbol}.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Historical CSV is not available for {symbol}")
    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    required = {"date", "open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{symbol} dataset is missing columns: {', '.join(sorted(missing))}")
    df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)
    for col in ("open", "high", "low", "close", "volume"):
        if col not in df:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["date", "open", "high", "low", "close"])
    df = df[(df["open"] > 0) & (df["high"] > 0) & (df["low"] > 0) & (df["close"] > 0)]
    df = df[(df["high"] >= df[["open", "low", "close"]].max(axis=1)) & (df["low"] <= df[["open", "high", "close"]].min(axis=1))]
    return df.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)


def indicators(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    c = x["close"]
    x["return"] = c.pct_change()
    x["ema_9"] = c.ewm(span=9, adjust=False, min_periods=9).mean()
    x["ema_21"] = c.ewm(span=21, adjust=False, min_periods=21).mean()
    x["ema_50"] = c.ewm(span=50, adjust=False, min_periods=50).mean()
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = gain / loss.replace(0, np.nan)
    x["rsi_14"] = 100 - 100 / (1 + rs)
    x.loc[(loss == 0) & (gain > 0), "rsi_14"] = 100
    x.loc[(loss == 0) & (gain == 0), "rsi_14"] = 50
    prev = c.shift(1)
    tr = pd.concat([x["high"]-x["low"], (x["high"]-prev).abs(), (x["low"]-prev).abs()], axis=1).max(axis=1)
    x["atr_14"] = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    x["macd"] = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    x["macd_signal"] = x["macd"].ewm(span=9, adjust=False).mean()
    x["sma_20"] = c.rolling(20).mean()
    x["sma_50"] = c.rolling(50).mean()
    x["volume_sma_20"] = x["volume"].rolling(20).mean()
    return x


def universe_status() -> dict[str, Any]:
    rows = []
    for symbol, name, kind in UNIVERSE:
        path = RAW / f"{symbol}.csv"
        item = {"symbol": symbol, "name": name, "type": kind, "available": path.is_file(), "rows": 0, "first_date": None, "last_date": None, "status": "MISSING"}
        if path.is_file():
            try:
                df = load_daily(symbol)
                item.update(rows=len(df), first_date=df["date"].min().date().isoformat() if len(df) else None, last_date=df["date"].max().date().isoformat() if len(df) else None, status="READY" if len(df) >= 60 else "INSUFFICIENT_HISTORY")
            except Exception as exc:
                item.update(status="INVALID", error=str(exc))
        rows.append(item)
    ready = sum(x["status"] == "READY" for x in rows)
    return {"target_count": len(rows), "ready_count": ready, "missing_count": sum(x["status"] == "MISSING" for x in rows), "instruments": rows, "source": "local_daily_csv"}


def technical_analysis(symbol: str) -> dict[str, Any]:
    df = indicators(load_daily(symbol))
    if len(df) < 50:
        raise ValueError("At least 50 valid daily candles are required")
    r = df.iloc[-1]
    close = float(r.close)
    trend = "BULLISH" if r.ema_9 > r.ema_21 > r.ema_50 and close > r.ema_50 else "BEARISH" if r.ema_9 < r.ema_21 < r.ema_50 and close < r.ema_50 else "MIXED"
    momentum = "POSITIVE" if r.macd > r.macd_signal else "NEGATIVE"
    return {"symbol": symbol.upper(), "as_of": r.date.date().isoformat(), "close": close, "trend": trend, "momentum": momentum, "rsi_14": _num(r.rsi_14), "macd": _num(r.macd), "macd_signal": _num(r.macd_signal), "atr_14": _num(r.atr_14), "ema_9": _num(r.ema_9), "ema_21": _num(r.ema_21), "ema_50": _num(r.ema_50), "sma_20": _num(r.sma_20), "sma_50": _num(r.sma_50), "volume": _num(r.volume), "volume_sma_20": _num(r.volume_sma_20), "interpretation": "Trend and momentum are descriptive historical indicators, not a standalone entry signal."}


def scanner() -> dict[str, Any]:
    results, missing = [], []
    for symbol, name, kind in UNIVERSE:
        if kind != "equity":
            continue
        try:
            a = technical_analysis(symbol)
            score = (2 if a["trend"] == "BULLISH" else -2 if a["trend"] == "BEARISH" else 0) + (1 if a["momentum"] == "POSITIVE" else -1)
            results.append({**a, "name": name, "score": score, "classification": "Bullish trend" if score >= 2 else "Bearish trend" if score <= -2 else "Mixed / wait"})
        except FileNotFoundError:
            missing.append(symbol)
        except Exception as exc:
            missing.append({"symbol": symbol, "reason": str(exc)})
    results.sort(key=lambda x: x["score"], reverse=True)
    return {"as_of": max((x["as_of"] for x in results), default=None), "available_count": len(results), "target_stock_count": 20, "missing": missing, "results": results, "method": "EMA 9/21/50 trend + MACD direction; heuristic ranking, not a probability model"}


def forecast(symbol: str, horizons: list[int] | None = None) -> dict[str, Any]:
    horizons = horizons or [1, 5, 10]
    if any(h not in (1, 5, 10) for h in horizons):
        raise ValueError("Supported horizons are 1, 5 and 10 trading days")
    df = indicators(load_daily(symbol))
    if len(df) < 80:
        raise ValueError("At least 80 valid daily candles are required for the baseline forecast")
    r = df.iloc[-1]
    returns = df["close"].pct_change().dropna().tail(60)
    mu, sigma = float(returns.mean()), float(returns.std(ddof=1))
    close = float(r.close)
    rows = []
    for h in horizons:
        expected = close * ((1 + mu) ** h)
        band = 1.96 * sigma * np.sqrt(h) * close
        rows.append({"horizon_trading_days": h, "expected_price_baseline": round(expected, 2), "lower_95_approx": round(max(0, expected-band), 2), "upper_95_approx": round(expected+band, 2), "expected_return_pct": round(((expected/close)-1)*100, 3)})
    return {"symbol": symbol.upper(), "as_of": r.date.date().isoformat(), "last_close": close, "method": "60-session historical mean-return drift baseline", "daily_mean_return_pct": round(mu*100, 4), "daily_volatility_pct": round(sigma*100, 4), "forecasts": rows, "limitations": "Exploratory baseline only. Approximate volatility bands are not calibrated prediction intervals. Not an ML model or a trading recommendation."}


def backtest(symbol: str, fast: int = 20, slow: int = 50, cost_bps: float = 10.0) -> dict[str, Any]:
    if not (2 <= fast < slow <= 200) or not (0 <= cost_bps <= 100):
        raise ValueError("Use 2 <= fast < slow <= 200 and 0 <= cost_bps <= 100")
    df = load_daily(symbol)
    if len(df) < slow + 5:
        raise ValueError(f"At least {slow+5} valid rows are required")
    x = df[["date", "close"]].copy()
    x["fast"] = x.close.rolling(fast).mean()
    x["slow"] = x.close.rolling(slow).mean()
    x["signal"] = (x.fast > x.slow).astype(float)
    x["position"] = x.signal.shift(1).fillna(0)
    x["asset_return"] = x.close.pct_change().fillna(0)
    x["turnover"] = x.position.diff().abs().fillna(x.position.abs())
    x["strategy_return"] = x.position*x.asset_return - x.turnover*(cost_bps/10000)
    x = x.dropna(subset=["fast", "slow"]).copy()
    if x.empty:
        raise ValueError("Not enough observations after indicator warm-up")
    equity = (1+x.strategy_return).cumprod()
    peak = equity.cummax().clip(lower=1.0)
    drawdown = equity/peak-1
    trades = int((x.turnover > 0).sum())
    wins = int((x.loc[x.turnover > 0, "strategy_return"] > 0).sum())
    total = float(equity.iloc[-1]-1)
    years = max((x.date.iloc[-1]-x.date.iloc[0]).days/365.25, 1/252)
    cagr = float(equity.iloc[-1]**(1/years)-1) if equity.iloc[-1] > 0 else -1.0
    vol = float(x.strategy_return.std(ddof=1)*np.sqrt(252)) if len(x)>1 else 0.0
    sharpe = float(x.strategy_return.mean()/x.strategy_return.std(ddof=1)*np.sqrt(252)) if x.strategy_return.std(ddof=1)>0 else None
    return {"symbol": symbol.upper(), "strategy": f"SMA {fast}/{slow} long/cash crossover", "period_start": x.date.iloc[0].date().isoformat(), "period_end": x.date.iloc[-1].date().isoformat(), "observations": len(x), "trades_or_position_changes": trades, "winning_position_days": wins, "total_return_pct": round(total*100,2), "cagr_pct": round(cagr*100,2), "annualized_volatility_pct": round(vol*100,2), "max_drawdown_pct": round(float(drawdown.min())*100,2), "sharpe_ratio": round(sharpe,3) if sharpe is not None else None, "cost_bps_per_turnover": cost_bps, "buy_and_hold_return_pct": round((float(x.close.iloc[-1]/x.close.iloc[0])-1)*100,2), "disclaimer": "Daily-bar research simulation. Signal is shifted one session to reduce look-ahead; excludes intraday fills, taxes, market impact and corporate-action validation."}


def risk(symbol: str) -> dict[str, Any]:
    df = load_daily(symbol)
    ret = df.close.pct_change().dropna()
    if len(ret) < 30:
        raise ValueError("At least 30 daily returns are required")
    equity = (1+ret).cumprod()
    dd = equity/equity.cummax()-1
    q = float(ret.quantile(0.05))
    tail = ret[ret <= q]
    vol = float(ret.std(ddof=1)*np.sqrt(252))
    return {"symbol": symbol.upper(), "as_of": df.date.iloc[-1].date().isoformat(), "observations": len(ret), "annualized_volatility_pct": round(vol*100,2), "max_drawdown_pct": round(float(dd.min())*100,2), "historical_var_95_daily_pct": round(q*100,3), "historical_cvar_95_daily_pct": round(float(tail.mean())*100,3), "sharpe_vs_zero_rf": round(float(ret.mean()/ret.std(ddof=1)*np.sqrt(252)),3) if ret.std(ddof=1)>0 else None, "method": "Historical daily close-to-close returns; no portfolio weights or risk-free rate applied."}


def data_catalog() -> dict[str, Any]:
    status = universe_status()
    return {"universe": status, "datasets": [{"symbol": x["symbol"], "file": f'{x["symbol"]}.csv', "rows": x["rows"], "first_date": x["first_date"], "last_date": x["last_date"], "status": x["status"]} for x in status["instruments"]]}


def _num(v: Any) -> float | None:
    return None if pd.isna(v) else round(float(v), 4)
