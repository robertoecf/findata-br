"""ANBIMA Data — credentialed Brazilian financial-market data.

Gated behind ANBIMA's developer programme. Set:
    ANBIMA_CLIENT_ID
    ANBIMA_CLIENT_SECRET
…in the environment to enable. Without them, the routes and CLI commands
that depend on this module return a clean 503 / RuntimeError.

Provides:
    - IMA family (IMA-B, IMA-S, IRF-M, etc.)
    - IHFA (hedge fund index)
    - IDA (debenture indices)
    - ETTJ (curva a termo / yield curve)
    - Debêntures (private fixed income)
"""

from findata.sources.anbima.client import ANBIMAClient, get_default_client
from findata.sources.anbima.credentials import ANBIMACredentials, load_anbima_credentials
from findata.sources.anbima.indices import (
    IMADataPoint,
    IMAFamily,
    get_ettj,
    get_ida,
    get_ihfa,
    get_ima,
)

__all__ = [
    "ANBIMAClient",
    "ANBIMACredentials",
    "IMADataPoint",
    "IMAFamily",
    "get_default_client",
    "get_ettj",
    "get_ida",
    "get_ihfa",
    "get_ima",
    "load_anbima_credentials",
]
