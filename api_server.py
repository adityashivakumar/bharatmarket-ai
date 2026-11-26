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

@app.get('/data/health')
def data_health():
 results=[]
 for symbol in SYMBOLS:
  path=RAW/f'{symbol}.csv'
  item={'symbol':symbol,'file':path.name,'exists':path.exists(),'status':'MISSING','rows':0,'first_date':None,'last_date':None,'missing_volume':False,'issues':[]}
  if not path.exists():
   item['issues'].append('CSV file not found')
   results.append(item)
   continue
  try:
   df=pd.read_csv(path)
   df.columns=[str(col).strip().lower() for col in df.columns]
   required={'date','open','high','low','close'}
   missing=sorted(required-set(df.columns))
   if missing:
    item['issues'].append('Missing columns: '+', '.join(missing))
    item['status']='INVALID'
    results.append(item)
    continue
   item['missing_volume']='volume' not in df.columns
   if item['missing_volume']:
    item['issues'].append('Volume column missing; Streamlit analytics expects volume')
   df['date']=pd.to_datetime(df['date'],errors='coerce')
   for col in ['open','high','low','close','volume']:
    if col in df: df[col]=pd.to_numeric(df[col],errors='coerce')
   item['rows']=int(len(df))
   valid=df.dropna(subset=['date','open','high','low','close']).copy()
   item['first_date']=valid['date'].min().strftime('%Y-%m-%d') if not valid.empty else None
   item['last_date']=valid['date'].max().strftime('%Y-%m-%d') if not valid.empty else None
   invalid_dates=int(df['date'].isna().sum())
   if invalid_dates: item['issues'].append(f'{invalid_dates} invalid date rows')
   invalid_prices=int(df[['open','high','low','close']].isna().any(axis=1).sum())
   if invalid_prices: item['issues'].append(f'{invalid_prices} rows with missing/non-numeric OHLC')
   bad_ohlc=int(((valid['high'] < valid[['open','close','low']].max(axis=1)) | (valid['low'] > valid[['open','close','high']].min(axis=1))).sum())
   if bad_ohlc: item['issues'].append(f'{bad_ohlc} inconsistent OHLC rows')
   duplicates=int(valid['date'].duplicated().sum())
   if duplicates: item['issues'].append(f'{duplicates} duplicate dates (loader keeps last)')
   if item['rows']==0 or valid.empty: item['status']='INVALID'
   elif item['issues']: item['status']='WARNING'
   else: item['status']='OK'
  except Exception as exc:
   item['status']='ERROR'
   item['issues'].append(str(exc))
  results.append(item)
 ok=sum(1 for item in results if item['status']=='OK')
 return {'source':'local_csv','checked':len(results),'ok':ok,'warnings':sum(1 for item in results if item['status']=='WARNING'),'invalid':sum(1 for item in results if item['status'] in ('INVALID','ERROR','MISSING')),'instruments':results,'timestamp':datetime.now().astimezone().isoformat()}

@app.get('/ml/status')
def ml_status():
 candidates=[ROOT/'models',ROOT/'outputs'/'models',ROOT/'artifacts'/'models',ROOT/'outputs'/'forecasts']
 found=[]
 for folder in candidates:
  if folder.exists():
   for path in sorted(folder.rglob('*')):
    if path.is_file():
     found.append({'name':path.name,'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size})
 return {'integration':'not_verified','model_artifacts_found':len(found),'artifacts':found[:100],'message':'Artifact discovery only. Model loading, feature compatibility and inference have not been tested by this API.'}
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
  from upstox_integration.live.streaming_candle_engine import candle_engine

  s = get_service().get_snapshot().get('status', {})
  engine = candle_engine.get_snapshot()

  now = datetime.now().astimezone()
  last_message = s.get('last_message_time')
  last_update = s.get('last_update_time')

  def _age_seconds(value):
   if not value:
    return None
   try:
    timestamp = datetime.fromisoformat(value)
    if timestamp.tzinfo is None:
     timestamp = timestamp.astimezone()
    return max(0.0, (now - timestamp).total_seconds())
   except (TypeError, ValueError):
    return None

  message_age_seconds = _age_seconds(last_message)
  update_age_seconds = _age_seconds(last_update)

  connected = bool(s.get('connected'))
  started = bool(s.get('started'))
  expected_instruments = len(SYMBOLS)
  received_instruments = len((snapshot := get_service().get_snapshot().get('data'))['symbol'].unique()) if snapshot is not None and not snapshot.empty else 0

  if not started:
   feed_state = 'stopped'
  elif not connected:
   feed_state = 'disconnected'
  elif not s.get('valid_observation_count'):
   feed_state = 'connected_awaiting_data'
  elif update_age_seconds is None or update_age_seconds > 30:
   feed_state = 'stale'
  else:
   feed_state = 'receiving_data'

  return {
   'connected': connected,
   'started': started,
   'feed_state': feed_state,
   'last_message_time': last_message,
   'last_update_time': last_update,
   'last_update_exchange_time': s.get('last_update_exchange_time'),
   'message_age_seconds': message_age_seconds,
   'update_age_seconds': update_age_seconds,
   'expected_instruments': expected_instruments,
   'received_instruments': received_instruments,
   'message_count': int(s.get('message_count', 0)),
   'update_count': int(s.get('update_count', 0)),
   'valid_observation_count': int(s.get('valid_observation_count', 0)),
   'duplicate_observation_count': int(s.get('duplicate_observation_count', 0)),
   'invalid_observation_count': int(s.get('invalid_observation_count', 0)),
   'candle_engine': engine,
   'last_error': s.get('last_error'),
   'tick_file': s.get('tick_file')
  }
 except Exception as exc:
  return {
   'connected': False,
   'started': False,
   'feed_state': 'unavailable',
   'last_message_time': None,
   'message_age_seconds': None,
   'message_count': 0,
   'update_count': 0,
   'candle_engine': None,
   'last_error': f'Live service unavailable: {exc}',
   'tick_file': None
  }
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


# ----------------------------------------------------------
# LIVE MARKET DATA ENDPOINTS
# ----------------------------------------------------------

def _live_clean_value(value):
 try:
  if pd.isna(value):
   return None
 except (TypeError, ValueError):
  pass

 if hasattr(value, 'isoformat'):
  return value.isoformat()

 if hasattr(value, 'item'):
  return value.item()

 return value


def _live_clean_records(records):
 return [
  {key: _live_clean_value(value) for key, value in row.items()}
  for row in records
 ]


@app.get('/live/market')
def live_market():
 try:
  from upstox_integration.live.live_feed_service import get_service

  snapshot = get_service().get_snapshot()
  df = snapshot.get('data')

  rows = []
  if df is not None and not df.empty:
   rows = _live_clean_records(df.to_dict(orient='records'))

  return {
   'source': 'upstox_live_feed',
   'count': len(rows),
   'instruments': rows,
   'status': snapshot.get('status', {})
  }
 except Exception as exc:
  raise HTTPException(503, f'Live market data unavailable: {exc}')


@app.get('/live/candles')
def live_candles(
 symbol: str = Query(..., min_length=1),
 timeframe: str = Query('1m', pattern='^(1m|5m|15m)$'),
 limit: int = Query(200, ge=1, le=500)
):
 try:
  from upstox_integration.live.streaming_candle_engine import candle_engine

  symbol = symbol.strip().upper()

  if symbol not in SYMBOLS:
   raise HTTPException(404, 'Unknown instrument')

  rows = candle_engine.get_candles(
   symbol=symbol,
   timeframe=timeframe,
   limit=limit
  )

  return {
   'symbol': symbol,
   'timeframe': timeframe,
   'source': 'upstox_streaming_candles',
   'count': len(rows),
   'candles': rows
  }
 except HTTPException:
  raise
 except Exception as exc:
  raise HTTPException(503, f'Live candles unavailable: {exc}')


@app.get('/live/indicators')
def live_indicators(
 symbol: str = Query(..., min_length=1),
 timeframe: str = Query('1m', pattern='^(1m|5m|15m)$'),
 limit: int = Query(200, ge=1, le=500)
):
 try:
  from upstox_integration.live.streaming_candle_engine import candle_engine
  from upstox_integration.live.indicator_engine import calculate_indicators

  symbol = symbol.strip().upper()

  if symbol not in SYMBOLS:
   raise HTTPException(404, 'Unknown instrument')

  candles = candle_engine.get_candles(
   symbol=symbol,
   timeframe=timeframe,
   limit=limit
  )

  if not candles:
   return {
    'symbol': symbol,
    'timeframe': timeframe,
    'source': 'upstox_streaming_candles',
    'count': 0,
    'indicators': [],
    'message': 'No live candles received yet.'
   }

  df = pd.DataFrame(candles)

  # The indicator engine expects a volume column.
  # Keep unavailable volume as NaN; do not invent index volume.
  df['volume'] = pd.to_numeric(
   df['volume'],
   errors='coerce'
  )

  calculated = calculate_indicators(df)

  records = _live_clean_records(
   calculated.to_dict(orient='records')
  )

  return {
   'symbol': symbol,
   'timeframe': timeframe,
   'source': 'upstox_streaming_candles',
   'count': len(records),
   'indicators': records
  }

 except HTTPException:
  raise
 except Exception as exc:
  raise HTTPException(503, f'Live indicators unavailable: {exc}')

