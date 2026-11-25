from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from textwrap import dedent

import streamlit as st

from dashboard.analysis import render_analysis
from dashboard.live_feed import render_live_feed
from dashboard.theme import inject_theme
from dashboard.overview import render_overview

PROJECT_DIR = Path(__file__).resolve().parent
IST = ZoneInfo("Asia/Kolkata")

st.set_page_config(
    page_title="BharatMarket AI | Market Intelligence Terminal",
    page_icon="B",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()

# Refined terminal skin layered over the existing theme.
st.markdown("""
<style>
:root {
    --bm-bg: #080d14;
    --bm-panel: #101925;
    --bm-panel-2: #131f2d;
    --bm-line: #263547;
    --bm-muted: #91a0b2;
    --bm-text: #e6edf5;
    --bm-green: #20c997;
    --bm-red: #f16b78;
    --bm-amber: #e6b45c;
    --bm-blue: #68a9e8;
}
.stApp { background: var(--bm-bg); color: var(--bm-text); }
[data-testid="stHeader"] { background: rgba(8,13,20,.92); }
[data-testid="stSidebar"] {
    background: #0b121c;
    border-right: 1px solid var(--bm-line);
}
[data-testid="stSidebar"] > div { padding-top: 1.2rem; }
.block-container { max-width: 1680px; padding-top: 1.2rem; padding-bottom: 2rem; }
h1, h2, h3 { letter-spacing: -.025em; }
h1 { font-size: 1.55rem !important; font-weight: 700 !important; }
h2 { font-size: 1.08rem !important; font-weight: 650 !important; }
h3 { font-size: .93rem !important; font-weight: 650 !important; }
p, label, .stCaption { color: var(--bm-muted); }
[data-testid="stMetric"] {
    background: linear-gradient(180deg, #121e2b, #0f1823);
    border: 1px solid var(--bm-line);
    border-radius: 8px;
    padding: 13px 15px;
}
[data-testid="stMetricLabel"] p {
    color: #9eacbc !important; font-size: .72rem !important;
    text-transform: uppercase; letter-spacing: .08em;
}
[data-testid="stMetricValue"] { font-size: 1.35rem !important; font-weight: 650; }
[data-testid="stMetricDelta"] { font-size: .78rem !important; }
.stButton button, [data-testid="stDownloadButton"] button {
    border-radius: 6px; border: 1px solid #34475d;
    background: #162536; color: #e6edf5;
}
.stButton button:hover { border-color: #68a9e8; color: white; }
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
    background: #101a27; border-color: #34475d;
}
hr { border-color: var(--bm-line); }
[data-testid="stDataFrame"], [data-testid="stTable"] {
    border: 1px solid var(--bm-line); border-radius: 7px; overflow: hidden;
}
.bm-brand { font-size: 1.02rem; font-weight: 800; letter-spacing: .11em; color: #f1f5f9; }
.bm-brand-sub { color: #8495a8; font-size: .62rem; letter-spacing: .17em; margin-top: 3px; }
.bm-eyebrow { color: #7f94aa; font-size: .65rem; letter-spacing: .15em; text-transform: uppercase; }
.bm-topbar {
    display:flex; justify-content:space-between; align-items:center; gap:16px;
    padding: 12px 16px; margin-bottom: 20px;
    background: #0e1722; border:1px solid #263547; border-radius:8px;
}
.bm-topbar-title { color:#e6edf5; font-size: .92rem; font-weight:700; letter-spacing:.06em; }
.bm-status { color:#e6b45c; font-size:.68rem; letter-spacing:.08em; font-weight:700; }
.bm-status-dot { color:#e6b45c; }
.bm-chip { color:#9cabbc; font-size:.68rem; letter-spacing:.04em; }
.bm-section {
    display:flex; align-items:center; justify-content:space-between;
    padding: 8px 0 10px; margin: 8px 0 12px;
    border-bottom:1px solid #263547;
}
.bm-section strong { font-size:.79rem; letter-spacing:.08em; color:#dce6f0; }
.bm-section span { font-size:.65rem; color:#7f91a5; letter-spacing:.08em; }
.bm-note {
    background:#111c29; border:1px solid #2b3d51; border-left:3px solid #68a9e8;
    padding:10px 13px; border-radius:5px; color:#aebdcd; font-size:.78rem;
}
</style>
""", unsafe_allow_html=True)

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

with st.sidebar:
    st.markdown("""
    <div style="padding:4px 0 18px">
      <div style="font-size:22px;color:#68a9e8;font-weight:800">B<span style="color:#20c997">/</span>M</div>
      <div class="bm-brand">BHARATMARKET</div>
      <div class="bm-brand-sub">MARKET INTELLIGENCE TERMINAL</div>
    </div>
    <div class="bm-eyebrow">Workspace</div>
    """, unsafe_allow_html=True)

    selected_page = st.radio(
        "Terminal Navigation", NAVIGATION, index=0,
        key="terminal_navigation", label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown('<div class="bm-eyebrow">Platform</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:.72rem;line-height:2.05;color:#9aabba">
      <div>PROJECT <b style="color:#dce6f0">BM-AI-001</b></div>
      <div>EXCHANGE <b style="color:#dce6f0">NSE INDIA</b></div>
      <div>EXECUTION <b style="color:#dce6f0">PAPER ONLY</b></div>
      <div>BUILD <b style="color:#dce6f0">1.1.0</b></div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    st.caption("CS3216 · TIME SERIES ANALYSIS & FORECASTING")

now = datetime.now(IST)
st.markdown(dedent(f"""
<div class="bm-topbar">
  <div>
    <div class="bm-eyebrow">India equity market / research workspace</div>
    <div class="bm-topbar-title">BHARATMARKET AI <span style="color:#60758b">/</span> TERMINAL</div>
  </div>
  <div style="text-align:right">
    <div class="bm-status"><span class="bm-status-dot">●</span> HISTORICAL DATA MODE</div>
    <div class="bm-chip">{now.strftime("%a, %d %b %Y")} &nbsp;·&nbsp; {now.strftime("%H:%M:%S")} IST</div>
  </div>
</div>
"""), unsafe_allow_html=True)

if selected_page == "Overview":
    render_overview(PROJECT_DIR)
elif selected_page == "Market Analysis":
    render_analysis(PROJECT_DIR)
elif selected_page == "Live Market Feed":
    render_live_feed(PROJECT_DIR)
else:
    descriptions = {
        "Trading Signals": "Signal research is intentionally disabled pending live-feed and candle validation.",
        "AI Forecasting": "Forecasting research and model evaluation workspace.",
        "Backtesting": "Historical strategy evaluation and benchmark comparison.",
        "Risk Analytics": "Portfolio risk, volatility, drawdown, VaR and CVaR.",
        "Data Explorer": "Historical datasets, schemas, coverage and quality checks.",
        "System Monitor": "Pipeline diagnostics, model registry and service health.",
    }
    st.markdown('<div class="bm-eyebrow">Workspace module</div>', unsafe_allow_html=True)
    st.title(selected_page)
    st.markdown(f'<div class="bm-note">{descriptions.get(selected_page, "")}</div>', unsafe_allow_html=True)
    if selected_page == "Trading Signals":
        st.warning("Trading signals are not available until market-data freshness and intraday candle validation have passed.")

st.markdown("---")
st.caption("BHARATMARKET AI  ·  HISTORICAL RESEARCH  ·  PAPER TRADING ONLY  ·  DATA MAY BE DELAYED")
