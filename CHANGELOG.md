# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added — CVM fund deep dive

Three new CVM fund products on top of the existing catalog + daily NAV:

- **`get_fund_holdings(cnpj, year, month)`** — full portfolio (CDA file).
  Every position the fund holds, classified by CVM block (BLC_1 títulos
  públicos, BLC_2 cotas de fundos, BLC_4 ações/debêntures, BLC_8
  disponibilidades, etc., plus CONFID / PL / FIE). The monthly zip is
  ~150 MB unzipped, so a CNPJ filter is required and we line-stream
  every block in-place. Optional `blocks=` whitelist.
- **`get_fund_lamina(year, month, cnpj=None)`** plus
  `get_fund_monthly_returns()` and `get_fund_yearly_returns()` — the
  regulatory factsheet (lâmina) with strategy, restrições, alavancagem
  caps, plus per-month and per-year returns vs benchmark.
- **`get_fund_profile(year, month, cnpj=None)`** — perfil mensal:
  cotistas count broken down by type (PF private/varejo, PJ
  financeira/não-financeira, banco, corretora).

### Added — period discovery via HTML scrape

- **`findata.sources.cvm.list_files / list_periods / latest_period`** —
  scrapes `https://dados.cvm.gov.br/dados/<cat>/<product>/DADOS/`
  directly so we don't hard-code year ranges that go stale. New
  `/cvm/funds/periods?product=...` route exposes it.
- Pattern lifted from `gabrielguarisa/brdata`'s `_get_table_links`,
  reimplemented async-native against our shared httpx client.

### Added — CLI

- `findata cvm holdings <CNPJ> -y YYYY -m MM [--blocks BLC_1,BLC_4]`
- `findata cvm lamina <CNPJ> -y YYYY -m MM`
- `findata cvm profile <CNPJ> -y YYYY -m MM`

### Tests

- `tests/test_cvm_funds.py` — 9 respx-mocked tests covering directory
  listing, block-label decoding, CDA filter + whitelist, lâmina main +
  monthly + yearly returns, perfil filter + no-filter passthrough.
- 57 unit tests pass total (was 48). ruff + mypy --strict clean.

### Live smoke

Validated end-to-end against real CVM with `00.280.302/0001-60`
(Bradesco H FIF — Crédito Privado): 6 holdings (R$ 270M concentrados em
cotas de outros fundos), lâmina com objetivo CDI + 0% alavancagem, 1491
cotistas PF varejo + 50 PJ varejo + 24 PF private.

### Added — ANBIMA as a public-data source

- **`findata.sources.anbima`** — covers IMA family snapshot (IRF-M, IMA-B,
  IMA-S, IMA-Geral, with sub-indices like `IRF-M 1+`, `IMA-B 5`, etc.), the
  ETTJ zero-coupon yield curve (Pré, IPCA, inflação implícita per vértice),
  and daily debentures secondary-market quotes.
- Implementation reads ANBIMA's free static files at
  `www.anbima.com.br/informacoes/*` (XLS / CSV / TXT). No credentials, no
  API keys, no cadastro institucional — same canonical numbers as ANBIMA's
  commercial Sensedia API, just delivered as files.
- **Rotas:** `/anbima/{ima,ettj,debentures}`, all public.
- **CLI:** `findata anbima {ima,ettj,debentures}` (with `--family`,
  `--date`, `--emissor` filters).
- **`xlrd>=2.0.1`** added as a core dependency to parse the legacy `.xls`
  files ANBIMA still publishes.

### Added — auth framework (groundwork for future credentialed sources)

- **`findata.auth`** module — generic `OAuth2ClientCredentials` flow with
  in-process token cache and customisable header conventions for non-spec
  gateways (Sensedia, etc.). Surfaces `AuthError` and
  `MissingCredentialsError` for callers.
- The framework is intentionally unused by the current ANBIMA integration
  (which is fully public). It stays in the codebase for future sources
  that genuinely require auth — SUSEP, BNDES, CETIP, etc. The recipe for
  contributors is documented in `docs/SOURCES_WITH_AUTH.md`.

### Background

We initially shipped ANBIMA as an authenticated integration, validated the
OAuth2 flow live, but discovered ANBIMA's developer programme isn't
self-serve — it requires institutional membership or a commercial contract.
We pivoted to the equivalent public file feeds, which give the same data
without gating. The auth scaffolding stays so the next genuinely
credentialed source ships in hours rather than days.

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
