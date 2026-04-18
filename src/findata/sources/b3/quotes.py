"""B3 stock quotes via yfinance.

yfinance uses Yahoo Finance's publicly available endpoints.
No API key required. Brazilian tickers use .SA suffix.

Note: yfinance is sync-only, so we run it in a thread executor.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from pydantic import BaseModel

_executor = ThreadPoolExecutor(max_workers=4)


class StockQuote(BaseModel):
    ticker: str
    nome: str | None = None
    preco: float | None = None
    variacao_dia: float | None = None  # %
    abertura: float | None = None
    maxima: float | None = None
    minima: float | None = None
    volume: int | None = None
    market_cap: float | None = None
    setor: str | None = None
    moeda: str | None = None


class StockHistoryPoint(BaseModel):
    date: str  # YYYY-MM-DD
    open: float
    high: float
    low: float
    close: float
    volume: int


def _ensure_sa(ticker: str) -> str:
    """Ensure ticker has .SA suffix for B3 stocks."""
    t = ticker.upper().strip()
    if not t.endswith(".SA"):
        t = f"{t}.SA"
    return t


def _fetch_quote_sync(ticker: str) -> StockQuote:
    """Fetch current quote (sync, runs in thread)."""
    import yfinance as yf

    sa_ticker = _ensure_sa(ticker)
    stock = yf.Ticker(sa_ticker)
    info = stock.info

    return StockQuote(
        ticker=ticker.upper().replace(".SA", ""),
        nome=info.get("longName") or info.get("shortName"),
        preco=info.get("currentPrice") or info.get("regularMarketPrice"),
        variacao_dia=info.get("regularMarketChangePercent"),
        abertura=info.get("regularMarketOpen"),
        maxima=info.get("regularMarketDayHigh"),
        minima=info.get("regularMarketDayLow"),
        volume=info.get("regularMarketVolume"),
        market_cap=info.get("marketCap"),
        setor=info.get("sector"),
        moeda=info.get("currency"),
    )


def _fetch_history_sync(
    ticker: str,
    period: str,
    interval: str,
) -> list[StockHistoryPoint]:
    """Fetch historical data (sync, runs in thread)."""
    import yfinance as yf

    sa_ticker = _ensure_sa(ticker)
    stock = yf.Ticker(sa_ticker)
    df = stock.history(period=period, interval=interval)

    results = []
    for idx, row in df.iterrows():
        results.append(
            StockHistoryPoint(
                date=idx.strftime("%Y-%m-%d"),
                open=round(row["Open"], 2),
                high=round(row["High"], 2),
                low=round(row["Low"], 2),
                close=round(row["Close"], 2),
                volume=int(row["Volume"]),
            )
        )
    return results


async def get_quote(ticker: str) -> StockQuote:
    """Get current stock quote for a B3 ticker.

    Args:
        ticker: B3 ticker (e.g., 'PETR4', 'VALE3', 'WEGE3').
              .SA suffix is added automatically.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, partial(_fetch_quote_sync, ticker))


async def get_history(
    ticker: str,
    period: str = "1mo",
    interval: str = "1d",
) -> list[StockHistoryPoint]:
    """Get historical price data for a B3 stock.

    Args:
        ticker: B3 ticker (e.g., 'PETR4').
        period: Data period — 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max.
        interval: Data interval — 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor, partial(_fetch_history_sync, ticker, period, interval)
    )


async def get_multiple_quotes(tickers: list[str]) -> list[StockQuote]:
    """Get current quotes for multiple B3 tickers in parallel.

    Args:
        tickers: List of B3 tickers (e.g., ['PETR4', 'VALE3', 'ITUB4']).
    """
    tasks = [get_quote(t) for t in tickers]
    return await asyncio.gather(*tasks)
