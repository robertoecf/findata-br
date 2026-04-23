"""Tesouro Direto — Historical prices and rates from Tesouro Transparente.

Public CSV, no auth. UTF-8, semicolon-delimited.
"""

from __future__ import annotations

import csv
import io
from datetime import date

from pydantic import BaseModel

from findata._cache import TTLCache
from findata.http_client import get_bytes

TESOURO_CSV_URL = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/"
    "df56aa42-484a-4a59-8184-7676580c81e3/resource/"
    "796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv"
)


class TreasuryBond(BaseModel):
    tipo: str
    titulo: str
    dt_vencimento: str
    dt_base: str
    taxa_compra: float | None = None
    taxa_venda: float | None = None
    pu_compra: float | None = None
    pu_venda: float | None = None
    pu_base: float | None = None


def _float(val: str) -> float | None:
    if not val or not val.strip():
        return None
    try:
        return float(val.replace(",", "."))
    except ValueError:
        return None


_DATE_PARTS = 3  # day / month / year


def _date_br(val: str) -> str:
    """DD/MM/YYYY → YYYY-MM-DD."""
    parts = val.strip().split("/")
    if len(parts) != _DATE_PARTS:
        return val
    return f"{parts[2]}-{parts[1]}-{parts[0]}"


# Parsed-data cache (avoids re-parsing ~170k rows on every call).
_bonds_cache: TTLCache[list[TreasuryBond]] = TTLCache(ttl=3600)


async def _load() -> list[TreasuryBond]:
    raw = await get_bytes(TESOURO_CSV_URL, cache_ttl=3600)
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")), delimiter=";")
    results: list[TreasuryBond] = []
    for row in reader:
        tipo = row.get("Tipo Titulo", "")
        venc = _date_br(row.get("Data Vencimento", ""))
        results.append(
            TreasuryBond(
                tipo=tipo,
                titulo=f"{tipo} {venc[:4]}".strip(),
                dt_vencimento=venc,
                dt_base=_date_br(row.get("Data Base", "")),
                taxa_compra=_float(row.get("Taxa Compra Manha", "")),
                taxa_venda=_float(row.get("Taxa Venda Manha", "")),
                pu_compra=_float(row.get("PU Compra Manha", "")),
                pu_venda=_float(row.get("PU Venda Manha", "")),
                pu_base=_float(row.get("PU Base Manha", "")),
            )
        )
    return results


def _filter_by_text(items: list[TreasuryBond], field: str, query: str) -> list[TreasuryBond]:
    q = query.upper()
    return [b for b in items if q in getattr(b, field, "").upper()]


def _filter_by_dates(
    items: list[TreasuryBond],
    start: date | None,
    end: date | None,
) -> list[TreasuryBond]:
    if start:
        s = start.isoformat()
        items = [b for b in items if b.dt_base >= s]
    if end:
        e = end.isoformat()
        items = [b for b in items if b.dt_base <= e]
    return items


async def get_treasury_bonds(
    tipo: str | None = None,
    start: date | None = None,
    end: date | None = None,
    limit: int = 500,
) -> list[TreasuryBond]:
    """Get treasury bonds, optionally filtered by type and date range."""
    bonds = await _bonds_cache.get_or_load(_load)
    if tipo:
        bonds = _filter_by_text(bonds, "tipo", tipo)
    bonds = _filter_by_dates(bonds, start, end)
    return bonds[-limit:]


async def get_bond_history(
    titulo: str,
    start: date | None = None,
    end: date | None = None,
) -> list[TreasuryBond]:
    """Get price/rate history for a specific bond by title substring."""
    bonds = _filter_by_text(await _bonds_cache.get_or_load(_load), "titulo", titulo)
    return _filter_by_dates(bonds, start, end)


async def search_bonds(query: str) -> list[str]:
    """Search bond titles by substring. Returns unique, sorted titles."""
    bonds = await _bonds_cache.get_or_load(_load)
    return sorted({b.titulo for b in _filter_by_text(bonds, "titulo", query)})
