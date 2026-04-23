"""BCB API routes — Selic, IPCA, câmbio, Focus."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from findata.sources.bcb import focus, ptax, sgs

router = APIRouter(prefix="/bcb", tags=["Banco Central"])


# ── SGS (time series) ──────────────────────────────────────────────


@router.get("/series")
async def list_series() -> dict[str, dict[str, object]]:
    """List all available BCB time series in our catalog."""
    return sgs.SERIES_CATALOG


@router.get("/series/code/{code}")
async def get_series_by_code(
    code: int,
    start: date | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end: date | None = Query(default=None, description="End date (YYYY-MM-DD)"),
    n: int | None = Query(default=None, ge=1, le=1000, description="Last N values"),
) -> list[sgs.SGSDataPoint]:
    """Get a BCB time series by numeric code (e.g., 432 for Selic)."""
    if n is not None:
        return await sgs.get_series_last(code, n)
    return await sgs.get_series(code, start, end)


@router.get("/series/name/{name}")
async def get_series_by_name(
    name: str,
    n: int = Query(default=10, ge=1, le=1000, description="Number of recent values"),
) -> list[sgs.SGSDataPoint]:
    """Get recent values for a named series (selic, ipca, dolar_ptax, etc.)."""
    return await sgs.get_series_by_name(name, n)


# ── PTAX (exchange rates) ──────────────────────────────────────────


@router.get("/ptax/usd")
async def ptax_usd(
    d: date | None = Query(default=None, alias="date", description="Date (YYYY-MM-DD)"),
) -> list[ptax.PTAXQuote]:
    """Get USD/BRL PTAX quote for a specific date (default: today)."""
    return await ptax.get_ptax_usd(d)


@router.get("/ptax/usd/period")
async def ptax_usd_period(
    start: date = Query(..., description="Start date"),
    end: date = Query(..., description="End date"),
) -> list[ptax.PTAXQuote]:
    """Get USD/BRL PTAX quotes for a date range."""
    return await ptax.get_ptax_usd_period(start, end)


@router.get("/ptax/{currency}")
async def ptax_currency(
    currency: str,
    d: date | None = Query(default=None, alias="date"),
) -> list[ptax.PTAXQuote]:
    """Get PTAX quote for any currency (EUR, GBP, JPY, etc.)."""
    return await ptax.get_ptax_currency(currency, d)


@router.get("/currencies")
async def list_currencies() -> list[ptax.Currency]:
    """List all currencies available in PTAX."""
    return await ptax.get_currencies()


# ── Focus (market expectations) ────────────────────────────────────


@router.get("/focus/indicators")
async def focus_indicators() -> list[str]:
    """List all indicators available in Focus bulletin."""
    return focus.FOCUS_INDICATORS


@router.get("/focus/annual")
async def focus_annual(
    indicator: str = Query(default="IPCA"),
    top: int = Query(default=20, ge=1, le=100),
) -> list[focus.FocusExpectation]:
    """Get annual market expectations from Boletim Focus."""
    return await focus.get_focus_annual(indicator, top)


@router.get("/focus/monthly")
async def focus_monthly(
    indicator: str = Query(default="IPCA"),
    top: int = Query(default=20, ge=1, le=100),
) -> list[focus.FocusExpectation]:
    """Get monthly market expectations from Boletim Focus."""
    return await focus.get_focus_monthly(indicator, top)


@router.get("/focus/selic")
async def focus_selic(
    top: int = Query(default=20, ge=1, le=100),
) -> list[focus.FocusSelic]:
    """Get Selic expectations per COPOM meeting."""
    return await focus.get_focus_selic(top)


@router.get("/focus/top5")
async def focus_top5(
    indicator: str = Query(default="IPCA"),
    top: int = Query(default=20, ge=1, le=100),
) -> list[focus.FocusExpectation]:
    """Get Top 5 forecasters' annual expectations."""
    return await focus.get_focus_top5_annual(indicator, top)
