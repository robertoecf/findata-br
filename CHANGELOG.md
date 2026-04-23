# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added — public MCP server ergonomics

- **Rate limiting** via `slowapi` — `FINDATA_RATE_LIMIT_DEFAULT` env var
  (default `60/minute;1000/day`), keyed by `X-Forwarded-For` then
  remote address. Emits `X-RateLimit-Limit/Remaining/Reset` headers.
  Toggle with `FINDATA_RATE_LIMIT_ENABLED=false` for local dev.
- **`GET /stats`** endpoint — uptime, cache size, sources, MCP enabled,
  rate-limit state. Cheap to poll from status pages.
- **`deploy/findata-br.service`** — hardened systemd unit (NoNewPrivileges,
  ProtectSystem=strict, MemoryMax=512M).
- **`deploy/docker-compose.prod.yml`** — localhost-only binding + optional
  `cloudflared` sidecar behind a `--profile tunnel` flag.
- **`docs/DEPLOY_PUBLIC.md`** — full walkthrough (pt-BR) to stand the
  server up on Windows+WSL2 behind Cloudflare Tunnel for free.
- **Community scaffolding** — issue templates (`new-source`, `bug`) with
  a `config.yml` that links to Discussions + the deploy guide, plus
  `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1).

### Changed — legacy cleanup

- **Extract `findata._cache.TTLCache`**, eliminating three copy-pasted
  module-level caches (`_companies/_companies_at/_CACHE_TTL` in CVM
  companies, `_catalog/_catalog_at/_CATALOG_TTL` in CVM funds,
  `_parsed/_parsed_at/_PARSED_TTL` in Tesouro bonds) and the `global`
  keyword dance that went with them.
- **Extract `findata._odata.parse_odata`** — the single generic OData
  `value[]` → Pydantic parser that lived in `bcb/focus.py`. BCB PTAX's
  `get_ptax_*` and `get_currencies` now use it too, dropping an ad-hoc
  `_parse_quotes` and a hand-rolled dict-unpacking list comprehension.
- **Lazy B3 thread-pool** — `ThreadPoolExecutor` is created on first
  use and drained by `close_executor()`, wired into the FastAPI
  lifespan. Importing the module no longer costs a live pool.
- **Type-safe CLI `_run`** — now `_run(coro: Coroutine[Any, Any, T]) -> T`
  via a `TypeVar`, so `typer` handlers don't leak `Any` to callers.
- **Pin `fastapi-mcp>=0.4`** and drop the defensive `mount()` fallback
  — the current API is `mount_http()` and the fallback was dead code.
- Docstrings added to previously empty `__init__.py` files (`api/`,
  `api/routers/`, `sources/`).
- Silence upstream `PydanticDeprecatedSince211` warning at the pytest
  level — it's triggered from inside pydantic-core when we validate a
  `ConfigDict` and not something our code can fix.

### Added

- **IPEA Data** source (OData v4) — access to ~8k curated macroeconomic
  series with endpoints for catalog listing, by-SERCODIGO values,
  metadata, and full-text search. CLI: `findata ipea {catalog,get,search}`.
- IPEA router at `/ipea/*` and curated built-in catalog.
- **Git guardrails** inspired by wealthuman's biome+eslint split:
  - Ruff now enforces AI guardrails (complexity `C901`, max-args `PLR0913`,
    magic-value `PLR2004`, branches `PLR0912`, returns `PLR0911`, stmts
    `PLR0915`), flake8-bandit `S*`, `no-print` `T201`, `ERA` commented-out.
  - Per-context overrides for tests (ignore `S`/`PLR2004`) and FastAPI
    routers (ignore `B008`).
  - `.githooks/pre-commit` (ruff + format check on staged .py + optional
    `ggshield` secret scan) and `.githooks/pre-push` (full `ruff check` +
    `mypy --strict` + `pytest`). Installed via
    `bash scripts/git/install-hooks.sh` → `core.hooksPath = .githooks`.
- `CONTRIBUTING.md` documenting the guardrail philosophy and dev workflow.
- `ROADMAP.md` section comparing findata-br against Tpessia/dados-financeiros
  and gprossignoli/findata (lessons learned, what we adopt / skip).

### Changed

- README fully translated to **pt-BR** and the top banner now renders as an
  ASCII code block (`FINDATA-BR`), matching CLI-tool repo conventions
  instead of relying on a remote typing-svg image that some GitHub clients
  were failing to render.
- Badges trimmed to working ones (CI, version, Python, license, status)
  — removed PyPI/Python-version badges that returned 404 while the package
  is unpublished.

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
