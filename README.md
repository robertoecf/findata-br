<!-- markdownlint-disable MD033 MD041 -->

```text
 ███████╗██╗███╗   ██╗██████╗  █████╗ ████████╗ █████╗        ██████╗ ██████╗
 ██╔════╝██║████╗  ██║██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗       ██╔══██╗██╔══██╗
 █████╗  ██║██╔██╗ ██║██║  ██║███████║   ██║   ███████║ █████╗██████╔╝██████╔╝
 ██╔══╝  ██║██║╚██╗██║██║  ██║██╔══██║   ██║   ██╔══██║ ╚════╝██╔══██╗██╔══██╗
 ██║     ██║██║ ╚████║██████╔╝██║  ██║   ██║   ██║  ██║       ██████╔╝██║  ██║
 ╚═╝     ╚═╝╚═╝  ╚═══╝╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝       ╚═════╝ ╚═╝  ╚═╝

                   Dados financeiros abertos do Brasil
        BCB · CVM · B3 · IBGE · IPEA · Tesouro  →  API + MCP + CLI
```

<div align="center">

**API + servidor MCP + CLI open-source para dados financeiros brasileiros.**

_Agrega dados públicos de BCB, CVM, B3, IBGE, IPEA e Tesouro Nacional._
_De graça. Sem API key. Sem truques de rate-limit. Só Python._

<p>
  <a href="https://github.com/robertoecf/findata-br/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/robertoecf/findata-br/ci.yml?branch=main&label=CI&logo=github"></a>
  <img alt="Versão" src="https://img.shields.io/badge/versão-0.1.0--alpha-009c3b">
  <img alt="Python" src="https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue?logo=python&logoColor=white">
  <a href="https://github.com/robertoecf/findata-br/blob/main/LICENSE"><img alt="Licença MIT" src="https://img.shields.io/badge/licença-MIT-yellow.svg"></a>
  <img alt="Status" src="https://img.shields.io/badge/status-alpha-orange">
</p>

</div>

---

## ✨ O que você ganha

- **API REST** com Swagger interativo em `/docs`.
- **Servidor MCP** montado automaticamente em `/mcp` — plugue o findata-br direto no Claude, Cursor, Codex.
- **CLI Python** (`findata ...`) com tabelas ricas e banner animado em TTY.
- **Biblioteca async** com connection pooling, retry com backoff exponencial e cache LRU de 15 min.
- **Zero autenticação, zero API keys.** Todas as fontes são dados públicos governamentais.

## 📊 Fontes de dados

| Fonte | Domínio | Cobertura | Auth |
|---|---|---|---|
| **BCB SGS** | Banco Central | Selic, CDI, IPCA, IGP-M, câmbio, PIB, desemprego — 18k+ séries temporais | — |
| **BCB Olinda PTAX** | Banco Central | USD/BRL, EUR/BRL e todas moedas rastreadas; ponto e período | — |
| **BCB Olinda Focus** | Banco Central | Boletim Focus (semanal) — anual, mensal, Selic, Top-5 | — |
| **CVM** | Regulador | Empresas registradas, demonstrações DFP/ITR, catálogo de fundos, cota diária de fundos | — |
| **IBGE Agregados v3** | Instituto de estatística | IPCA detalhado por 10 grupos + 365 subitens, INPC, PIB trimestral | — |
| **IPEA Data (OData v4)** | Instituto de pesquisa | ~8k séries macro curadas (histórico desde a década de 1940), busca no catálogo, metadados | — |
| **Tesouro Transparente** | Tesouro Nacional | Tesouro Direto — preços e taxas históricos | — |
| **B3** (opcional, via `yfinance`) | Bolsa | Cotações atuais e histórico OHLC de tickers BOVESPA | — |

## 🚀 Instalação

```bash
# Core (BCB, CVM, IBGE, IPEA, Tesouro)
pip install findata-br

# Com cotações da B3
pip install 'findata-br[b3]'
```

> Desenvolvimento local: `pip install -e '.[dev]'`

## 🔧 Uso

### CLI

```bash
findata bcb series              # catálogo de séries nomeadas
findata bcb get selic -n 10     # últimos 10 valores da Selic
findata bcb get ipca            # IPCA mensal
findata bcb ptax                # USD/BRL de hoje
findata bcb focus -i IPCA -n 5  # expectativas do Focus

findata tesouro search IPCA+
findata tesouro history "Tesouro IPCA+ 2035" -n 30

findata ibge ipca -n 6          # IPCA quebrado por grupo

findata ipea catalog            # séries IPEA curadas
findata ipea search desemprego  # busca full-text em ~8k séries
findata ipea get BM12_TJOVER12 -n 12

findata cvm search Petrobras

findata b3 quote PETR4          # requer o extra [b3]
findata b3 history VALE3 -p 1y

findata serve                   # sobe o servidor HTTP + MCP
```

### Biblioteca Python

```python
import asyncio
from findata.sources.bcb import sgs, ptax, focus
from findata.sources.ipea import get_series_values

async def main() -> None:
    selic = await sgs.get_series_by_name("selic", n=5)
    print(selic)

    usd = await ptax.get_ptax_usd()  # hoje
    print(usd)

    ipca_expect = await focus.get_focus_annual("IPCA", top=3)
    print(ipca_expect)

    # Selic over mensal do IPEA (série desde 1974)
    hist = await get_series_values("BM12_TJOVER12", top=12)
    print(hist)

asyncio.run(main())
```

### API REST

```bash
findata serve                # http://localhost:8000
curl http://localhost:8000/bcb/series/name/selic?n=5
curl 'http://localhost:8000/bcb/focus/annual?indicator=IPCA&top=3'
curl http://localhost:8000/docs     # Swagger UI
curl http://localhost:8000/redoc    # ReDoc
```

### Servidor MCP

O endpoint MCP é gerado automaticamente a partir das rotas FastAPI. Qualquer
cliente MCP (Claude Desktop, Cursor, Codex, Continue) consegue conectar em
`http://<host>:<port>/mcp` e chamar todos os endpoints do findata como
ferramentas.

```jsonc
// Exemplo de configuração de cliente MCP
{
  "mcpServers": {
    "findata-br": { "url": "http://localhost:8000/mcp" }
  }
}
```

### 🌎 Rodando como MCP server público

Quer compartilhar sua instância com a comunidade? O guia
[**docs/DEPLOY_PUBLIC.md**](docs/DEPLOY_PUBLIC.md) mostra como subir o
findata-br no seu PC/WSL com **Cloudflare Tunnel** em ~20 min, custo R$ 0:
HTTPS automático, URL fixa, DDoS protegido, rate-limit embutido. Quando a
URL pública estiver no ar, qualquer pessoa pode apontar o Claude Desktop /
Cursor / Codex pra ela e usar as 27 rotas como tools MCP.

- Rate limit configurável via env: `FINDATA_RATE_LIMIT_DEFAULT="60/minute;1000/day"`.
- `/health`, `/stats` e Swagger em `/docs` — observabilidade out-of-the-box.
- `deploy/docker-compose.prod.yml` e `deploy/findata-br.service` prontos pra produção.

## 🏗️ Arquitetura

```
 findata/
 ├─ http_client.py        ← cliente async httpx c/ cache, retry, URLs OData-safe
 ├─ banner.py             ← banner animado da CLI
 ├─ cli.py                ← app Typer
 ├─ api/
 │   ├─ app.py            ← FastAPI + mount do MCP
 │   └─ routers/          ← um router por fonte
 └─ sources/
     ├─ bcb/   (sgs, ptax, focus)
     ├─ cvm/   (companies, financials, funds, parser)
     ├─ ibge/  (indicators)
     ├─ ipea/  (series)
     ├─ tesouro/ (bonds)
     └─ b3/    (quotes)       ← opcional, atrás do extras
```

Cada fonte é um wrapper async tipado e enxuto sobre o endpoint público oficial.
Todas compartilham `http_client.get_json` / `get_bytes` — assim pooling, retry
e cache ficam centralizados em um único lugar.

## 🧪 Testes

```bash
pytest                       # unit + API rápidos (sem rede)
pytest -m integration        # bate nas APIs públicas reais
pytest -m ""                 # roda tudo
```

Os testes de integração são pulados por padrão — dependem de acesso à rede e
do uptime dos terceiros. Atualmente o projeto tem **34 unit + 15 integration
tests**, todos verdes.

## 🗺️ Roadmap — próximos passos

- **Deploy** — Dockerfile + `docker-compose` para servidor local em um comando.
- **CI/CD** — GitHub Actions em cada push; publicação no PyPI em tag.
- **Rate limiting** — middleware `slowapi` (para deploys públicos).
- **Observabilidade** — logs JSON estruturados, `/metrics` (Prometheus), OpenTelemetry opcional.
- **ANBIMA** — índices IMA, IMA-B, IDkA, IHFA.
- **B3 nativo** — raspar os arquivos oficiais da B3 (índices, COTAHIST) pra soltar a dependência de `yfinance`.
- **Expansão IBGE** — PNAD Contínua, produção industrial, comércio varejista, confiança.
- **Cache Redis** — opt-in para cache distribuído em deploys multi-réplica.
- **SDK TypeScript** — cliente gerado a partir do OpenAPI.

## 🌱 Comunidade

findata-br é **open-source pra durar** — MIT, sem CLA, sem adotar upstream
comercial. O roadmap depende de quem usa: se você sentir falta de uma fonte
(ANBIMA, SUSEP, BNDES, ...), abra uma
[issue usando o template "Nova fonte"](https://github.com/robertoecf/findata-br/issues/new?template=new-source.yml).

Qualquer desenvolvedor brasileiro interessado em dados financeiros abertos é
convidado a hospedar sua própria instância pública e colaborar com PRs.

## 🤝 Contribuindo

Guia completo em [CONTRIBUTING.md](CONTRIBUTING.md). TL;DR:

```bash
pip install -e '.[dev]'
bash scripts/git/install-hooks.sh   # habilita pre-commit + pre-push
ruff check src tests                # lint (core + AI guardrails)
mypy src                            # type check estrito
pytest                              # unit + API (sem rede)
```

Mantenha as mudanças tipadas (`mypy --strict`), linted (`ruff check`) e
cobertas por testes. Para novas fontes, adicione testes de integração em
`tests/test_integration.py` (marcador `integration`). Para o resto, prefira
unit tests com `respx` que não batem em rede.

## 📜 Licença

[MIT](LICENSE) — use como quiser.

<div align="center">
<sub>Feito com ❤️ para o ecossistema de dados abertos do Brasil.</sub>
</div>
