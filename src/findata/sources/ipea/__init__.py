"""IPEA Data — Brazilian applied economic research institute.

Source: IPEA Data OData v4 API (http://www.ipeadata.gov.br/api/odata4)
No auth required. JSON format.

Provides historical macroeconomic series that complement BCB/IBGE — often
with longer history (back to 1940s) and cross-source aggregation (IPEA
curates IBGE, BCB, FGV, MTE, etc. into a single catalog of ~8k series).
"""

from findata.sources.ipea.series import (
    IPEADataPoint,
    IPEAMetadata,
    get_metadata,
    get_series_values,
    search_series,
)

__all__ = [
    "IPEADataPoint",
    "IPEAMetadata",
    "get_metadata",
    "get_series_values",
    "search_series",
]
