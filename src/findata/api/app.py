"""FastAPI application — REST API + auto-generated MCP server."""

from __future__ import annotations

from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_mcp import FastApiMCP

from findata.api.routers import b3, bcb, cvm, ibge, tesouro
from findata.http_client import close_client

_VERSION = version("findata-br")


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    yield
    await close_client()


app = FastAPI(
    title="findata-br",
    description=(
        "Open-source Brazilian financial data API. "
        "Aggregates public data from BCB, CVM, B3, ANBIMA, and Tesouro Nacional. "
        "Free. No API key required."
    ),
    version=_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def _value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# ── Routers ────────────────────────────────────────────────────────

app.include_router(bcb.router)
app.include_router(cvm.router)
app.include_router(tesouro.router)
app.include_router(ibge.router)
app.include_router(b3.router)


# ── MCP Server (auto-generated from FastAPI endpoints) ─────────────

mcp = FastApiMCP(
    app,
    name="findata-br",
    description="Brazilian financial data MCP server — BCB, CVM, B3, IBGE, Tesouro",
)
mcp.mount()  # Serves MCP at /mcp


# ── Health / Root ──────────────────────────────────────────────────


@app.get("/", tags=["Meta"])
async def root():
    return {
        "name": "findata-br",
        "version": _VERSION,
        "docs": "/docs",
        "mcp": "/mcp",
        "sources": {
            "bcb": "Banco Central do Brasil (Selic, IPCA, PTAX, Focus)",
            "cvm": "CVM (companies, financial statements, funds)",
            "tesouro": "Tesouro Direto (treasury bonds)",
            "ibge": "IBGE (economic indicators)",
            "b3": "B3 (stock quotes via yfinance)",
        },
    }
