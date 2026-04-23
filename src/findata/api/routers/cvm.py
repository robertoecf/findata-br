"""CVM API routes — companies, financial statements, funds."""

from __future__ import annotations

from datetime import date
from typing import TypeVar

from fastapi import APIRouter, Query

from findata.sources.cvm import companies, financials, funds

router = APIRouter(prefix="/cvm", tags=["CVM"])

_CURRENT_YEAR = date.today().year

_T = TypeVar("_T")


def _page(items: list[_T], skip: int, limit: int) -> list[_T]:
    return items[skip : skip + limit]


# ── Companies ──────────────────────────────────────────────────────


@router.get("/companies")
async def list_companies(
    only_active: bool = Query(default=True),
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max records to return"),
) -> list[companies.Company]:
    """List all companies registered at CVM (paginated)."""
    return _page(await companies.get_companies(only_active), skip, limit)


@router.get("/companies/search")
async def search_companies(
    q: str = Query(..., min_length=2, description="Search query"),
    only_active: bool = Query(default=True),
) -> list[companies.Company]:
    """Search companies by name."""
    return await companies.search_company(q, only_active)


# ── Financial Statements ───────────────────────────────────────────


@router.get("/financials/dfp")
async def get_dfp(
    year: int = Query(..., ge=2010, le=_CURRENT_YEAR),
    statement: financials.StatementType = Query(default=financials.StatementType.DRE_CON),
    cnpj: str | None = Query(default=None, description="Filter by CNPJ (recommended)"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=5000),
) -> list[financials.FinancialEntry]:
    """Fetch annual financial statements (DFP) from CVM.

    Statement types: BPA_con, BPP_con, DRE_con, DFC_MI_con, DMPL_con, DVA_con
    (and _ind variants for individual/non-consolidated).

    **Tip**: Always pass `cnpj` to avoid downloading the entire dataset.
    """
    return _page(await financials.get_dfp(year, statement, cnpj), skip, limit)


@router.get("/financials/itr")
async def get_itr(
    year: int = Query(..., ge=2011, le=_CURRENT_YEAR),
    statement: financials.StatementType = Query(default=financials.StatementType.DRE_CON),
    cnpj: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=5000),
) -> list[financials.FinancialEntry]:
    """Fetch quarterly financial statements (ITR) from CVM."""
    return _page(await financials.get_itr(year, statement, cnpj), skip, limit)


# ── Funds ──────────────────────────────────────────────────────────


@router.get("/funds")
async def list_funds(
    only_active: bool = Query(default=True),
    classe: str | None = Query(default=None, description="Filter by class"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[funds.Fund]:
    """List all registered investment funds (paginated)."""
    return _page(await funds.get_fund_catalog(only_active, classe), skip, limit)


@router.get("/funds/daily")
async def fund_daily(
    year: int = Query(..., ge=2021, le=_CURRENT_YEAR + 1),
    month: int = Query(..., ge=1, le=12),
    cnpj: str | None = Query(default=None, description="Filter by fund CNPJ (recommended)"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=5000),
) -> list[funds.FundDaily]:
    """Fetch daily fund data (NAV, quota, flows) for a given month.

    **Tip**: Always pass `cnpj` to avoid loading the entire monthly file.
    """
    return _page(await funds.get_fund_daily(year, month, cnpj), skip, limit)
