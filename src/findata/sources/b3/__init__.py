"""B3 — Brasil, Bolsa, Balcão (stock exchange data).

Uses yfinance for stock quotes (tickers with .SA suffix).
"""

from findata.sources.b3.quotes import (
    get_history,
    get_multiple_quotes,
    get_quote,
)

__all__ = [
    "get_quote",
    "get_history",
    "get_multiple_quotes",
]
