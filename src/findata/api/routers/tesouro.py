"""Tesouro Direto API routes — Treasury bonds."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from findata.sources.tesouro import bonds

router = APIRouter(prefix="/tesouro", tags=["Tesouro Direto"])


@router.get("/bonds")
async def list_bonds(
    tipo: str | None = Query(default=None, description="Bond type filter (e.g., 'Tesouro IPCA+')"),
    start: date | None = Query(default=None, description="Start date"),
    end: date | None = Query(default=None, description="End date"),
    limit: int = Query(default=500, ge=1, le=5000),
):
    """Get treasury bond prices and rates from Tesouro Transparente."""
    return await bonds.get_treasury_bonds(tipo, start, end, limit)


@router.get("/bonds/search")
async def search_bonds(
    q: str = Query(..., min_length=2, description="Search query"),
):
    """Search available bond names."""
    return await bonds.search_bonds(q)


@router.get("/bonds/history")
async def bond_history(
    titulo: str = Query(..., description="Bond name (e.g., 'Tesouro IPCA+ 2035')"),
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
):
    """Get price/rate history for a specific bond."""
    return await bonds.get_bond_history(titulo, start, end)
