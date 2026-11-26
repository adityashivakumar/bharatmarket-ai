# BHARATMARKET AI — Research Architecture

## Product definition

BHARATMARKET AI is a research and decision-support terminal for Indian equities and the NIFTY 50 index. It supports intraday market observation and swing/investment research. It does not execute broker orders.

## Approved scope

- Universe: NIFTY 50 index plus 20 named Indian equities.
- Intraday horizons: Upstox 1-minute, 5-minute and 15-minute streaming candles where the instrument subscription is configured.
- Swing horizons: 1, 5 and 10 trading days.
- Automation: research calculations and recommendations only; no automatic order placement.
- Historical source: local daily OHLCV CSV files.
- Live source: existing Upstox WebSocket integration.

## Current repository facts

The merged live terminal is in `web/app/page.tsx`; FastAPI endpoints are in `api_server.py`; Upstox candle and indicator processing is in `upstox_integration/live/`.

At the time this architecture was added, `data/raw` contained daily CSVs for NIFTY50, BANKNIFTY, HDFCBANK, ICICIBANK, INFY, ITC, LT, RELIANCE, SBIN and TCS. This is not the complete approved 21-instrument universe. Research endpoints report each target instrument's data readiness and return a missing-data response instead of fabricating values.

Existing `outputs/models/*.joblib`, forecast CSVs and model comparison reports are retained as historical project artifacts. Their presence does not prove that a model can be loaded safely, that its feature schema matches current data, or that it generalizes out of sample. In particular, the NIFTY50 metadata currently identifies a Zero Return Baseline as its selected model. Do not present the artifact inventory as verified AI inference.

## Research modules

### Market Analysis / Scanner
Ranks available equities using EMA 9/21/50 alignment and MACD direction. The score is a transparent heuristic, not a calibrated probability or trade recommendation.

### Forecasting
Provides 1-, 5- and 10-session exploratory price baselines using the trailing 60-session mean daily return and volatility bands. This is deliberately labelled a statistical drift baseline, not a trained machine-learning forecast. The bands are approximate and not calibrated prediction intervals.

### Backtesting
Runs a daily SMA 20/50 long/cash crossover. Positions are shifted by one session to reduce look-ahead bias. A configurable turnover cost is applied. Results exclude intraday fills, taxes, market impact and full corporate-action validation, so they are research simulations only.

### Risk Analytics
Calculates single-instrument historical annualized volatility, maximum drawdown, daily historical 95% VaR/CVaR and a zero-risk-free-rate Sharpe statistic. It is not portfolio-level risk until holdings and weights are supplied.

### Data Explorer
Shows target universe, file availability, valid row counts and date coverage. Missing symbols must be ingested from an authorized data source before they can be analyzed.

### System Monitor
Reports backend health and should be extended with live-feed freshness, ingestion lag, model status and service diagnostics.

## API

Read-only endpoints under `/research`:

- `GET /research/universe`
- `GET /research/catalog`
- `GET /research/scanner`
- `GET /research/technical/{symbol}`
- `GET /research/forecast/{symbol}`
- `GET /research/backtest/{symbol}?fast=20&slow=50&cost_bps=10`
- `GET /research/risk/{symbol}`

Unknown symbols return 422; known symbols without a local CSV return 404. Research endpoints do not start the Upstox feed and do not place orders.

## Implementation roadmap

1. **Research workspace foundation (this branch):** expose transparent historical scanner, technical summary, baseline forecast, SMA backtest, single-symbol risk metrics and dataset catalog; add tests and interactive frontend pages.
2. **Universe data completion:** acquire and validate historical data for all 20 stocks; add symbol/instrument-key mapping and authorized Upstox subscriptions. Show readiness per instrument.
3. **Intraday research:** compute intraday features from completed 1m/5m/15m candles; distinguish incomplete candles; test session boundaries and stale data.
4. **Model validation:** establish chronological walk-forward splits, compare against zero-return and persistence baselines, report MAE/RMSE/directional accuracy and calibration; reject models that do not beat baselines after costs.
5. **Model serving:** only load artifacts with a versioned feature manifest, training cutoff, library versions and validation report. Never deserialize untrusted model files.
6. **Portfolio risk:** support user-defined holdings/weights, correlation, concentration, portfolio VaR/CVaR and scenario stress.
7. **Security and release:** authentication/authorization before any non-local exposure, rate limiting, audit logs, HTTPS, secret rotation, dependency and artifact scanning.

## Safety and operating constraints

- Paper-only order ticket remains disabled.
- No broker order-placement endpoint is added by this work.
- No predictions are represented as guarantees.
- Missing data and stale live data must be visible, not silently imputed.
- Keep FastAPI bound to loopback for local development until authentication and deployment controls are implemented.
