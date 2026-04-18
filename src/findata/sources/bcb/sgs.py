"""BCB SGS (Sistema Gerenciador de Séries Temporais).

Public API, no auth. Docs: dadosabertos.bcb.gov.br
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel

from findata.http_client import get_json

BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"

SERIES_CATALOG: dict[str, dict[str, Any]] = {
    "selic": {"code": 432, "name": "Taxa Selic", "unit": "% a.a.", "freq": "diária"},
    "cdi": {"code": 12, "name": "Taxa CDI", "unit": "% a.a.", "freq": "diária"},
    "cdi_acum_mensal": {
        "code": 4389, "name": "CDI acumulado mensal", "unit": "%", "freq": "mensal",
    },
    "tr": {"code": 226, "name": "Taxa Referencial (TR)", "unit": "%", "freq": "diária"},
    "ipca": {"code": 433, "name": "IPCA mensal", "unit": "%", "freq": "mensal"},
    "ipca_12m": {
        "code": 13522, "name": "IPCA acumulado 12 meses", "unit": "%", "freq": "mensal",
    },
    "ipca_15": {"code": 7478, "name": "IPCA-15", "unit": "%", "freq": "mensal"},
    "igpm": {"code": 189, "name": "IGP-M mensal", "unit": "%", "freq": "mensal"},
    "igpdi": {"code": 190, "name": "IGP-DI mensal", "unit": "%", "freq": "mensal"},
    "inpc": {"code": 188, "name": "INPC mensal", "unit": "%", "freq": "mensal"},
    "dolar_ptax": {"code": 1, "name": "Dólar PTAX venda", "unit": "BRL/USD", "freq": "diária"},
    "euro": {"code": 21619, "name": "Euro PTAX venda", "unit": "BRL/EUR", "freq": "diária"},
    "pib_mensal": {
        "code": 4380, "name": "PIB mensal (IBC-Br)", "unit": "índice", "freq": "mensal",
    },
    "desemprego": {
        "code": 24369, "name": "Taxa de desocupação (PNAD)", "unit": "%", "freq": "mensal",
    },
    "poupanca": {"code": 195, "name": "Rendimento poupança", "unit": "%", "freq": "mensal"},
    "divida_pib": {
        "code": 4513, "name": "Dívida líquida setor público / PIB",
        "unit": "%", "freq": "mensal",
    },
}


class SGSDataPoint(BaseModel):
    data: str  # DD/MM/YYYY
    valor: float


def _parse(raw: list[dict[str, str]]) -> list[SGSDataPoint]:
    results = []
    for item in raw:
        try:
            results.append(SGSDataPoint(data=item["data"], valor=float(item["valor"])))
        except (ValueError, KeyError):
            continue
    return results


async def get_series(
    code: int, start: date | None = None, end: date | None = None,
) -> list[SGSDataPoint]:
    """Fetch a BCB time series by code with optional date range."""
    url = BASE_URL.format(code=code)
    params: dict[str, str] = {"formato": "json"}
    if start:
        params["dataInicial"] = start.strftime("%d/%m/%Y")
    if end:
        params["dataFinal"] = end.strftime("%d/%m/%Y")
    return _parse(await get_json(url, params))


async def get_series_last(code: int, n: int = 10) -> list[SGSDataPoint]:
    """Fetch the last N values of a BCB time series."""
    url = BASE_URL.format(code=code) + f"/ultimos/{n}"
    return _parse(await get_json(url, {"formato": "json"}))


async def get_series_by_name(name: str, n: int = 10) -> list[SGSDataPoint]:
    """Fetch series by catalog name (e.g., 'selic', 'ipca', 'dolar_ptax')."""
    if name not in SERIES_CATALOG:
        raise ValueError(
            f"Unknown series '{name}'. Available: {', '.join(sorted(SERIES_CATALOG))}"
        )
    return await get_series_last(SERIES_CATALOG[name]["code"], n)
