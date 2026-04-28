"""Tesouro Nacional — Treasury bonds + public-finance accounting (SICONFI).

| Module       | Source                                       | Cadence     |
|--------------|----------------------------------------------|-------------|
| `bonds.py`   | Tesouro Direto historical CSV                | daily       |
| `siconfi.py` | RREO (bimestral) + RGF (quadrimestral) API   | bi/quadrim. |

Sources: ``tesourotransparente.gov.br`` and
``apidatalake.tesouro.gov.br/ords/siconfi``. No auth required.
"""

from findata.sources.tesouro.bonds import (
    TreasuryBond,
    get_bond_history,
    get_treasury_bonds,
    search_bonds,
)
from findata.sources.tesouro.siconfi import (
    SiconfiAccount,
    SiconfiEntity,
    get_entes,
    get_rgf,
    get_rreo,
)

__all__ = [
    "SiconfiAccount",
    "SiconfiEntity",
    "TreasuryBond",
    "get_bond_history",
    "get_entes",
    "get_rgf",
    "get_rreo",
    "get_treasury_bonds",
    "search_bonds",
]
