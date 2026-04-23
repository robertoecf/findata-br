<!-- markdownlint-disable MD033 MD041 -->
<div align="center">

<!-- Typing SVG banner — renders the "FINDATA-BR" title as an animated typewriter
     on GitHub. Powered by readme-typing-svg.demolab.com (public, free). -->
<a href="https://github.com/robertoecf/findata-br">
  <img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=700&size=44&duration=2800&pause=900&color=009C3B&center=true&vCenter=true&width=760&height=80&lines=FINDATA-BR;Dados+abertos+do+Brasil;BCB+·+CVM+·+B3+·+IBGE+·+IPEA+·+Tesouro" alt="FINDATA-BR" />
</a>

<p><strong>Open-source Brazilian financial data — API + MCP server + CLI.</strong></p>
<p>
  <em>Aggregates public data from BCB, CVM, B3, IBGE, and Tesouro Nacional.</em><br/>
  <em>Free. No API key. No rate-limiting tricks. Just Python.</em>
</p>

<p>
  <a href="https://github.com/robertoecf/findata-br/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/robertoecf/findata-br/ci.yml?branch=main&label=CI&logo=github"></a>
  <a href="https://pypi.org/project/findata-br/"><img alt="PyPI" src="https://img.shields.io/pypi/v/findata-br?color=009c3b&logo=pypi&logoColor=white"></a>
  <img alt="Python" src="https://img.shields.io/pypi/pyversions/findata-br?logo=python&logoColor=white">
  <a href="https://github.com/robertoecf/findata-br/blob/main/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-yellow.svg"></a>
  <img alt="Status" src="https://img.shields.io/badge/status-alpha-orange">
</p>

</div>

---

## ✨ What you get

- **REST API** with interactive Swagger docs at `/docs`.
- **MCP server** auto-mounted at `/mcp` — plug findata-br directly into Claude, Cursor, Codex.
- **Python CLI** (`findata ...`) with rich tables and an animated TTY banner.
- **Async Python library** with connection pooling, retries with exponential backoff, and a 15-minute LRU cache.
- **Zero auth, zero API keys.** All sources are public government data.

## 📊 Data sources

| Source | Domain | Coverage | Auth |
|---|---|---|---|
| **BCB SGS** | Banco Central | Selic, CDI, IPCA, IGP-M, câmbio, PIB, desemprego — 18k+ time series | — |
| **BCB Olinda PTAX** | Banco Central | USD/BRL, EUR/BRL, and all tracked currencies; daily + period | — |
| **BCB Olinda Focus** | Banco Central | Boletim Focus (weekly) — annual, monthly, Selic, Top-5 | — |
| **CVM** | Regulator | Registered companies, DFP/ITR financial statements, investment funds catalog, daily fund NAV | — |
| **IBGE Agregados v3** | Stats agency | IPCA breakdown by 10 groups + 365 sub-items, INPC, PIB trimestral | — |
| **IPEA Data (OData v4)** | Applied research institute | ~8k curated macro series (long history back to 1940s), catalog search, metadata | — |
| **Tesouro Transparente** | National Treasury | Tesouro Direto — historical prices and rates | — |
| **B3** (optional, via `yfinance`) | Stock exchange | Current quotes, OHLC history for BOVESPA tickers | — |

## 🚀 Install

```bash
# Core (BCB, CVM, IBGE, Tesouro)
pip install findata-br

# With B3 stock quotes
pip install 'findata-br[b3]'
```

> Repo-local development: `pip install -e '.[dev]'`

## 🔧 Usage

### CLI

```bash
findata bcb series              # catalog of named series
findata bcb get selic -n 10     # last 10 Selic values
findata bcb get ipca            # monthly IPCA
findata bcb ptax                # today's USD/BRL
findata bcb focus -i IPCA -n 5  # Focus expectations

findata tesouro search IPCA+
findata tesouro history "Tesouro IPCA+ 2035" -n 30

findata ibge ipca -n 6          # IPCA broken down by group

findata ipea catalog            # curated IPEA series
findata ipea search desemprego  # full-text search across ~8k series
findata ipea get BM12_TJOVER12 -n 12

findata cvm search Petrobras

findata b3 quote PETR4          # needs [b3] extra
findata b3 history VALE3 -p 1y

findata serve                   # fires up the HTTP + MCP server
```

### Python library

```python
import asyncio
from findata.sources.bcb import sgs, ptax, focus

async def main() -> None:
    selic = await sgs.get_series_by_name("selic", n=5)
    print(selic)

    usd = await ptax.get_ptax_usd()  # today
    print(usd)

    ipca_expect = await focus.get_focus_annual("IPCA", top=3)
    print(ipca_expect)

asyncio.run(main())
```

### REST API

```bash
findata serve                # http://localhost:8000
curl http://localhost:8000/bcb/series/name/selic?n=5
curl 'http://localhost:8000/bcb/focus/annual?indicator=IPCA&top=3'
curl http://localhost:8000/docs     # Swagger UI
curl http://localhost:8000/redoc    # ReDoc
```

### MCP server

The MCP endpoint is auto-generated from the FastAPI routes. Any MCP-aware
client (Claude Desktop, Cursor, Codex, Continue) can connect to
`http://<host>:<port>/mcp` and automatically call all findata endpoints as
tools.

```jsonc
// Example MCP client config
{
  "mcpServers": {
    "findata-br": { "url": "http://localhost:8000/mcp" }
  }
}
```

## 🏗️ Architecture

```
 findata/
 ├─ http_client.py        ← async httpx client w/ cache, retry, OData-safe URLs
 ├─ banner.py             ← animated CLI banner
 ├─ cli.py                ← Typer app
 ├─ api/
 │   ├─ app.py            ← FastAPI app + MCP mount
 │   └─ routers/          ← one router per source
 └─ sources/
     ├─ bcb/   (sgs, ptax, focus)
     ├─ cvm/   (companies, financials, funds, parser)
     ├─ ibge/  (indicators)
     ├─ tesouro/ (bonds)
     └─ b3/    (quotes)       ← optional, gated by extras
```

Each source is a thin, typed async wrapper over the official public endpoint.
They all share `http_client.get_json` / `get_bytes` for pooling, retries, and
caching, so HTTP concerns are centralised.

## 🧪 Tests

```bash
pytest                       # fast unit + API tests (no network)
pytest -m integration        # hit the live public APIs
pytest -m ""                 # run everything
```

Integration tests are skipped by default — they depend on network access and
third-party uptime.

## 🗺️ Roadmap — next steps

- **Deploy** — Dockerfile + `docker-compose` for one-command local server.
- **CI/CD** — GitHub Actions on every push; publish to PyPI on tag.
- **Rate limiting** — `slowapi` middleware (public deployments).
- **Observability** — structured JSON logs, `/metrics` (Prometheus), optional OpenTelemetry.
- **ANBIMA** — IMA, IMA-B, IDkA, IHFA indexes.
- **B3 native** — scrape official B3 files (indexes, closing prices) to drop the `yfinance` dependency.
- **IBGE expansion** — PNAD, produção industrial, comércio, confiança.
- **Redis cache** — opt-in distributed cache for multi-replica deploys.
- **SDK typings** — publish a TypeScript client generated from the OpenAPI spec.

## 🤝 Contributing

PRs welcome. Keep changes typed (`mypy --strict`), linted (`ruff check`), and
covered by tests. Integration tests should only be added for new sources —
unit tests with `respx` are preferred for anything testable without the
network.

```bash
pip install -e '.[dev]'
ruff check src tests
mypy src
pytest
```

## 📜 License

[MIT](LICENSE) — use it however you like.

<div align="center">
<sub>Built with ❤️ for the Brazilian open-data ecosystem.</sub>
</div>
