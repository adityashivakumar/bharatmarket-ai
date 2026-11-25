from dashboard.analysis import render_analysis
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from textwrap import dedent
from dashboard.live_feed import render_live_feed
import streamlit as st

from dashboard.theme import inject_theme
from dashboard.overview import render_overview

# ==========================================
# APPLICATION CONFIGURATION
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent
IST = ZoneInfo("Asia/Kolkata")

st.set_page_config(
    page_title="BharatMarket AI | Intelligence Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()

# ==========================================
# NAVIGATION
# ==========================================

NAVIGATION = [
    "Overview",
    "Market Analysis",
    "Live Market Feed",
    "Trading Signals",
    "AI Forecasting",
    "Backtesting",
    "Risk Analytics",
    "Data Explorer",
    "System Monitor",
]

# ==========================================
# SIDEBAR
# ==========================================

with st.sidebar:

    st.markdown(
        """
        <div style="padding:8px 0 20px 0">
            <div style="font-size:25px">📈</div>
            <div class="terminal-brand">BHARATMARKET</div>
            <div class="terminal-subtitle">
                AI INTELLIGENCE TERMINAL
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    st.markdown(
        '<div class="section-label">WORKSPACE</div>',
        unsafe_allow_html=True,
    )

    selected_page = st.radio(
        "Terminal Navigation",
        NAVIGATION,
        index=0,
        key="terminal_navigation",
        label_visibility="collapsed",
    )

    st.markdown("---")

    st.markdown(
        """
        <div class="section-label">PLATFORM INFORMATION</div>
        <div style="font-size:12px;line-height:2">
            <div>PROJECT <b>BM-AI-001</b></div>
            <div>MARKET <b>NSE INDIA</b></div>
            <div>MODE <b>PAPER TRADING</b></div>
            <div>VERSION <b>1.0.0</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.caption("BHARATMARKET AI · ACADEMIC PROJECT")

# ==========================================
# TERMINAL HEADER
# ==========================================

now = datetime.now(IST)

header_html = dedent(f"""
<div class="terminal-header">
    <div>
        <div class="terminal-subtitle">
            INDIA EQUITY MARKET
        </div>
        <div style="font-size:17px;font-weight:700">
            BHARATMARKET AI
        </div>
    </div>
    <div style="text-align:right">
        <div class="status-offline">
            ● HISTORICAL DATA MODE
        </div>
        <div class="terminal-subtitle">
            {now.strftime("%d %b %Y")} |
            {now.strftime("%H:%M:%S")} IST
        </div>
    </div>
</div>
""")

st.markdown(
    header_html,
    unsafe_allow_html=True,
)

# ==========================================
# PAGE ROUTING
# ==========================================


if selected_page == "Overview":

    render_overview(PROJECT_DIR)

elif selected_page == "Market Analysis":

    render_analysis(PROJECT_DIR)

elif selected_page == "Live Market Feed":

    render_live_feed(PROJECT_DIR)

else:

    descriptions = {
        "Live Market Feed":
            "Upstox V3 WebSocket streaming and market updates.",
        "Trading Signals":
            "AI-assisted trading signals and risk/reward.",
        "AI Forecasting":
            "Machine-learning forecasts and model evaluation.",
        "Backtesting":
            "Strategy performance and benchmark comparison.",
        "Risk Analytics":
            "Portfolio risk, VaR, CVaR and drawdown.",
        "Data Explorer":
            "Historical datasets and feature data.",
        "System Monitor":
            "Model registry and pipeline diagnostics.",
    }

    st.title(selected_page)
    st.caption(descriptions.get(selected_page, ""))

    st.info(
        "This module will be connected to existing "
        "BharatMarket AI datasets and model artifacts "
        "in upcoming development stages."
    )


# ==========================================
# FOOTER
# ==========================================

st.markdown(
    '<div class="terminal-divider"></div>',
    unsafe_allow_html=True,
)

st.caption(
    "BHARATMARKET AI | FINANCIAL INTELLIGENCE | "
    "ACADEMIC PROJECT | PAPER TRADING ONLY"
)
