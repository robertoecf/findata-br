# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **IPEA Data** source (OData v4) — access to ~8k curated macroeconomic
  series with endpoints for catalog listing, by-SERCODIGO values,
  metadata, and full-text search. CLI: `findata ipea {catalog,get,search}`.
- IPEA router at `/ipea/*` and curated built-in catalog.

## [0.1.0] — 2026-04-22

### Added

- Initial public release of **findata-br**.
- REST API (FastAPI) with routers for BCB, CVM, B3, IBGE, Tesouro.
- Auto-generated MCP server mounted at `/mcp` (via `fastapi-mcp`).
- CLI (`findata`) with animated gradient banner and rich-text tables.
- Async Python library with shared httpx client (connection pool, retries,
  LRU cache, OData-safe URL builder).
- BCB sources: SGS (18 curated series), PTAX (USD/EUR/all currencies,
  period endpoint), Focus (annual, monthly, Selic-per-COPOM, Top-5).
- CVM sources: registered companies (search + listing), DFP/ITR financial
  statements, fund catalog and daily NAV.
- IBGE Agregados v3 source with IPCA breakdown by 10 major groups.
- Tesouro Transparente historical bond CSV with caching.
- B3 quotes via `yfinance` (optional extra `[b3]`).
- Unit tests for http client, models, parsers, and API (network-free, via
  `respx`). Integration suite gated by `pytest -m integration`.
- `Dockerfile` + `docker-compose.yml` for one-command deployment.
- GitHub Actions CI matrix (3.11/3.12/3.13).
