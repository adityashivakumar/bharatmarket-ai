import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard.market_data import (
    SYMBOLS, STOCKS, load_all_market_data, add_indicators,
    get_instrument_summary, calculate_market_breadth,
)


def _section(title, meta=""):
    st.markdown(
        f'<div class="bm-section"><strong>{title}</strong><span>{meta}</span></div>',
        unsafe_allow_html=True,
    )


def _fmt(value, digits=2):
    return "—" if pd.isna(value) else f"{value:,.{digits}f}"


def render_overview(project_dir):
    data, errors = load_all_market_data(project_dir)

    st.markdown('<div class="bm-eyebrow">NSE India / Market intelligence</div>', unsafe_allow_html=True)
    st.title("Market overview")
    st.caption("Historical daily market data · Latest available observations · Not a live quote")

    if not data:
        st.error("No historical market datasets could be loaded.")
        for symbol, error in errors.items():
            st.write(f"{symbol}: {error}")
        return

    # Index summary strip
    _section("INDEX MONITOR", "HISTORICAL CLOSE")
    index_cols = st.columns(2)
    for col, symbol in zip(index_cols, ["NIFTY50", "BANKNIFTY"]):
        with col:
            df = data.get(symbol)
            if df is None or df.empty:
                st.metric(symbol, "Unavailable")
                continue
            summary = get_instrument_summary(df)
            delta = summary["change_pct"]
            col.metric(
                symbol, _fmt(summary["close"]),
                f"{delta:+.2f}%" if pd.notna(delta) else None,
                help="Latest historical daily close, not a real-time quote.",
            )
            st.caption(f"SESSION DATE  ·  {summary['date']:%d %b %Y}")

    _section("MARKET BREADTH", "EIGHT EQUITY CONSTITUENTS")
    breadth = calculate_market_breadth(data)
    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Advances", breadth["advances"])
    b2.metric("Declines", breadth["declines"])
    b3.metric("Unchanged", breadth["unchanged"])
    b4.metric("Unavailable", breadth["unavailable"])
    st.caption("Breadth uses the eight equity stocks in the current project watchlist; indices are excluded.")

    _section("PRICE DISCOVERY", "DAILY OHLC")
    c1, c2, c3 = st.columns([1.2, 1, 1])
    available_symbols = [s for s in SYMBOLS if s in data and not data[s].empty]
    if not available_symbols:
        st.warning("No usable instrument series found.")
        return
    selected_symbol = c1.selectbox("INSTRUMENT", available_symbols, key="overview_symbol")
    period = c2.selectbox("LOOKBACK", ["1M", "3M", "6M", "1Y", "5Y"], index=2, key="overview_period")
    chart_type = c3.selectbox("CHART", ["Candlestick", "Close line"], key="overview_chart_type")

    df = add_indicators(data[selected_symbol])
    days = {"1M": 31, "3M": 92, "6M": 183, "1Y": 365, "5Y": 1826}[period]
    chart_df = df[df["date"] >= df["date"].max() - pd.Timedelta(days=days)].copy()

    if chart_df.empty:
        st.warning("No observations available for this period.")
    else:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=.035,
                            row_heights=[.76, .24])
        if chart_type == "Candlestick":
            fig.add_trace(go.Candlestick(
                x=chart_df["date"], open=chart_df["open"], high=chart_df["high"],
                low=chart_df["low"], close=chart_df["close"], name="OHLC",
                increasing_line_color="#20c997", decreasing_line_color="#f16b78",
            ), row=1, col=1)
        else:
            fig.add_trace(go.Scatter(
                x=chart_df["date"], y=chart_df["close"], name="Close",
                line=dict(color="#68a9e8", width=1.8),
            ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=chart_df["date"], y=chart_df["ema_20"], name="EMA 20",
            line=dict(color="#68a9e8", width=1.1),
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=chart_df["date"], y=chart_df["ema_50"], name="EMA 50",
            line=dict(color="#e6b45c", width=1.1),
        ), row=1, col=1)

        volume = pd.to_numeric(chart_df["volume"], errors="coerce")
        fig.add_trace(go.Bar(
            x=chart_df["date"], y=volume, name="Volume",
            marker_color="#526f8e", opacity=.65,
        ), row=2, col=1)

        fig.update_layout(
            height=610, template="plotly_dark",
            paper_bgcolor="#101925", plot_bgcolor="#101925",
            font=dict(family="Inter, sans-serif", color="#cbd5e1", size=10),
            margin=dict(l=12, r=12, t=34, b=12),
            legend=dict(orientation="h", y=1.04, x=0),
            hovermode="x unified", xaxis_rangeslider_visible=False,
        )
        fig.update_xaxes(gridcolor="#263547", showgrid=True)
        fig.update_yaxes(gridcolor="#263547", showgrid=True)
        st.plotly_chart(fig, width="stretch", config={"displaylogo": False, "scrollZoom": True})

        latest = chart_df.iloc[-1]
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("LATEST CLOSE", _fmt(latest["close"]))
        k2.metric("DAILY RETURN", f"{latest['daily_return']:+.2f}%" if pd.notna(latest["daily_return"]) else "—")
        k3.metric("RSI (14)", _fmt(latest["rsi_14"]))
        k4.metric("VOLUME", _fmt(latest["volume"], 0))

    _section("COVERAGE & WATCHLIST", "CURRENT LOCAL DATASET")
    rows = []
    for symbol in SYMBOLS:
        frame = data.get(symbol)
        if frame is None or frame.empty:
            rows.append({"Instrument": symbol, "Date": "—", "Close": None, "Change %": None, "Status": "MISSING"})
            continue
        summary = get_instrument_summary(frame)
        rows.append({
            "Instrument": symbol,
            "Date": summary["date"].strftime("%d %b %Y"),
            "Close": summary["close"],
            "Change %": summary["change_pct"],
            "Status": "HISTORICAL",
        })
    watch = pd.DataFrame(rows)
    st.dataframe(
        watch, width="stretch", hide_index=True,
        column_config={
            "Close": st.column_config.NumberColumn("Close", format="%.2f"),
            "Change %": st.column_config.NumberColumn("Change %", format="%.2f%%"),
        },
    )

    dates = [frame["date"].max() for frame in data.values() if not frame.empty]
    q1, q2, q3 = st.columns(3)
    q1.metric("Loaded instruments", len(data))
    q2.metric("Missing instruments", len(errors))
    q3.metric("Latest common available date", min(dates).strftime("%d %b %Y") if dates else "—")

    if errors:
        with st.expander("Dataset loading diagnostics"):
            for symbol, error in errors.items():
                st.error(f"{symbol}: {error}")

    st.markdown(
        '<div class="bm-note">DATA CLASSIFICATION: HISTORICAL DAILY CSV. Prices and breadth shown here are derived from the latest rows in local datasets; they are not live exchange quotes.</div>',
        unsafe_allow_html=True,
    )
