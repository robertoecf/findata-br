"""B3 API routes — Stock quotes and history.

yfinance is imported lazily so the rest of the API stays available
when the optional [b3] extra is not installed.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/b3", tags=["B3 - Bolsa"])


def _quotes() -> Any:
    try:
        from findata.sources.b3 import quotes
    except ImportError as exc:  # pragma: no cover — triggered only without yfinance
        raise HTTPException(
            status_code=503,
            detail="B3 support is disabled. Install with: pip install 'findata-br[b3]'",
        ) from exc
    return quotes


@router.get("/quote/{ticker}")
async def get_quote(ticker: str) -> Any:
    """Get current stock quote for a B3 ticker (e.g., PETR4, VALE3, WEGE3)."""
    quotes = _quotes()
    try:
        return await quotes.get_quote(ticker)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Ticker not found: {ticker}") from exc


@router.get("/history/{ticker}")
async def get_history(
    ticker: str,
    period: str = Query(
        default="1mo",
        description="Period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max",
    ),
    interval: str = Query(
        default="1d",
        description="Interval: 1d, 1wk, 1mo",
    ),
) -> Any:
    """Get historical price data for a B3 stock."""
    quotes = _quotes()
    try:
        return await quotes.get_history(ticker, period, interval)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"No history for: {ticker}") from exc


@router.get("/quotes")
async def get_multiple_quotes(
    tickers: str = Query(..., description="Comma-separated tickers (e.g., PETR4,VALE3,ITUB4)"),
) -> Any:
    """Get current quotes for multiple B3 tickers."""
    quotes = _quotes()
    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        raise HTTPException(status_code=400, detail="At least one ticker is required")
    if len(ticker_list) > 20:
        raise HTTPException(status_code=400, detail="Max 20 tickers per request")
    try:
        return await quotes.get_multiple_quotes(ticker_list)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
