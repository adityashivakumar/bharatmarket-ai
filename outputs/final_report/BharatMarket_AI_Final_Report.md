# BHARATMARKET AI
## Final Integrated Project Report

Report generated: 25 November 2026, 17:44

## 1. Project Overview
BharatMarket AI is an Indian stock market forecasting and analytics project covering ten market instruments. It combines historical data validation, exploratory analysis, technical feature engineering, statistical forecasting, machine learning, walk-forward validation, signal generation, backtesting and portfolio risk analysis.

## 2. Instruments
- NIFTY50
- BANKNIFTY
- RELIANCE
- TCS
- HDFCBANK
- INFY
- ICICIBANK
- SBIN
- ITC
- LT

## 3. Methodology
- Historical market data is stored in CSV files.
- Data is validated and cleaned before feature engineering.
- Statistical models and machine-learning models are evaluated.
- Chronological validation is used to respect time ordering.
- The ML forecasting target is next-day return.
- Statistical forecasts use a price-level target.
- Trading strategies are evaluated through historical simulation.

## 4. Model Evaluation
Statistical and machine-learning evaluation results are reported separately because their forecasting targets and error units differ.

## 5. Backtesting and Risk
The backtesting and risk-management reports contain the simulated portfolio results, trading performance, drawdown and risk metrics. These are historical simulation outputs, not guarantees of future returns.

## 6. Limitations
- Historical data and model performance may not represent future market conditions.
- Daily forecasts are not equivalent to intraday predictions.
- Underlying price forecasts do not establish options premium or options P&L performance.
- The backtest uses assumptions about execution, costs and daily OHLC prices.
- Statistical price-level RMSE and ML return RMSE are not directly comparable.
- Live market integration and automated data updates are planned future work.

## 7. Future Enhancements
- Upstox API integration for live market data.
- Automated daily historical data updates.
- Streamlit-based interactive dashboard.
- Model monitoring and periodic retraining.
- Separate intraday forecasting models.
- Expanded transaction-cost and execution modelling.