"""ANEEL API routes — energy-auction results."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from findata.sources.aneel import leiloes

router = APIRouter(prefix="/aneel", tags=["ANEEL — Energia"])

_CURRENT_YEAR = date.today().year


@router.get("/leiloes/geracao")
async def list_leiloes_geracao(
    year: int | None = Query(default=None, ge=2005, le=_CURRENT_YEAR + 1),
    fonte: str | None = Query(
        default=None,
        description='Substring of DscFonteEnergia (e.g. "Eólica", "Solar", "Biomassa")',
    ),
    uf: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=5000),
) -> list[leiloes.LeilaoGeracao]:
    """Generation-auction results (every winning empreendimento since 2005)."""
    rows = await leiloes.get_aneel_leiloes_geracao(year=year, fonte=fonte, uf=uf)
    return rows[skip : skip + limit]


@router.get("/leiloes/transmissao")
async def list_leiloes_transmissao(
    year: int | None = Query(default=None, ge=1999, le=_CURRENT_YEAR + 1),
    uf: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=5000),
) -> list[leiloes.LeilaoTransmissao]:
    """Transmission-auction results (every winning lot since 1999)."""
    rows = await leiloes.get_aneel_leiloes_transmissao(year=year, uf=uf)
    return rows[skip : skip + limit]
