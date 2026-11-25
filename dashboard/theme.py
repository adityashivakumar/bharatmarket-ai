import streamlit as st

BG='#080D14'
PANEL='#101925'
BORDER='#263547'
TEXT='#E6EDF5'
MUTED='#91A0B2'
BLUE='#68A9E8'
GREEN='#20C997'
RED='#F16B78'
AMBER='#E6B45C'

def inject_theme():
 st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700;800&display=swap');
:root{--bg:#080d14;--panel:#101925;--panel2:#131f2d;--line:#263547;--text:#e6edf5;--muted:#91a0b2;--blue:#68a9e8;--green:#20c997;--red:#f16b78;--amber:#e6b45c}
html,body,[class*="css"]{font-family:Inter,sans-serif}.stApp{background:var(--bg);color:var(--text)}[data-testid="stHeader"]{background:rgba(8,13,20,.96)}
[data-testid="stSidebar"]{background:#0b121c;border-right:1px solid var(--line)}[data-testid="stSidebar"]>div{padding:1.05rem .85rem 1.4rem}.block-container{max-width:1800px;padding-top:1.05rem;padding-bottom:2rem}
h1,h2,h3{color:var(--text)!important;letter-spacing:-.025em}h1{font-size:1.42rem!important;font-weight:700!important}h2{font-size:1.04rem!important}h3{font-size:.88rem!important}p,label,[data-testid="stCaptionContainer"]{color:var(--muted)}
.bm-brand-lockup{display:flex;align-items:center;gap:10px;padding:4px 2px 18px}.bm-monogram{font:800 24px Inter,sans-serif;color:#e9f2fb;letter-spacing:-2px}.bm-monogram span{color:var(--green)}.bm-brand{color:#edf3f9;font-size:.88rem;font-weight:800;letter-spacing:.12em}.bm-brand-sub{color:#718398;font:500 .55rem 'DM Mono',monospace;letter-spacing:.12em;margin-top:4px}.bm-sidebar-rule{border-top:1px solid var(--line);margin:0 0 17px}.bm-nav-label{color:#65788e;font:500 .61rem 'DM Mono',monospace;letter-spacing:.14em;margin:17px 0 7px 5px}
[data-testid="stSidebar"] .stButton{margin:0 0 3px}[data-testid="stSidebar"] .stButton button{min-height:36px;justify-content:flex-start;text-align:left;border-radius:5px;border:1px solid transparent;background:transparent;color:#9eacbc;font-size:.78rem;padding:0 10px}[data-testid="stSidebar"] .stButton button:hover{background:#142235;border-color:#263a50;color:#edf4fb}[data-testid="stSidebar"] .stButton button[kind="primary"]{background:#16283c;border-color:#2a4968;color:#eaf3fb;box-shadow:inset 2px 0 0 var(--blue)}
.bm-sidebar-bottom{margin-top:24px;border-top:1px solid var(--line);padding-top:14px}.bm-sidebar-meta{display:grid;gap:9px}.bm-sidebar-meta div{display:flex;justify-content:space-between;gap:5px;font:500 .59rem 'DM Mono',monospace}.bm-sidebar-meta span{color:#6f8297}.bm-sidebar-meta b{color:#bdc9d6;font-weight:500}
.bm-topbar{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:12px 16px;margin-bottom:18px;background:#0e1722;border:1px solid var(--line);border-radius:7px}.bm-kicker{color:#8193a7;font:500 .61rem 'DM Mono',monospace;letter-spacing:.14em}.bm-kicker span,.bm-slash{color:#4e759b}.bm-topbar-title{margin-top:5px;font-size:.9rem;font-weight:750;letter-spacing:.07em;color:#e6edf5}.bm-topbar-right{text-align:right}.bm-session{color:var(--amber);font:500 .62rem 'DM Mono',monospace;letter-spacing:.08em}.bm-session i{display:inline-block;width:6px;height:6px;background:var(--amber);border-radius:50%;margin:0 5px 1px 0}.bm-clock{color:#8294a8;font:400 .62rem 'DM Mono',monospace;margin-top:5px}
.bm-eyebrow{color:#71869c;font:500 .61rem 'DM Mono',monospace;letter-spacing:.15em;text-transform:uppercase}.bm-section{display:flex;align-items:center;justify-content:space-between;gap:8px;border-bottom:1px solid var(--line);padding:8px 0 9px;margin:12px 0 11px}.bm-section strong{color:#dce6f0;font:600 .68rem 'DM Mono',monospace;letter-spacing:.08em}.bm-section span{color:#72869c;font:400 .58rem 'DM Mono',monospace;letter-spacing:.07em}.bm-note{background:#111c29;border:1px solid #2b3d51;border-left:3px solid var(--blue);border-radius:5px;padding:10px 12px;color:#aebdcd;font-size:.75rem}
.bm-footer{display:flex;justify-content:space-between;gap:12px;border-top:1px solid var(--line);margin-top:26px;padding-top:11px;color:#63778c;font:400 .56rem 'DM Mono',monospace;letter-spacing:.08em}
[data-testid="stMetric"]{background:linear-gradient(180deg,#121e2b,#0f1823);border:1px solid var(--line);border-radius:6px;padding:11px 13px;min-height:88px}[data-testid="stMetricLabel"] p{color:#91a0b2!important;font:500 .62rem 'DM Mono',monospace!important;letter-spacing:.06em;text-transform:uppercase}[data-testid="stMetricValue"]{color:#e6edf5;font:600 1.27rem 'DM Mono',monospace!important}[data-testid="stMetricDelta"]{font-size:.72rem!important}
.stButton button,[data-testid="stDownloadButton"] button{border-radius:5px;border:1px solid #34475d;background:#162536;color:#e6edf5}div[data-baseweb="select"]>div,div[data-baseweb="input"]>div{background:#101a27;border-color:#34475d}hr{border-color:var(--line)}[data-testid="stDataFrame"],[data-testid="stTable"]{border:1px solid var(--line);border-radius:6px;overflow:hidden}[data-testid="stAlert"]{border-radius:5px}[data-testid="stPlotlyChart"]{border:1px solid #202f40;border-radius:6px;overflow:hidden}[data-testid="stExpander"]{border-color:var(--line)}footer{visibility:hidden}
@media(max-width:700px){.bm-topbar{align-items:flex-start;flex-direction:column}.bm-topbar-right{text-align:left}.bm-footer{flex-direction:column}}
</style>''',unsafe_allow_html=True)

def terminal_card(label,value,note='AWAITING DATA'):
 st.markdown(f'''<div style="background:#101925;border:1px solid #263547;border-radius:6px;padding:14px;min-height:104px"><div style="color:#91a0b2;font:500 10px 'DM Mono',monospace;letter-spacing:1px">{label}</div><div style="color:#e6edf5;font:600 24px 'DM Mono',monospace;margin-top:12px">{value}</div><div style="color:#718398;font-size:10px;margin-top:5px">{note}</div></div>''',unsafe_allow_html=True)
