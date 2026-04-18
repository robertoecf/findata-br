# findata-br

Open-source Brazilian financial data API, MCP server, and CLI.

Aggregates public data from BCB, CVM, B3, ANBIMA, and Tesouro Nacional.
Free. No API key required.

## Install

```bash
pip install findata-br
```

## Usage

### CLI
```bash
findata bcb series          # list available series
findata bcb get selic -n 10 # last 10 Selic values
findata bcb ptax            # today's USD/BRL
findata bcb focus           # Focus market expectations
findata serve               # start API + MCP server
```

### API
```bash
findata serve
# http://localhost:8000/docs  — Swagger UI
# http://localhost:8000/mcp   — MCP server
```

### Python
```python
from findata.sources.bcb import sgs

data = await sgs.get_series_by_name("selic", n=10)
```

## Data Sources

| Source | Data | Auth |
|--------|------|------|
| BCB SGS | Selic, IPCA, CDI, câmbio, 18k+ series | None |
| BCB Olinda | PTAX, Focus expectations | None |
| CVM | Companies, DFP/ITR, funds | None |
| B3 | Stock quotes, indices (coming soon) | None |

## License

MIT
