from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st
from dashboard.theme import inject_theme
from dashboard.overview import render_overview
from dashboard.analysis import render_analysis
from dashboard.live_feed import render_live_feed
from dashboard.terminal_pages import render_backtesting, render_risk_analytics, render_forecasting, render_data_explorer, render_system_monitor, render_signals
PROJECT_DIR=Path(__file__).resolve().parent
IST=ZoneInfo('Asia/Kolkata')
st.set_page_config(page_title='BharatMarket AI | Institutional Market Terminal',page_icon='B',layout='wide',initial_sidebar_state='expanded')
inject_theme()
NAV_GROUPS={'MARKET':['Overview','Market Analysis','Live Market Feed'],'RESEARCH':['AI Forecasting','Backtesting','Risk Analytics'],'DATA & OPERATIONS':['Data Explorer','System Monitor'],'EXECUTION':['Trading Signals']}
NAV_ITEMS=[x for group in NAV_GROUPS.values() for x in group]
with st.sidebar:
 st.markdown('''<div class="bm-brand-lockup"><div class="bm-monogram">B<span>/</span>M</div><div><div class="bm-brand">BHARATMARKET</div><div class="bm-brand-sub">MARKET INTELLIGENCE TERMINAL</div></div></div><div class="bm-sidebar-rule"></div>''',unsafe_allow_html=True)
 current=st.session_state.get('terminal_navigation','Overview')
 for group,items in NAV_GROUPS.items():
  st.markdown(f'<div class="bm-nav-label">{group}</div>',unsafe_allow_html=True)
  for item in items:
   active=current==item
   if st.button(('▣  ' if active else '   ')+item,key='nav_'+item,use_container_width=True,type='primary' if active else 'secondary'):
    st.session_state.terminal_navigation=item
    st.rerun()
 st.markdown('''<div class="bm-sidebar-bottom"><div class="bm-sidebar-meta"><div><span>PROJECT</span><b>BM-AI-001</b></div><div><span>EXCHANGE</span><b>NSE · INDIA</b></div><div><span>MODE</span><b>PAPER / RESEARCH</b></div><div><span>COURSE</span><b>CS3216 · TSAF</b></div></div></div>''',unsafe_allow_html=True)
 st.caption('BUILD 1.2 · LOCAL RESEARCH WORKSPACE')
selected_page=st.session_state.get('terminal_navigation','Overview')
if selected_page not in NAV_ITEMS: selected_page='Overview'
now=datetime.now(IST)
st.markdown(f'''<div class="bm-topbar"><div><div class="bm-kicker">INDIA EQUITY MARKETS <span>/</span> RESEARCH WORKSPACE</div><div class="bm-topbar-title">BHARATMARKET AI <span class="bm-slash">/</span> {selected_page.upper()}</div></div><div class="bm-topbar-right"><div class="bm-session"><i></i> HISTORICAL DATA MODE</div><div class="bm-clock">{now.strftime('%a, %d %b %Y')} · {now.strftime('%H:%M:%S')} IST</div></div></div>''',unsafe_allow_html=True)
if selected_page=='Overview': render_overview(PROJECT_DIR)
elif selected_page=='Market Analysis': render_analysis(PROJECT_DIR)
elif selected_page=='Live Market Feed': render_live_feed(PROJECT_DIR)
elif selected_page=='AI Forecasting': render_forecasting(PROJECT_DIR)
elif selected_page=='Backtesting': render_backtesting(PROJECT_DIR)
elif selected_page=='Risk Analytics': render_risk_analytics(PROJECT_DIR)
elif selected_page=='Data Explorer': render_data_explorer(PROJECT_DIR)
elif selected_page=='System Monitor': render_system_monitor(PROJECT_DIR)
elif selected_page=='Trading Signals': render_signals(PROJECT_DIR)
st.markdown('''<div class="bm-footer"><span>BHARATMARKET AI</span><span>HISTORICAL RESEARCH · MARKET DATA MAY BE DELAYED · PAPER TRADING ONLY</span><span>CS3216 / TSAF</span></div>''',unsafe_allow_html=True)
