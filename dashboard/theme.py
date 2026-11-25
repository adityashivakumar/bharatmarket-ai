
import streamlit as st

BG = "#080D16"
PANEL = "#101927"
PANEL_LIGHT = "#152235"
BORDER = "#263449"
TEXT = "#E5EDF7"
MUTED = "#8797AB"
BLUE = "#42A5FF"
GREEN = "#16C784"
RED = "#EA3943"
AMBER = "#F5B942"


def inject_theme():

    st.markdown(
        """
        <style>

        @import url(
          'https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700;800&display=swap'
        );

        :root {
            --bg: #080D16;
            --panel: #101927;
            --panel-light: #152235;
            --border: #263449;
            --text: #E5EDF7;
            --muted: #8797AB;
            --blue: #42A5FF;
            --green: #16C784;
            --red: #EA3943;
            --amber: #F5B942;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .stApp {
            background: var(--bg);
            color: var(--text);
        }

        [data-testid="stHeader"] {
            background: rgba(8,13,22,0.96);
        }

        [data-testid="stSidebar"] {
            background: #0B1320;
            border-right: 1px solid var(--border);
        }

        [data-testid="stSidebar"] > div {
            padding-top: 1rem;
        }

        [data-testid="stSidebar"] p {
            color: var(--text);
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1800px;
        }

        h1, h2, h3 {
            color: var(--text) !important;
            letter-spacing: -0.4px;
        }

        .terminal-brand {
            font-family: 'IBM Plex Mono', monospace;
            font-weight: 700;
            font-size: 20px;
            color: #FFFFFF;
            letter-spacing: 1px;
        }

        .terminal-subtitle {
            color: var(--muted);
            font-family: 'IBM Plex Mono', monospace;
            font-size: 10px;
            letter-spacing: 1.8px;
        }

        .terminal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 12px 16px;
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 7px;
            margin-bottom: 22px;
        }

        .status-online {
            color: var(--green);
            font-family: 'IBM Plex Mono', monospace;
            font-size: 11px;
            font-weight: 600;
        }

        .status-offline {
            color: var(--amber);
            font-family: 'IBM Plex Mono', monospace;
            font-size: 11px;
            font-weight: 600;
        }

        .section-label {
            color: var(--muted);
            font-family: 'IBM Plex Mono', monospace;
            font-size: 11px;
            letter-spacing: 1.4px;
            margin-bottom: 10px;
        }

        .terminal-card {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 7px;
            padding: 16px;
            min-height: 112px;
        }

        .card-label {
            color: var(--muted);
            font-family: 'IBM Plex Mono', monospace;
            font-size: 11px;
            letter-spacing: 0.8px;
        }

        .card-value {
            color: var(--text);
            font-family: 'IBM Plex Mono', monospace;
            font-size: 25px;
            font-weight: 600;
            margin-top: 12px;
        }

        .card-note {
            color: var(--muted);
            font-size: 11px;
            margin-top: 6px;
        }

        .terminal-divider {
            border-top: 1px solid var(--border);
            margin: 20px 0;
        }

        .mono {
            font-family: 'IBM Plex Mono', monospace;
        }

        .stButton button {
            background: #14243A;
            color: var(--text);
            border: 1px solid var(--border);
            border-radius: 5px;
        }

        .stButton button:hover {
            border-color: var(--blue);
            color: var(--blue);
        }

        [data-testid="stMetric"] {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 7px;
            padding: 13px;
        }

        [data-testid="stMetricLabel"] {
            color: var(--muted);
        }

        [data-testid="stDataFrame"] {
            border: 1px solid var(--border);
            border-radius: 7px;
        }

        [data-testid="stAlert"] {
            border-radius: 6px;
        }

        footer {
            visibility: hidden;
        }

        </style>
        """,
        unsafe_allow_html=True
    )


def terminal_card(label, value, note="AWAITING DATA"):

    st.markdown(
        f"""
        <div class="terminal-card">
            <div class="card-label">{label}</div>
            <div class="card-value">{value}</div>
            <div class="card-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
