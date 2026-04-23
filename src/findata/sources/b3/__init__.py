"""B3 — Brasil, Bolsa, Balcão (stock exchange data).

Uses yfinance for stock quotes (tickers with .SA suffix).
Install the optional dependency:  pip install findata-br[b3]
"""

from findata.sources.b3.quotes import (
    StockHistoryPoint,
    StockQuote,
    get_history,
    get_multiple_quotes,
    get_quote,
)

__all__ = [
    "StockHistoryPoint",
    "StockQuote",
    "get_history",
    "get_multiple_quotes",
    "get_quote",
]
