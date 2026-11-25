# BharatMarket AI — Professional Terminal UI

This branch introduces a unified dark institutional-style Streamlit workspace inspired by common interaction patterns in Bloomberg Terminal, TradingView and Koyfin. It is an original implementation and does not copy proprietary layouts or assets.

## Included
- Unified grouped navigation and terminal header
- Shared typography, colour, spacing, metric, chart and table styling
- Existing overview, technical analysis and Upstox live-feed pages retained
- Forecasting, backtesting and risk screens for saved CSV research artifacts
- CSV data explorer with preview and downloads
- Read-only local system monitor
- Trading Signals remains gated pending live-feed and candle validation

## Install
Back up the current project, then update these files from this branch:
- `app.py`
- `dashboard/theme.py`
- Add `dashboard/terminal_pages.py`

No historical data, research notebooks or Upstox backend source files are modified by this UI change.

Run:
```powershell
python -m streamlit run app.py --server.port 8501
```

The UI labels historical data as historical. A WebSocket connection is not itself proof that fresh market data is arriving.
