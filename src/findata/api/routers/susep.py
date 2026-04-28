"""SUSEP API routes — supervised-entities lookup table."""

from __future__ import annotations

from fastapi import APIRouter, Query

from findata.sources.susep import empresas

router = APIRouter(prefix="/susep", tags=["SUSEP — Seguros"])


@router.get("/empresas")
async def list_empresas(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=5000),
) -> list[empresas.EmpresaSusep]:
    """Full list of SUSEP-supervised entities (insurance, previdência, capitalização)."""
    rows = await empresas.get_susep_empresas()
    return rows[skip : skip + limit]


@router.get("/empresas/search")
async def search_empresa(
    q: str = Query(..., min_length=2, description="Substring search (case-insensitive)"),
) -> list[empresas.EmpresaSusep]:
    """Search SUSEP entities by name."""
    return await empresas.search_susep_empresa(q)
