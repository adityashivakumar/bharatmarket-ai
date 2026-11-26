# BharatMarket AI — Web Terminal (Next.js + FastAPI)

Streamlit is no longer the target frontend. The browser application is in `web/`; Python research notebooks, historical CSVs and Upstox integration remain intact.

## Stack
- Frontend: Next.js 15, React, TypeScript, Recharts, Lucide and Tailwind.
- API: FastAPI reads the existing `data/raw/*.csv` datasets and exposes market history, universe, live-service status and research report endpoints.
- Live feed: the API reads the existing Upstox service status. The API process must own the WebSocket service process for its status and controls to be shared.
- Existing notebooks, model artifacts and reports are retained. The initial UI does not invent forecasts or trading signals.

## Run locally
From repository root:
```powershell
python -m pip install -r requirements-web.txt
uvicorn api_server:app --host 127.0.0.1 --port 8000 --reload
```
In another terminal:
```powershell
cd web
npm install
npm run dev
```
Open http://localhost:3000. Next.js proxies `/backend/*` to http://127.0.0.1:8000. Set `BHARATMARKET_API_URL` to override.

## Security and validation
Keep the Upstox token in the root `.env`; never expose it to browser code or commit it. Run the API with the project root as working directory. A WebSocket connection alone is not proof of fresh prices. Validate exchange timestamps and candle construction during NSE market hours before enabling signals.

## Deployment
Deploy Next.js and FastAPI separately. Configure `BHARATMARKET_API_URL` to the API origin and store broker credentials only in the API host environment.
