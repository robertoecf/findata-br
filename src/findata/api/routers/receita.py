"""Receita Federal API routes — federal-tax revenue (arrecadação)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from findata.sources.receita import arrecadacao

router = APIRouter(prefix="/receita", tags=["Receita Federal"])

_CURRENT_YEAR = date.today().year


@router.get("/arrecadacao")
async def list_arrecadacao(
    year: int | None = Query(default=None, ge=2000, le=_CURRENT_YEAR + 1),
    month: int | None = Query(default=None, ge=1, le=12),
    uf: str | None = Query(default=None, description="State UF (e.g. SP, RJ)"),
    tributo: str | None = Query(
        default=None,
        description="Substring match against tax-category column (e.g. 'IRPF', 'COFINS')",
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=5000),
) -> list[arrecadacao.ArrecadacaoMensal]:
    """Federal-tax revenue, long-form (one row per period × UF × tributo)."""
    rows = await arrecadacao.get_arrecadacao(year, month, uf, tributo)
    return rows[skip : skip + limit]


@router.get("/tributos")
async def list_tributos() -> list[str]:
    """List the current tributo categories (CSV header)."""
    return await arrecadacao.list_tributos()
