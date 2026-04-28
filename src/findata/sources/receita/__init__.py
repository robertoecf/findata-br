"""Receita Federal — federal-tax data (currently arrecadação por UF).

Source: ``https://www.gov.br/receitafederal/dados/`` (open-data portal).
No auth. CSV files served behind a Cloudflare-style edge that needs a
realistic User-Agent (handled by the shared http client).
"""

from findata.sources.receita.arrecadacao import (
    ArrecadacaoMensal,
    get_arrecadacao,
    list_tributos,
)

__all__ = [
    "ArrecadacaoMensal",
    "get_arrecadacao",
    "list_tributos",
]
