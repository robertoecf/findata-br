"""Tesouro Direto + SICONFI API routes — bonds + public-finance accounting."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from findata.sources.tesouro import bonds, siconfi

router = APIRouter(prefix="/tesouro", tags=["Tesouro Direto"])

_CURRENT_YEAR = date.today().year


@router.get("/bonds")
async def list_bonds(
    tipo: str | None = Query(default=None, description="Bond type filter (e.g., 'Tesouro IPCA+')"),
    start: date | None = Query(default=None, description="Start date"),
    end: date | None = Query(default=None, description="End date"),
    limit: int = Query(default=500, ge=1, le=5000),
) -> list[bonds.TreasuryBond]:
    """Get treasury bond prices and rates from Tesouro Transparente."""
    return await bonds.get_treasury_bonds(tipo, start, end, limit)


@router.get("/bonds/search")
async def search_bonds(
    q: str = Query(..., min_length=2, description="Search query"),
) -> list[str]:
    """Search available bond names."""
    return await bonds.search_bonds(q)


@router.get("/bonds/history")
async def bond_history(
    titulo: str = Query(..., description="Bond name (e.g., 'Tesouro IPCA+ 2035')"),
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
) -> list[bonds.TreasuryBond]:
    """Get price/rate history for a specific bond."""
    return await bonds.get_bond_history(titulo, start, end)


# ── SICONFI — RREO + RGF + entes ─────────────────────────────────


@router.get("/siconfi/rreo")
async def siconfi_rreo(
    year: int = Query(..., ge=2013, le=_CURRENT_YEAR + 1),
    bimestre: int = Query(..., ge=1, le=6, description="Bimestre 1-6"),
    cod_ibge: int = Query(..., description="IBGE entity code (1=União, 27 UFs, ~5570 munis)"),
    demonstrativo: str = Query(default="RREO", description="RREO / RREO Simplificado"),
    anexo: str | None = Query(default=None, description='e.g. "RREO-Anexo 01"'),
) -> list[siconfi.SiconfiAccount]:
    """RREO — Relatório Resumido de Execução Orçamentária (bimestral)."""
    return await siconfi.get_rreo(
        year,
        bimestre,
        cod_ibge,
        demonstrativo=demonstrativo,  # type: ignore[arg-type]
        anexo=anexo,
    )


@router.get("/siconfi/rgf")
async def siconfi_rgf(
    year: int = Query(..., ge=2013, le=_CURRENT_YEAR + 1),
    quadrimestre: int = Query(..., ge=1, le=3, description="Quadrimestre 1-3"),
    cod_ibge: int = Query(..., description="IBGE entity code"),
    poder: str = Query(default="E", description="E/L/J/M/D — power branch"),
    demonstrativo: str = Query(default="RGF"),
    anexo: str | None = Query(default=None),
) -> list[siconfi.SiconfiAccount]:
    """RGF — Relatório de Gestão Fiscal (quadrimestral, LRF)."""
    return await siconfi.get_rgf(
        year,
        quadrimestre,
        cod_ibge,
        poder=poder,  # type: ignore[arg-type]
        demonstrativo=demonstrativo,  # type: ignore[arg-type]
        anexo=anexo,
    )


@router.get("/siconfi/entes")
async def siconfi_entes() -> list[siconfi.SiconfiEntity]:
    """Full federation-entity list with IBGE codes (cached 24h)."""
    return await siconfi.get_entes()
