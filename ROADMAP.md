# Roadmap & Next Steps

Status: **v0.1.0 — alpha, release-ready for local/self-hosted use.**

## 🟢 Ready to use right now

- `pip install -e '.[dev]'` → venv with everything.
- `findata serve --host 0.0.0.0 --port 8000` → REST + MCP server.
- `findata bcb get selic -n 10` → CLI access to BCB.
- All unit tests pass (`pytest`), `ruff` and `mypy --strict` clean.

## 🟡 Immediate next steps (pick them up when you hit the WSL server)

1. **Run the server on WSL**
   ```bash
   # in WSL
   git clone https://github.com/robertoecf/findata-br.git
   cd findata-br
   python3 -m venv .venv && . .venv/bin/activate
   pip install -e '.[b3]'
   findata serve --host 0.0.0.0 --port 8000
   ```
   Or Docker: `docker compose up -d`.

2. **Enable GitHub Actions CI**
   The CI workflow is staged at [`.github-pending/ci.yml`](.github-pending/ci.yml)
   because the local `gh` token is missing the `workflow` scope. To enable:
   ```bash
   gh auth refresh -s workflow
   mkdir -p .github/workflows
   mv .github-pending/ci.yml .github/workflows/ci.yml
   rmdir .github-pending
   git add .github && git commit -m "ci: enable GitHub Actions"
   git push
   ```

3. **Publish to PyPI**
   - Reserve the name: <https://pypi.org/project/findata-br/>
   - Create a release: `git tag v0.1.0 && git push --tags`
   - Add a `release.yml` workflow that runs on tags and publishes via
     [trusted publishing](https://docs.pypi.org/trusted-publishers/).

4. **Systemd / process manager on WSL**
   Minimal `findata.service` unit:
   ```ini
   [Unit]
   Description=findata-br
   After=network.target

   [Service]
   Type=simple
   User=yourself
   WorkingDirectory=/srv/findata-br
   ExecStart=/srv/findata-br/.venv/bin/findata serve --host 0.0.0.0 --port 8000 --no-banner
   Restart=on-failure

   [Install]
   WantedBy=multi-user.target
   ```

5. **Expose behind nginx or Caddy** if you want HTTPS. Caddy one-liner:
   ```
   findata.yourdomain.com { reverse_proxy localhost:8000 }
   ```

## 🔵 Feature roadmap (0.2+)

- **Rate limiting** (`slowapi`) when exposing publicly.
- **Observability** — structured JSON logs, `/metrics` (Prometheus exporter),
  optional OpenTelemetry via env vars.
- **Redis cache** — drop-in replacement for the in-memory LRU for multi-replica
  deploys.
- **ANBIMA indexes** — IMA, IMA-B, IDkA, IHFA.
- **B3 native** — scrape official CSVs/COTAHIST to remove the `yfinance` dep.
- **IBGE expansion** — PNAD Contínua, produção industrial, comércio varejista.
- **TypeScript SDK** — generate from the OpenAPI spec.
- **Webhooks / streaming** — SSE for "give me the new PTAX the moment BCB
  publishes it".

## 🧪 Known caveats

- **CVM financial statements (DFP/ITR)** download a multi-hundred-MB ZIP for a
  full year — always pass `cnpj=` when hitting `/cvm/financials/*`.
- **Fund daily NAV** files are ~50 MB/month — same recommendation: filter by
  `cnpj=`.
- **yfinance** is optional. Without the `[b3]` extra installed, `/b3/*`
  returns `503`.
- **fastapi-mcp** is pinned at a minimum version; if your deployment picks up
  a major-version break, `/mcp` is silently disabled but the REST API keeps
  serving.
