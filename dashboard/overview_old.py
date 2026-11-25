
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard.market_data import (
    SYMBOLS,
    STOCKS,
    load_all_market_data,
    add_indicators,
    get_instrument_summary,
    calculate_market_breadth,
)


def render_overview(project_dir):

    st.title("Market Overview")

    st.caption(
        "Indian equity market intelligence | "
        "Historical market data and analytics"
    )

    data, errors = load_all_market_data(project_dir)

    if not data:
        st.error("No historical market datasets could be loaded.")

        for symbol, error in errors.items():
            st.write(f"{symbol}: {error}")

        return

    index_col1, index_col2 = st.columns(2)

    for col, symbol in zip(
        [index_col1, index_col2],
        ["NIFTY50", "BANKNIFTY"]
    ):

        with col:

            df = data.get(symbol)

            if df is None or df.empty:
                st.warning(f"{symbol}: Data unavailable")
                continue

            summary = get_instrument_summary(df)

            st.metric(
                label=symbol,
                value=f"{summary['close']:,.2f}",
                delta=(
                    f"{summary['change_pct']:+.2f}%"
                    if pd.notna(summary["change_pct"])
                    else None
                ),
                help=(
                    "Historical closing price. "
                    "Not a live market quote."
                )
            )

            st.caption(
                "Latest historical session: "
                + summary["date"].strftime("%d %b %Y")
            )

    st.divider()

    st.subheader("Market Breadth")

    breadth = calculate_market_breadth(data)

    b1, b2, b3, b4 = st.columns(4)

    b1.metric("Advances", breadth["advances"])
    b2.metric("Declines", breadth["declines"])
    b3.metric("Unchanged", breadth["unchanged"])
    b4.metric("Unavailable", breadth["unavailable"])

    st.caption(
        "Breadth is calculated using the eight equity stocks "
        "in the project watchlist, excluding the two indices."
    )

    st.divider()

    st.subheader("Historical Market Chart")

    available_symbols = [
        symbol for symbol in SYMBOLS if symbol in data
    ]

    selected_symbol = st.selectbox(
        "Select instrument",
        available_symbols,
        index=0
    )

    period = st.selectbox(
        "Historical period",
        ["1M", "3M", "6M", "1Y", "5Y"],
        index=2
    )

    df = add_indicators(data[selected_symbol])

    days = {
        "1M": 31,
        "3M": 92,
        "6M": 183,
        "1Y": 365,
        "5Y": 1826,
    }[period]

    latest_date = df["date"].max()
    cutoff = latest_date - pd.Timedelta(days=days)

    chart_df = df[df["date"] >= cutoff].copy()

    if chart_df.empty:
        st.warning("No observations available for this period.")
    else:

        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.06,
            row_heights=[0.72, 0.28],
        )

        fig.add_trace(
            go.Candlestick(
                x=chart_df["date"],
                open=chart_df["open"],
                high=chart_df["high"],
                low=chart_df["low"],
                close=chart_df["close"],
                name="Price",
                increasing_line_color="#16C784",
                decreasing_line_color="#EA3943",
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=chart_df["date"],
                y=chart_df["ema_20"],
                name="EMA 20",
                line=dict(color="#42A5FF", width=1.4),
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=chart_df["date"],
                y=chart_df["ema_50"],
                name="EMA 50",
                line=dict(color="#F5B942", width=1.4),
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Bar(
                x=chart_df["date"],
                y=chart_df["volume"],
                name="Volume",
                marker_color="#52799D",
                opacity=0.65,
            ),
            row=2,
            col=1,
        )

        fig.update_layout(
            height=570,
            template="plotly_dark",
            paper_bgcolor="#101927",
            plot_bgcolor="#101927",
            font=dict(
                family="IBM Plex Mono, monospace",
                color="#DCE6F2",
                size=11,
            ),
            margin=dict(l=15, r=15, t=35, b=15),
            xaxis_rangeslider_visible=False,
            legend=dict(
                orientation="h",
                y=1.04,
                x=0,
            ),
            hovermode="x unified",
        )

        fig.update_xaxes(
            gridcolor="#263449",
            showgrid=True,
        )

        fig.update_yaxes(
            gridcolor="#263449",
            showgrid=True,
        )

        st.plotly_chart(
    fig,
    width="stretch"
)

        latest = chart_df.iloc[-1]

        rsi_value = latest["rsi_14"]

        st.caption(
            f"Latest RSI (14): "
            f"{rsi_value:.2f}"
            if pd.notna(rsi_value)
            else "Latest RSI (14): unavailable"
        )

    st.divider()

    st.subheader("Instrument Watchlist")

    rows = []

    for symbol in SYMBOLS:

        if symbol not in data:
            rows.append({
                "Instrument": symbol,
                "Latest Date": "Unavailable",
                "Close": None,
                "Daily Change %": None,
                "Volume": None,
                "Status": "DATA MISSING",
            })
            continue

        summary = get_instrument_summary(data[symbol])

        rows.append({
            "Instrument": symbol,
            "Latest Date": summary["date"].strftime("%d %b %Y"),
            "Close": summary["close"],
            "Daily Change %": summary["change_pct"],
            "Volume": summary["volume"],
            "Status": "HISTORICAL DATA",
        })

    watchlist_df = pd.DataFrame(rows)

    st.dataframe(
    watchlist_df,
    width="stretch",
        hide_index=True,
        column_config={
            "Close": st.column_config.NumberColumn(
                "Close",
                format="%.2f"
            ),
            "Daily Change %": st.column_config.NumberColumn(
                "Daily Change %",
                format="%.2f%%"
            ),
            "Volume": st.column_config.NumberColumn(
                "Volume",
                format="localized"
            ),
        }
    )

    st.divider()

    st.subheader("Data Quality and Availability")

    q1, q2, q3 = st.columns(3)

    q1.metric(
        "Loaded instruments",
        len(data)
    )

    q2.metric(
        "Missing instruments",
        len(errors)
    )

    dates = [
        df["date"].max()
        for df in data.values()
        if not df.empty
    ]

    latest_common = min(dates) if dates else None

    q3.metric(
        "Latest available date",
        latest_common.strftime("%d %b %Y")
        if latest_common is not None
        else "Unavailable"
    )

    if errors:

        with st.expander("Dataset loading errors"):
            for symbol, error in errors.items():
                st.error(f"{symbol}: {error}")

    st.info(
        "DATA CLASSIFICATION: HISTORICAL DAILY CSV DATA. "
        "The displayed values are not live quotes. "
        "Upstox live-feed integration will be added separately."
    )
