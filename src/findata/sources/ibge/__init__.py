"""IBGE — Instituto Brasileiro de Geografia e Estatística.

Source: IBGE Agregados API v3 (servicodados.ibge.gov.br)
No auth required. JSON format.
"""

from findata.sources.ibge.indicators import (
    IBGE_INDICATORS,
    get_indicator,
    get_ipca_breakdown,
)

__all__ = [
    "get_ipca_breakdown",
    "get_indicator",
    "IBGE_INDICATORS",
]
