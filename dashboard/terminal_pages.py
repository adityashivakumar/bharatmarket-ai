from pathlib import Path
import pandas as pd
import streamlit as st

def _files(root,pattern): return sorted(Path(root).glob(pattern))
def _read(path):
 try: return pd.read_csv(path)
 except Exception: return pd.DataFrame()
def _head(kicker,title,desc):
 st.markdown(f'<div class="bm-eyebrow">{kicker}</div>',unsafe_allow_html=True); st.title(title); st.caption(desc)
def _report(root,title,pattern,note):
 files=_files(Path(root)/'outputs'/'reports',pattern)
 st.markdown(f'### {title}')
 if not files: st.info(f'No matching report found: outputs/reports/{pattern}'); return
 path=st.selectbox('REPORT FILE',files,format_func=lambda p:p.name,key='report_'+pattern)
 df=_read(path); st.caption(note)
 if df.empty: st.warning('The report is empty or could not be parsed.')
 else:
  st.dataframe(df,use_container_width=True,hide_index=True,height=340)
  st.download_button('Download CSV',path.read_bytes(),file_name=path.name,mime='text/csv')

def render_forecasting(project_dir):
 _head('RESEARCH / MODEL EVALUATION','Forecasting research','Inspect saved forecasting artifacts and model-comparison outputs. This workspace does not generate new predictions.')
 a,b=st.columns(2)
 with a: _report(project_dir,'Model evaluation reports','*model*.csv','Saved results from the existing model evaluation pipeline.')
 with b:
  root=Path(project_dir); files=sorted((root/'data'/'forecasts').glob('*.csv'))+sorted((root/'outputs'/'final_report').glob('*forecast*.csv'))
  st.markdown('### Forecast artifacts')
  if not files: st.info('No forecast CSV artifacts found.')
  else:
   p=st.selectbox('FORECAST DATASET',files,format_func=lambda p:str(p.relative_to(root)),key='forecast_artifact'); df=_read(p)
   st.caption(f'{len(df):,} rows · {len(df.columns)} columns · {p.name}'); st.dataframe(df.head(100),use_container_width=True,hide_index=True,height=340)
 st.markdown('<div class="bm-note">Forecast outputs are historical research artifacts. Their presence does not establish predictive reliability or guarantee future performance.</div>',unsafe_allow_html=True)

def render_backtesting(project_dir):
 _head('RESEARCH / STRATEGY EVALUATION','Backtesting','Inspect saved strategy simulations, trade logs and benchmark comparisons.')
 root=Path(project_dir)/'outputs'/'reports'
 for filename,label in [('backtest_performance_summary.csv','Performance summary'),('backtest_benchmark_comparison.csv','Benchmark comparison')]:
  p=root/filename; st.markdown(f'### {label}')
  if p.exists(): st.dataframe(_read(p),use_container_width=True,hide_index=True)
  else: st.info(f'Not found: {p.name}')
 _report(project_dir,'Trade log and supporting reports','*backtest*.csv','Historical backtest output; inspect assumptions and out-of-sample dates before interpreting results.')

def render_risk_analytics(project_dir):
 _head('RISK / PORTFOLIO METRICS','Risk analytics','Review saved portfolio risk, drawdown, volatility and VaR analysis outputs.')
 _report(project_dir,'Risk reports','*risk*.csv','Historical model outputs; not a live portfolio risk estimate.')
 _report(project_dir,'VaR / CVaR reports','*var*cvar*.csv','Review the estimation window, confidence level and return frequency in the source report.')

def render_data_explorer(project_dir):
 _head('DATA / INVENTORY & QUALITY','Data explorer','Browse local market datasets and saved analytical outputs with explicit source paths.')
 root=Path(project_dir)
 folders=[('Raw daily market data','data/raw/*.csv'),('Processed series','data/processed/*.csv'),('Feature datasets','data/features/*.csv'),('Forecast datasets','data/forecasts/*.csv'),('Research reports','outputs/reports/*.csv')]
 for label,pattern in folders:
  files=_files(root/pattern.split('/')[0],'/'.join(pattern.split('/')[1:])) if False else sorted(root.glob(pattern))
  with st.expander(f'{label} · {len(files)} files',expanded=label=='Raw daily market data'):
   if not files: st.caption('No files found.'); continue
   p=st.selectbox('SELECT FILE',files,format_func=lambda p:p.name,key='data_'+pattern); df=_read(p)
   m1,m2,m3=st.columns(3); m1.metric('ROWS',f'{len(df):,}'); m2.metric('COLUMNS',len(df.columns)); m3.metric('SIZE',f'{p.stat().st_size/1024:,.1f} KB')
   st.caption(f'SOURCE PATH · {p.relative_to(root)}')
   if not df.empty:
    st.dataframe(df.head(250),use_container_width=True,hide_index=True,height=300)
    st.download_button('Download selected CSV',p.read_bytes(),file_name=p.name,mime='text/csv',key='download_'+pattern)

def render_system_monitor(project_dir):
 _head('OPERATIONS / LOCAL DIAGNOSTICS','System monitor','Read-only inventory of expected project services, datasets and generated artifacts.')
 root=Path(project_dir); checks=[('Historical market data',root/'data'/'raw'),('Dashboard modules',root/'dashboard'),('Upstox integration',root/'upstox_integration'/'live'),('Research notebooks',root/'notebooks'),('Saved reports',root/'outputs'/'reports'),('Saved charts',root/'outputs'/'charts')]
 cols=st.columns(3)
 for i,(label,path) in enumerate(checks):
  exists=path.exists(); count=sum(1 for p in path.rglob('*') if p.is_file()) if exists else 0
  with cols[i%3]:
   status='AVAILABLE' if exists else 'MISSING'; color='#20c997' if exists else '#e6b45c'
   st.markdown(f'<div style="background:#101925;border:1px solid #263547;border-radius:6px;padding:13px;margin-bottom:10px"><div style="color:#91a0b2;font-size:10px;letter-spacing:1px">{label.upper()}</div><div style="font:600 22px DM Mono,monospace;color:{color};margin:8px 0">{status}</div><div style="font-size:11px;color:#8193a7">{count:,} files indexed</div></div>',unsafe_allow_html=True)
 st.markdown('### Live integration diagnostics'); tick_dir=root/'upstox_integration'/'live'/'ticks'; tick_files=sorted(tick_dir.glob('normalized_ticks_*.csv')) if tick_dir.exists() else []
 if tick_files:
  rows=[{'File':p.name,'Size KB':round(p.stat().st_size/1024,2),'Modified':pd.Timestamp(p.stat().st_mtime,unit='s')} for p in tick_files]
  st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
  st.caption('Presence of tick files does not imply that the feed is currently connected or receiving fresh updates.')
 else: st.info('No normalized tick files found.')
 st.markdown('<div class="bm-note">This monitor checks local file presence only. It does not claim external APIs, WebSocket sessions or market data are currently healthy.</div>',unsafe_allow_html=True)

def render_signals(project_dir):
 _head('EXECUTION / RESEARCH GATE','Trading signals','Signal presentation remains disabled until the live feed and observation-derived candle pipeline pass market-hours validation.')
 st.warning('Trading signals are intentionally locked. No actionable CE/PE or buy/sell recommendations are generated from this workspace.')
 st.markdown('**Validation gates**\n- Confirm fresh timestamped observations during NSE market hours.\n- Verify per-instrument updates and duplicate / invalid observation handling.\n- Validate 1-minute, 5-minute and 15-minute observed-bar construction.\n- Compare sampled bars with an authoritative broker or exchange candle source.\n- Document gaps and volume limitations before exposing signals.')
