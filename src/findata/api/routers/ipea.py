"""IPEA Data API routes — OData v4 series from IPEA."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from findata.sources.ipea import series as ipea_series

router = APIRouter(prefix="/ipea", tags=["IPEA Data"])


@router.get("/catalog")
async def list_catalog() -> dict[str, dict[str, str]]:
    """List curated IPEA series that complement BCB/IBGE coverage."""
    return ipea_series.IPEA_CATALOG


@router.get("/series/{sercodigo}")
async def get_series(
    sercodigo: str,
    top: int | None = Query(default=None, ge=1, le=5000, description="Most recent N values"),
) -> list[ipea_series.IPEADataPoint]:
    """Fetch values of an IPEA series by SERCODIGO (e.g., BM12_TJOVER12)."""
    return await ipea_series.get_series_values(sercodigo, top)


@router.get("/metadata/{sercodigo}")
async def get_metadata(sercodigo: str) -> ipea_series.IPEAMetadata:
    """Fetch metadata (name, unit, periodicity, source) for an IPEA series."""
    meta = await ipea_series.get_metadata(sercodigo)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Unknown SERCODIGO: {sercodigo}")
    return meta


@router.get("/search")
async def search(
    q: str = Query(..., min_length=2, description="Search query"),
    top: int = Query(default=25, ge=1, le=200),
) -> list[ipea_series.IPEAMetadata]:
    """Full-text search across the full IPEA catalog (~8k series)."""
    return await ipea_series.search_series(q, top)
