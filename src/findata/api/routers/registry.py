"""Cross-source CNPJ resolver — embedded FTS5 catalog."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from findata.registry import get_meta, lookup
from findata.registry.models import LookupResult

router = APIRouter(prefix="/registry", tags=["Registry — Cross-source CNPJ resolver"])


@router.get("/lookup")
async def lookup_entity(
    q: str = Query(
        ...,
        min_length=2,
        description=(
            "Query: CNPJ (with or without mask), B3 ticker (PETR4), CVM code, "
            "SUSEP FIP code, or company-name fragment. The registry resolves "
            "all of these via a single FTS5 MATCH query."
        ),
        examples=["33000167000101", "PETR4", "petrobras", "33.000.167/0001-01"],
    ),
    limit: int = Query(default=20, ge=1, le=100),
) -> LookupResult:
    """Resolve any CNPJ-shaped, ticker-shaped, or name-shaped query to entities.

    Uses the embedded FTS5 registry. BM25 rank tells you the match strength —
    very negative (e.g. -10) for unique-token exact hits, near-zero for fuzzy
    name matches against common words.
    """
    return await lookup(q, limit=limit)


@router.get("/meta")
async def registry_meta() -> dict[str, str]:
    """Build metadata of the embedded registry (version, build date, hash)."""
    try:
        return await get_meta()
    except Exception as e:  # pragma: no cover — only fires if the file is missing
        raise HTTPException(
            status_code=503,
            detail=f"registry.sqlite not available: {e}",
        ) from e
