"""ANBIMA API routes — gated by ANBIMA_CLIENT_ID / ANBIMA_CLIENT_SECRET env vars.

If the env vars aren't set, every route returns `503 Service Unavailable`
with a short hint pointing to the credentials docs. If ANBIMA itself
returns 401/403, we surface those upstream codes verbatim.
"""

from __future__ import annotations

from collections.abc import Awaitable
from datetime import date
from typing import TypeVar

import httpx
from fastapi import APIRouter, HTTPException, Query

from findata.auth.base import AuthError, MissingCredentialsError
from findata.sources.anbima import indices as anbima

router = APIRouter(prefix="/anbima", tags=["ANBIMA (auth required)"])

_T = TypeVar("_T")


def _wrap_auth_errors(exc: Exception) -> HTTPException:
    """Translate auth/upstream failures into clean HTTP responses."""
    if isinstance(exc, MissingCredentialsError):
        return HTTPException(
            status_code=503,
            detail={
                "error": "credentials_missing",
                "source": exc.source,
                "env_vars_required": exc.env_vars,
                "docs": "https://github.com/robertoecf/findata-br/blob/main/docs/SOURCES_WITH_AUTH.md",
            },
        )
    if isinstance(exc, AuthError):
        return HTTPException(status_code=502, detail=f"upstream auth failed: {exc}")
    if isinstance(exc, httpx.HTTPStatusError):
        return HTTPException(
            status_code=exc.response.status_code,
            detail=exc.response.text[:500],
        )
    return HTTPException(status_code=500, detail=str(exc))


async def _safely(coro: Awaitable[_T]) -> _T:
    try:
        return await coro
    except (MissingCredentialsError, AuthError, httpx.HTTPStatusError) as exc:
        raise _wrap_auth_errors(exc) from exc


@router.get("/ima")
async def ima(
    family: anbima.IMAFamily = Query(default=anbima.IMAFamily.IMA_B),
    data: date | None = Query(default=None),
) -> list[anbima.IMADataPoint]:
    """Fetch an IMA family index (IMA-B, IMA-S, IRF-M, ...) for a date."""
    return await _safely(anbima.get_ima(family, data))


@router.get("/ihfa")
async def ihfa(data: date | None = Query(default=None)) -> list[anbima.IHFADataPoint]:
    """Fetch the IHFA hedge fund index for a date."""
    return await _safely(anbima.get_ihfa(data))


@router.get("/ida")
async def ida(data: date | None = Query(default=None)) -> list[anbima.IDADataPoint]:
    """Fetch the IDA family of debenture indices for a date."""
    return await _safely(anbima.get_ida(data))


@router.get("/ettj")
async def ettj(data: date | None = Query(default=None)) -> list[anbima.ETTJDataPoint]:
    """Fetch the zero-coupon yield curve (estrutura a termo) for a date."""
    return await _safely(anbima.get_ettj(data))


@router.get("/status")
async def status() -> dict[str, object]:
    """Report whether ANBIMA credentials are configured (without exposing them)."""
    from findata.sources.anbima.credentials import load_anbima_credentials

    try:
        load_anbima_credentials()
        return {"configured": True}
    except MissingCredentialsError as exc:
        return {
            "configured": False,
            "env_vars_required": exc.env_vars,
            "docs": "/docs#/ANBIMA",
        }
