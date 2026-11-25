
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from plotly.subplots import make_subplots

from dashboard.market_data import (
    SYMBOLS,
    load_instrument,
)


def calculate_technical_indicators(df):

    df = df.copy().sort_values("date")

    close = df["close"]
    high = df["high"]
    low = df["low"]

    # Moving averages
    for period in [9, 21, 50, 200]:

        df[f"ema_{period}"] = close.ewm(
            span=period,
            adjust=False
        ).mean()

    # RSI 14 - Wilder smoothing
    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1/14,
        adjust=False,
        min_periods=14
    ).mean()

    avg_loss = loss.ewm(
        alpha=1/14,
        adjust=False,
        min_periods=14
    ).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    df["rsi_14"] = 100 - (100 / (1 + rs))

    # Handle persistent upward/downward series
    df.loc[
        (avg_loss == 0) & (avg_gain > 0),
        "rsi_14"
    ] = 100

    df.loc[
        (avg_gain == 0) & (avg_loss > 0),
        "rsi_14"
    ] = 0

    # MACD
    ema_12 = close.ewm(
        span=12, adjust=False
    ).mean()

    ema_26 = close.ewm(
        span=26, adjust=False
    ).mean()

    df["macd"] = ema_12 - ema_26

    df["macd_signal"] = df["macd"].ewm(
        span=9, adjust=False
    ).mean()

    df["macd_histogram"] = (
        df["macd"] - df["macd_signal"]
    )

    # Bollinger Bands
    middle = close.rolling(20).mean()
    std = close.rolling(20).std()

    df["bb_middle"] = middle
    df["bb_upper"] = middle + (2 * std)
    df["bb_lower"] = middle - (2 * std)

    df["bb_width"] = (
        (df["bb_upper"] - df["bb_lower"])
        / df["bb_middle"].replace(0, np.nan)
    ) * 100

    # ATR 14
    previous_close = close.shift(1)

    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1
    ).max(axis=1)

    df["atr_14"] = true_range.ewm(
        alpha=1/14,
        adjust=False,
        min_periods=14
    ).mean()

    df["atr_percentage"] = (
        df["atr_14"] / close.replace(0, np.nan)
    ) * 100

    # Previous 20-session support/resistance
    df["support_20"] = (
        low.shift(1).rolling(20).min()
    )

    df["resistance_20"] = (
        high.shift(1).rolling(20).max()
    )

    return df


def get_technical_summary(df):

    latest = df.iloc[-1]

    price = latest["close"]
    ema21 = latest["ema_21"]
    ema50 = latest["ema_50"]
    ema200 = latest["ema_200"]
    rsi = latest["rsi_14"]

    if price > ema21 > ema50:
        trend = "BULLISH"
    elif price < ema21 < ema50:
        trend = "BEARISH"
    else:
        trend = "MIXED"

    if pd.isna(rsi):
        momentum = "UNAVAILABLE"
    elif rsi >= 70:
        momentum = "OVERBOUGHT"
    elif rsi <= 30:
        momentum = "OVERSOLD"
    elif rsi > 50:
        momentum = "POSITIVE"
    else:
        momentum = "NEGATIVE"

    if latest["macd"] > latest["macd_signal"]:
        macd_status = "BULLISH"
    else:
        macd_status = "BEARISH"

    if pd.notna(ema200):
        long_term = (
            "ABOVE EMA 200"
            if price > ema200
            else "BELOW EMA 200"
        )
    else:
        long_term = "INSUFFICIENT HISTORY"

    return {
        "trend": trend,
        "momentum": momentum,
        "macd": macd_status,
        "long_term": long_term,
        "rsi": rsi,
        "atr": latest["atr_14"],
        "atr_percentage": latest["atr_percentage"],
        "support": latest["support_20"],
        "resistance": latest["resistance_20"],
    }


def render_analysis(project_dir):

    st.title("Market Analysis Terminal")

    st.caption(
        "Technical analysis | Trend | Momentum | Volatility | "
        "Support and resistance"
    )

    col1, col2 = st.columns([1, 1])

    with col1:

        symbol = st.selectbox(
            "Select instrument",
            SYMBOLS,
            key="analysis_symbol"
        )

    with col2:

        period = st.selectbox(
            "Historical period",
            ["1M", "3M", "6M", "1Y", "5Y"],
            index=2,
            key="analysis_period"
        )

    try:

        df = load_instrument(project_dir, symbol)

        if len(df) < 30:
            st.warning(
                "At least 30 observations are recommended "
                "for technical analysis."
            )

        df = calculate_technical_indicators(df)

    except Exception as exc:

        st.error(f"Could not load analysis data: {exc}")
        return

    period_days = {
        "1M": 31,
        "3M": 92,
        "6M": 183,
        "1Y": 365,
        "5Y": 1826,
    }

    cutoff = (
        df["date"].max()
        - pd.Timedelta(days=period_days[period])
    )

    chart_df = df[df["date"] >= cutoff].copy()

    if chart_df.empty:
        st.warning("No observations for selected period.")
        return

    latest = df.iloc[-1]
    summary = get_technical_summary(df)

    # ======================================
    # PRICE SNAPSHOT
    # ======================================

    st.markdown("### Instrument Snapshot")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Latest Close",
        f"{latest['close']:,.2f}"
    )

    c2.metric(
        "RSI 14",
        (
            f"{summary['rsi']:.2f}"
            if pd.notna(summary["rsi"])
            else "N/A"
        )
    )

    c3.metric(
        "ATR 14",
        (
            f"{summary['atr']:,.2f}"
            if pd.notna(summary["atr"])
            else "N/A"
        )
    )

    c4.metric(
        "ATR %",
        (
            f"{summary['atr_percentage']:.2f}%"
            if pd.notna(summary["atr_percentage"])
            else "N/A"
        )
    )

    st.caption(
        "Latest available historical session: "
        + latest["date"].strftime("%d %B %Y")
    )

    # ======================================
    # TECHNICAL SUMMARY
    # ======================================

    st.markdown("### Technical Conditions")

    s1, s2, s3, s4 = st.columns(4)

    s1.metric("Short-term trend", summary["trend"])
    s2.metric("Momentum", summary["momentum"])
    s3.metric("MACD condition", summary["macd"])
    s4.metric("Long-term trend", summary["long_term"])

    # ======================================
    # INDICATOR SELECTION
    # ======================================

    st.markdown("### Chart Configuration")

    ema_options = st.multiselect(
        "Moving averages",
        [9, 21, 50, 200],
        default=[21, 50]
    )

    show_bollinger = st.checkbox(
        "Show Bollinger Bands",
        value=True
    )

    show_support = st.checkbox(
        "Show 20-session support/resistance",
        value=True
    )

    # ======================================
    # FOUR PANEL CHART
    # ======================================

    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.035,
        row_heights=[0.50, 0.16, 0.17, 0.17],
        subplot_titles=[
            "PRICE AND TREND",
            "VOLUME",
            "RSI 14",
            "MACD",
        ]
    )

    # Candles
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
        col=1
    )

    # EMAs
    ema_colors = {
        9: "#FFFFFF",
        21: "#42A5FF",
        50: "#F5B942",
        200: "#C084FC",
    }

    for ema in ema_options:

        fig.add_trace(
            go.Scatter(
                x=chart_df["date"],
                y=chart_df[f"ema_{ema}"],
                name=f"EMA {ema}",
                line=dict(
                    color=ema_colors[ema],
                    width=1.4
                )
            ),
            row=1,
            col=1
        )

    # Bollinger Bands
    if show_bollinger:

        fig.add_trace(
            go.Scatter(
                x=chart_df["date"],
                y=chart_df["bb_upper"],
                name="BB Upper",
                line=dict(
                    color="#8B9BB4",
                    width=1,
                    dash="dot"
                )
            ),
            row=1,
            col=1
        )

        fig.add_trace(
            go.Scatter(
                x=chart_df["date"],
                y=chart_df["bb_lower"],
                name="BB Lower",
                line=dict(
                    color="#8B9BB4",
                    width=1,
                    dash="dot"
                )
            ),
            row=1,
            col=1
        )

    # Support and resistance
    if show_support:

        if pd.notna(summary["support"]):

            fig.add_hline(
                y=summary["support"],
                line_dash="dash",
                line_color="#16C784",
                annotation_text="20S SUPPORT",
                row=1,
                col=1
            )

        if pd.notna(summary["resistance"]):

            fig.add_hline(
                y=summary["resistance"],
                line_dash="dash",
                line_color="#EA3943",
                annotation_text="20S RESISTANCE",
                row=1,
                col=1
            )

    # Volume
    fig.add_trace(
        go.Bar(
            x=chart_df["date"],
            y=chart_df["volume"],
            name="Volume",
            marker_color="#52799D",
            opacity=0.7
        ),
        row=2,
        col=1
    )

    # RSI
    fig.add_trace(
        go.Scatter(
            x=chart_df["date"],
            y=chart_df["rsi_14"],
            name="RSI 14",
            line=dict(color="#C084FC", width=1.5)
        ),
        row=3,
        col=1
    )

    fig.add_hline(
        y=70,
        line_dash="dash",
        line_color="#EA3943",
        row=3,
        col=1
    )

    fig.add_hline(
        y=30,
        line_dash="dash",
        line_color="#16C784",
        row=3,
        col=1
    )

    # MACD
    fig.add_trace(
        go.Scatter(
            x=chart_df["date"],
            y=chart_df["macd"],
            name="MACD",
            line=dict(color="#42A5FF", width=1.4)
        ),
        row=4,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=chart_df["date"],
            y=chart_df["macd_signal"],
            name="Signal",
            line=dict(color="#F5B942", width=1.4)
        ),
        row=4,
        col=1
    )

    fig.add_trace(
        go.Bar(
            x=chart_df["date"],
            y=chart_df["macd_histogram"],
            name="MACD Histogram",
            marker_color="#52799D"
        ),
        row=4,
        col=1
    )

    fig.update_layout(
        height=1000,
        template="plotly_dark",
        paper_bgcolor="#101927",
        plot_bgcolor="#101927",
        font=dict(
            family="IBM Plex Mono, monospace",
            color="#DCE6F2",
            size=10
        ),
        margin=dict(l=20, r=20, t=60, b=25),
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            y=1.02,
            x=0
        )
    )

    fig.update_xaxes(
        gridcolor="#263449",
        showgrid=True
    )

    fig.update_yaxes(
        gridcolor="#263449",
        showgrid=True
    )

    fig.update_yaxes(
        range=[0, 100],
        row=3,
        col=1
    )

    st.plotly_chart(
        fig,
        width="stretch"
    )

    # ======================================
    # SUPPORT AND RESISTANCE TABLE
    # ======================================

    st.markdown("### Key Technical Levels")

    levels = pd.DataFrame([
        {
            "Level": "Latest Close",
            "Price": latest["close"]
        },
        {
            "Level": "20-Session Support",
            "Price": summary["support"]
        },
        {
            "Level": "20-Session Resistance",
            "Price": summary["resistance"]
        },
        {
            "Level": "EMA 21",
            "Price": latest["ema_21"]
        },
        {
            "Level": "EMA 50",
            "Price": latest["ema_50"]
        },
        {
            "Level": "EMA 200",
            "Price": latest["ema_200"]
        },
    ])

    st.dataframe(
        levels,
        width="stretch",
        hide_index=True,
        column_config={
            "Price": st.column_config.NumberColumn(
                "Price",
                format="%.2f"
            )
        }
    )

    st.info(
        "Technical indicators are descriptive calculations "
        "from historical daily data. Support and resistance "
        "are rolling 20-session reference levels, not guaranteed "
        "price barriers or trading recommendations."
    )
