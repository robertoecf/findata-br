"""IBGE API routes — Economic indicators with breakdowns."""

from __future__ import annotations

from fastapi import APIRouter, Query

from findata.sources.ibge import indicators

router = APIRouter(prefix="/ibge", tags=["IBGE"])


@router.get("/indicators")
async def list_indicators() -> dict[str, dict[str, object]]:
    """List all available IBGE economic indicators."""
    return indicators.IBGE_INDICATORS


@router.get("/indicators/{name}")
async def get_indicator(
    name: str,
    periods: int = Query(default=12, ge=1, le=120),
) -> list[indicators.IBGEDataPoint]:
    """Get an IBGE economic indicator (ipca_mensal, pib_trimestral, etc.)."""
    return await indicators.get_indicator(name, periods)


@router.get("/ipca/breakdown")
async def ipca_breakdown(
    periods: int = Query(default=6, ge=1, le=60, description="Number of recent months"),
) -> list[indicators.IBGEDataPoint]:
    """Get IPCA monthly variation broken down by major groups.

    Returns data for all 10 IPCA groups: food, housing, transport, health, etc.
    This granular breakdown is not available from BCB SGS.
    """
    return await indicators.get_ipca_breakdown(periods)


@router.get("/ipca/groups")
async def ipca_groups() -> dict[str, str]:
    """List IPCA major groups and their codes."""
    return indicators.IPCA_GROUPS
