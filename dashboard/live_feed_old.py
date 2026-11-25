
"""
BharatMarket AI
Live Intraday Analytics Dashboard

Streamlit 1.67+
Uses the existing Upstox service, candle pipeline
and indicator engine.
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from plotly.subplots import make_subplots

from upstox_integration.live.live_feed_service import (
    get_service,
    INSTRUMENTS,
)

from upstox_integration.live.intraday_pipeline import (
    load_ticks,
    prepare_live_updates,
    build_candles,
    mark_candle_completion,
)

from upstox_integration.live.indicator_engine import (
    calculate_indicators,
)


# ==========================================================
# CONFIGURATION
# ==========================================================

TIMEFRAMES = {
    "1 Minute": "1min",
    "5 Minutes": "5min",
    "15 Minutes": "15min",
}

IST = "Asia/Kolkata"


# ==========================================================
# HELPERS
# ==========================================================

def format_price(value):

    if pd.isna(value):
        return "—"

    return f"{value:,.2f}"


def get_feed_status(status):

    if not status["connected"]:
        return "DISCONNECTED", "off"

    last_message = status.get("last_message_time")

    if not last_message:
        return "CONNECTED · WAITING FOR DATA", "waiting"

    try:
        received = pd.Timestamp(last_message)

        age = (
            pd.Timestamp.now(tz=IST) - received
        ).total_seconds()

    except Exception:
        return "CONNECTED · WAITING FOR DATA", "waiting"

    if age > 15:
        return "CONNECTED · DATA STALE", "stale"

    if status.get("update_count", 0) > 0:
        return "LIVE UPDATES RECEIVED", "live"

    return "CONNECTED · SNAPSHOT ONLY", "snapshot"


def build_intraday_dataset(service, timeframe):

    """
    Read normalized ticks and generate candles and indicators.

    Only genuine feed_update observations are used.
    """

    tick_file = Path(service.tick_file)

    if not tick_file.exists():
        return pd.DataFrame(), pd.DataFrame()

    try:

        ticks = load_ticks(tick_file)

        updates = prepare_live_updates(ticks)

        if updates.empty:
            return pd.DataFrame(), pd.DataFrame()

        candles = build_candles(
            updates,
            timeframe
        )

        if candles.empty:
            return pd.DataFrame(), pd.DataFrame()

        candles = mark_candle_completion(
            candles
        )

        indicators = calculate_indicators(
            candles
        )

        return candles, indicators

    except (
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        PermissionError,
        ValueError,
    ) as error:

        st.warning(
            f"Could not process the current tick file: {error}"
        )

        return pd.DataFrame(), pd.DataFrame()


# ==========================================================
# PRICE AND INDICATOR CHART
# ==========================================================

def create_intraday_chart(df, symbol, timeframe):

    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.035,
        row_heights=[
            0.53,
            0.15,
            0.16,
            0.16,
        ],
        subplot_titles=[
            "PRICE ACTION · EMA · BOLLINGER BANDS",
            "VOLUME",
            "RSI 14",
            "MACD",
        ],
    )

    x = df["candle_start"]

    # --------------------------------------------------
    # CANDLESTICKS
    # --------------------------------------------------

    fig.add_trace(
        go.Candlestick(
            x=x,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="OHLC",
            increasing_line_color="#00C087",
            decreasing_line_color="#FF5263",
        ),
        row=1,
        col=1,
    )

    # --------------------------------------------------
    # EMA LINES
    # --------------------------------------------------

    ema_settings = [
        ("ema_9", "#38BDF8", "EMA 9"),
        ("ema_21", "#F59E0B", "EMA 21"),
        ("ema_50", "#A78BFA", "EMA 50"),
    ]

    for column, color, name in ema_settings:

        if column in df.columns:

            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=df[column],
                    name=name,
                    mode="lines",
                    line=dict(
                        color=color,
                        width=1.5,
                    ),
                    connectgaps=False,
                ),
                row=1,
                col=1,
            )

    # --------------------------------------------------
    # BOLLINGER BANDS
    # --------------------------------------------------

    if {"bb_upper", "bb_lower"}.issubset(df.columns):

        fig.add_trace(
            go.Scatter(
                x=x,
                y=df["bb_upper"],
                name="BB Upper",
                line=dict(
                    color="rgba(148,163,184,0.55)",
                    width=1,
                    dash="dot",
                ),
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=x,
                y=df["bb_lower"],
                name="BB Lower",
                line=dict(
                    color="rgba(148,163,184,0.55)",
                    width=1,
                    dash="dot",
                ),
                fill="tonexty",
                fillcolor="rgba(148,163,184,0.06)",
            ),
            row=1,
            col=1,
        )

    # --------------------------------------------------
    # VWAP
    # --------------------------------------------------

    if "vwap" in df.columns and df["vwap"].notna().any():

        fig.add_trace(
            go.Scatter(
                x=x,
                y=df["vwap"],
                name="VWAP",
                line=dict(
                    color="#F472B6",
                    width=1.8,
                ),
                connectgaps=False,
            ),
            row=1,
            col=1,
        )

    # --------------------------------------------------
    # VOLUME
    # --------------------------------------------------

    volume = pd.to_numeric(
        df["volume"],
        errors="coerce"
    )

    if volume.notna().any():

        volume_colors = [
            "#00C087" if close >= open_price
            else "#FF5263"
            for close, open_price
            in zip(df["close"], df["open"])
        ]

        fig.add_trace(
            go.Bar(
                x=x,
                y=volume,
                name="Observed Volume",
                marker_color=volume_colors,
                opacity=0.75,
            ),
            row=2,
            col=1,
        )

    # --------------------------------------------------
    # RSI
    # --------------------------------------------------

    if "rsi_14" in df.columns:

        fig.add_trace(
            go.Scatter(
                x=x,
                y=df["rsi_14"],
                name="RSI 14",
                line=dict(
                    color="#38BDF8",
                    width=1.7,
                ),
            ),
            row=3,
            col=1,
        )

        fig.add_hline(
            y=70,
            line_dash="dash",
            line_color="#FF5263",
            opacity=0.6,
            row=3,
            col=1,
        )

        fig.add_hline(
            y=30,
            line_dash="dash",
            line_color="#00C087",
            opacity=0.6,
            row=3,
            col=1,
        )

    # --------------------------------------------------
    # MACD
    # --------------------------------------------------

    if "macd" in df.columns:

        fig.add_trace(
            go.Scatter(
                x=x,
                y=df["macd"],
                name="MACD",
                line=dict(
                    color="#38BDF8",
                    width=1.5,
                ),
            ),
            row=4,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=x,
                y=df["macd_signal"],
                name="Signal",
                line=dict(
                    color="#F59E0B",
                    width=1.5,
                ),
            ),
            row=4,
            col=1,
        )

        histogram_colors = [
            "#00C087" if value >= 0
            else "#FF5263"
            for value in df["macd_histogram"].fillna(0)
        ]

        fig.add_trace(
            go.Bar(
                x=x,
                y=df["macd_histogram"],
                name="MACD Histogram",
                marker_color=histogram_colors,
                opacity=0.55,
            ),
            row=4,
            col=1,
        )

    # --------------------------------------------------
    # LAYOUT
    # --------------------------------------------------

    fig.update_layout(
        template="plotly_dark",
        height=850,
        title=dict(
            text=f"{symbol} · {timeframe} INTRADAY ANALYSIS",
            x=0.02,
            font=dict(size=17),
        ),
        paper_bgcolor="#0B1420",
        plot_bgcolor="#0B1420",
        font=dict(
            family="Inter, sans-serif",
            color="#D8E1EA",
            size=11,
        ),
        margin=dict(
            l=45,
            r=25,
            t=80,
            b=35,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,0.12)",
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,0.10)",
    )

    fig.update_yaxes(
        range=[0, 100],
        row=3,
        col=1,
    )

    return fig


# ==========================================================
# TREND INTERPRETATION
# ==========================================================

def get_trend(row):

    ema9 = row.get("ema_9")
    ema21 = row.get("ema_21")
    ema50 = row.get("ema_50")

    if pd.isna(ema9) or pd.isna(ema21) or pd.isna(ema50):
        return "INSUFFICIENT HISTORY"

    if ema9 > ema21 > ema50:
        return "BULLISH"

    if ema9 < ema21 < ema50:
        return "BEARISH"

    return "MIXED / SIDEWAYS"


def render_indicator_metrics(row):

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "RSI 14",
        format_price(row.get("rsi_14")),
    )

    col2.metric(
        "MACD",
        format_price(row.get("macd")),
    )

    col3.metric(
        "ATR 14",
        format_price(row.get("atr_14")),
    )

    col4.metric(
        "ATR %",
        (
            f"{row['atr_percentage']:.2f}%"
            if pd.notna(row.get("atr_percentage"))
            else "—"
        ),
    )


# ==========================================================
# LIVE ANALYTICS FRAGMENT
# ==========================================================

@st.fragment(run_every=2)
def render_live_analytics(
    service,
    symbol,
    timeframe,
):

    snapshot = service.get_snapshot()

    status = snapshot["status"]

    status_label, status_type = get_feed_status(
        status
    )

    status_colors = {
        "live": "#00D18F",
        "snapshot": "#F0B64D",
        "waiting": "#65A8FF",
        "stale": "#FF9D57",
        "off": "#FF5D68",
    }

    color = status_colors[status_type]

    st.markdown(
        f"""
        <div style="
            background:#101C2B;
            border:1px solid #26384B;
            border-radius:8px;
            padding:12px 15px;
            margin-bottom:15px;
            color:{color};
            font-weight:700;
            letter-spacing:0.7px;
            font-size:12px;
        ">
            ● {status_label}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------
    # FEED METRICS
    # --------------------------------------------------

    latest_data = snapshot["data"]

    selected_data = latest_data[
        latest_data["symbol"] == symbol
    ] if not latest_data.empty else pd.DataFrame()

    col1, col2, col3, col4 = st.columns(4)

    current_price = None
    price_change = None

    if not selected_data.empty:

        selected_row = selected_data.iloc[0]

        current_price = selected_row["ltp"]
        price_change = selected_row["change_pct"]

    col1.metric(
        "LATEST LTP",
        (
            f"₹{current_price:,.2f}"
            if pd.notna(current_price)
            else "—"
        ),
        (
            f"{price_change:+.2f}%"
            if pd.notna(price_change)
            else None
        ),
    )

    col2.metric(
        "FEED MESSAGES",
        status["message_count"],
    )

    col3.metric(
        "LIVE UPDATES",
        status["update_count"],
    )

    col4.metric(
        "CONNECTED",
        "YES" if status["connected"] else "NO",
    )

    # --------------------------------------------------
    # GENERATE INTRADAY DATA
    # --------------------------------------------------

    candles, indicators = build_intraday_dataset(
        service,
        timeframe,
    )

    if candles.empty or indicators.empty:

        st.warning(
            "No genuine intraday candles are available yet. "
            "The system will display the chart after receiving "
            "valid feed updates during market hours."
        )

        if not selected_data.empty:

            st.caption(
                "The latest available instrument observation "
                "is displayed in the LTP card above. It is not "
                "being converted into a historical candle."
            )

        if status.get("last_error"):
            st.error(status["last_error"])

        return

    symbol_candles = candles[
        candles["symbol"] == symbol
    ].copy()

    symbol_indicators = indicators[
        indicators["symbol"] == symbol
    ].copy()

    if symbol_candles.empty or symbol_indicators.empty:

        st.info(
            f"No intraday updates are available for {symbol} yet."
        )

        return

    # --------------------------------------------------
    # COMPLETION STATUS
    # --------------------------------------------------

    last_candle = symbol_indicators.iloc[-1]

    complete_count = int(
        symbol_candles["is_complete"].sum()
    )

    forming_count = int(
        (~symbol_candles["is_complete"]).sum()
    )

    st.markdown("### CANDLE STATUS")

    status_col1, status_col2, status_col3 = st.columns(3)

    status_col1.metric(
        "TOTAL CANDLES",
        len(symbol_candles),
    )

    status_col2.metric(
        "COMPLETED",
        complete_count,
    )

    status_col3.metric(
        "FORMING",
        forming_count,
    )

    # --------------------------------------------------
    # TREND AND INDICATORS
    # --------------------------------------------------

    st.markdown("### MARKET INDICATORS")

    trend = get_trend(last_candle)

    st.metric(
        "EMA TREND",
        trend,
    )

    render_indicator_metrics(
        last_candle
    )

    vwap = last_candle.get("vwap")

    if pd.notna(vwap):

        st.metric(
            "SESSION VWAP",
            f"₹{vwap:,.2f}",
        )

    else:

        st.caption(
            "VWAP unavailable: valid volume observations "
            "are not available for this instrument."
        )

    # --------------------------------------------------
    # CHART
    # --------------------------------------------------

    st.markdown("### INTRADAY PRICE ANALYSIS")

    fig = create_intraday_chart(
        symbol_indicators,
        symbol,
        timeframe,
    )

    st.plotly_chart(
        fig,
        width="stretch",
        config={
            "displaylogo": False,
            "scrollZoom": True,
            "displayModeBar": True,
        },
    )

    st.caption(
        "Candles are constructed from received feed updates. "
        "Volume represents observed cumulative-volume increments "
        "and may not equal complete exchange candle volume."
    )

    # --------------------------------------------------
    # LATEST INDICATOR TABLE
    # --------------------------------------------------

    st.markdown("### LATEST INDICATOR VALUES")

    indicator_columns = [
        "candle_start",
        "open",
        "high",
        "low",
        "close",
        "ema_9",
        "ema_21",
        "ema_50",
        "rsi_14",
        "macd",
        "macd_signal",
        "atr_14",
        "vwap",
        "is_complete",
    ]

    available_columns = [
        column
        for column in indicator_columns
        if column in symbol_indicators.columns
    ]

    st.dataframe(
        symbol_indicators[
            available_columns
        ].tail(15),
        width="stretch",
        hide_index=True,
    )


# ==========================================================
# MAIN PAGE
# ==========================================================

def render_live_feed(project_dir=None):

    service = get_service()

    st.markdown(
        """
        <div style="margin-bottom:15px;">
            <div style="
                font-size:26px;
                font-weight:800;
                letter-spacing:-0.7px;
            ">
                LIVE INTRADAY ANALYTICS
            </div>
            <div style="
                color:#91A4B7;
                font-size:12px;
                letter-spacing:1.3px;
            ">
                BHARATMARKET AI · UPSTOX V3
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------
    # CONNECTION CONTROLS
    # --------------------------------------------------

    st.markdown("### WEBSOCKET CONTROL")

    col1, col2, col3 = st.columns(
        [1, 1, 2]
    )

    with col1:

        if st.button(
            "▶ START FEED",
            width="stretch",
            disabled=service.started,
        ):

            try:

                result = service.start()

                st.success(
                    f"Feed start requested: {result['status']}"
                )

            except Exception as error:

                st.error(
                    f"Could not start feed: {error}"
                )

    with col2:

        if st.button(
            "■ STOP FEED",
            width="stretch",
            disabled=not service.started,
        ):

            service.stop()

            st.warning(
                "Disconnect requested."
            )

    with col3:

        st.caption(
            "Persistent WebSocket · Automatic reconnection · "
            "Two-second dashboard refresh"
        )

    st.divider()

    # --------------------------------------------------
    # INSTRUMENT AND TIMEFRAME SELECTORS
    # --------------------------------------------------

    st.markdown("### ANALYSIS CONFIGURATION")

    selector_col1, selector_col2 = st.columns(2)

    with selector_col1:

        symbol = st.selectbox(
            "SELECT INSTRUMENT",
            options=list(INSTRUMENTS.keys()),
            index=0,
            key="live_analytics_symbol",
        )

    with selector_col2:

        timeframe_label = st.selectbox(
            "SELECT TIMEFRAME",
            options=list(TIMEFRAMES.keys()),
            index=1,
            key="live_analytics_timeframe",
        )

    timeframe = TIMEFRAMES[
        timeframe_label
    ]

    st.divider()

    # --------------------------------------------------
    # LIVE ANALYTICS
    # --------------------------------------------------

    render_live_analytics(
        service,
        symbol,
        timeframe,
    )
