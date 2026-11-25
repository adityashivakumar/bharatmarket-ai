from pathlib import Path
from datetime import datetime
from typing import Optional
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
ROOT=Path(__file__).resolve().parent
RAW=ROOT/'data'/'raw'
REPORTS=ROOT/'outputs'/'reports'
app=FastAPI(title='BharatMarket AI API',version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:3000','http://127.0.0.1:3000'],allow_credentials=True,allow_methods=['GET','POST'],allow_headers=['*'])
SYMBOLS=['NIFTY50','BANKNIFTY','RELIANCE','TCS','HDFCBANK','INFY','ICICIBANK','SBIN','ITC','LT']
NAMES={'NIFTY50':'NIFTY 50','BANKNIFTY':'NIFTY BANK','RELIANCE':'Reliance Industries','TCS':'Tata Consultancy Services','HDFCBANK':'HDFC Bank','INFY':'Infosys','ICICIBANK':'ICICI Bank','SBIN':'State Bank of India','ITC':'ITC Limited','LT':'Larsen & Toubro'}
def read_symbol(symbol):
 if symbol not in SYMBOLS: raise HTTPException(404,'Unknown instrument')
 path=RAW/f'{symbol}.csv'
 if not path.exists(): raise HTTPException(404,f'Historical dataset missing for {symbol}')
 df=pd.read_csv(path); df.columns=[str(c).strip().lower() for c in df.columns]
 required={'date','open','high','low','close'}
 if not required.issubset(df.columns): raise HTTPException(422,f'Missing columns: {sorted(required-set(df.columns))}')
 df['date']=pd.to_datetime(df['date'],errors='coerce')
 for c in ['open','high','low','close','volume']:
  if c in df: df[c]=pd.to_numeric(df[c],errors='coerce')
 return df.dropna(subset=['date','close']).sort_values('date').drop_duplicates('date',keep='last')
@app.get('/health')
def health(): return {'ok':True,'service':'bharatmarket-api','timestamp':datetime.now().astimezone().isoformat()}
@app.get('/market/universe')
def universe():
 instruments=[]
 for symbol in SYMBOLS:
  try:
   df=read_symbol(symbol)
   if df.empty: continue
   last=df.iloc[-1]; prev=df.iloc[-2]['close'] if len(df)>1 else last['close']; change=float(last['close']-prev)
   instruments.append({'symbol':symbol,'name':NAMES[symbol],'price':float(last['close']),'change':change,'changePct':float(change/prev*100) if prev else 0.0,'date':last['date'].strftime('%Y-%m-%d')})
  except (HTTPException,ValueError,KeyError): continue
 return {'instruments':instruments,'source':'local_historical_csv','count':len(instruments)}
@app.get('/market/{symbol}/history')
def history(symbol:str,period:str=Query('1Y',pattern='^(1M|3M|6M|1Y|5Y)$')):
 df=read_symbol(symbol); days={'1M':31,'3M':92,'6M':183,'1Y':365,'5Y':1826}[period]; df=df[df.date>=df.date.max()-pd.Timedelta(days=days)]
 cols=['date','open','high','low','close']+(['volume'] if 'volume' in df else [])
 rows=[]
 for item in df[cols].itertuples(index=False,name=None):
  date,o,h,l,c,*rest=item; v=rest[0] if rest else None
  rows.append({'date':pd.Timestamp(date).strftime('%Y-%m-%d'),'open':float(o) if pd.notna(o) else None,'high':float(h) if pd.notna(h) else None,'low':float(l) if pd.notna(l) else None,'close':float(c),'volume':float(v) if v is not None and pd.notna(v) else None})
 return {'symbol':symbol,'period':period,'rows':rows,'count':len(rows),'source':'local_historical_csv'}
@app.get('/live/status')
def live_status():
 try:
  from upstox_integration.live.live_feed_service import get_service
  s=get_service().get_snapshot().get('status',{})
  return {'connected':bool(s.get('connected')),'started':bool(s.get('started')),'last_message_time':s.get('last_message_time'),'message_count':int(s.get('message_count',0)),'update_count':int(s.get('update_count',0)),'last_error':s.get('last_error'),'tick_file':s.get('tick_file')}
 except Exception as exc:
  return {'connected':False,'started':False,'last_message_time':None,'message_count':0,'update_count':0,'last_error':f'Live service unavailable: {exc}','tick_file':None}
@app.post('/live/start')
def start_live():
 try:
  from upstox_integration.live.live_feed_service import get_service
  return get_service().start()
 except Exception as exc: raise HTTPException(503,str(exc))
@app.post('/live/stop')
def stop_live():
 try:
  from upstox_integration.live.live_feed_service import get_service
  get_service().stop(); return {'ok':True,'status':'disconnect requested'}
 except Exception as exc: raise HTTPException(503,str(exc))
@app.get('/research/reports')
def reports(kind:Optional[str]=None):
 patterns={'backtest':'*backtest*.csv','risk':'*risk*.csv','models':'*model*.csv','all':'*.csv',None:'*.csv'}
 if kind not in patterns: raise HTTPException(400,'Unsupported report category')
 files=sorted(REPORTS.glob(patterns[kind])) if REPORTS.exists() else []
 return {'reports':[{'name':p.name,'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size} for p in files],'count':len(files)}
@app.get('/research/reports/{filename}')
def report_preview(filename:str):
 if Path(filename).name!=filename or not filename.endswith('.csv'): raise HTTPException(400,'Invalid report filename')
 path=REPORTS/filename
 if not path.exists(): raise HTTPException(404,'Report not found')
 df=pd.read_csv(path).replace({float('inf'):None,float('-inf'):None}).fillna('')
 return {'name':filename,'columns':list(df.columns),'rows':df.head(500).to_dict(orient='records'),'total_rows':len(df)}
