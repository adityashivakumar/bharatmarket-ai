from fastapi import APIRouter, HTTPException, Query
from research_service import (
    UNIVERSE_MAP, backtest, data_catalog, forecast, risk,
    scanner, technical_analysis, universe_status,
)

router = APIRouter(prefix="/research", tags=["research"])


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/universe")
def research_universe():
    return universe_status()


@router.get("/catalog")
def research_catalog():
    return data_catalog()


@router.get("/scanner")
def research_scanner():
    return _run(scanner)


@router.get("/technical/{symbol}")
def research_technical(symbol: str):
    return _run(technical_analysis, symbol)


@router.get("/forecast/{symbol}")
def research_forecast(symbol: str):
    return _run(forecast, symbol)


@router.get("/backtest/{symbol}")
def research_backtest(
    symbol: str,
    fast: int = Query(20, ge=2, le=199),
    slow: int = Query(50, ge=3, le=200),
    cost_bps: float = Query(10.0, ge=0, le=100),
):
    return _run(backtest, symbol, fast, slow, cost_bps)


@router.get("/risk/{symbol}")
def research_risk(symbol: str):
    return _run(risk, symbol)
