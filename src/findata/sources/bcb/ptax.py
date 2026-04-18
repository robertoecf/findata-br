"""BCB PTAX — Exchange rates via Olinda/OData.

Public API, no auth. Date format: MM-DD-YYYY (not DD/MM/YYYY like SGS).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel

from findata.http_client import get_json

BASE_URL = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata"


class PTAXQuote(BaseModel):
    cotacao_compra: float
    cotacao_venda: float
    data_hora_cotacao: str


class Currency(BaseModel):
    simbolo: str
    nome: str
    tipo_moeda: str


def _fmt(d: date) -> str:
    return d.strftime("%m-%d-%Y")


def _parse_quotes(raw: dict[str, Any]) -> list[PTAXQuote]:
    return [
        PTAXQuote(
            cotacao_compra=item["cotacaoCompra"],
            cotacao_venda=item["cotacaoVenda"],
            data_hora_cotacao=item["dataHoraCotacao"],
        )
        for item in raw.get("value", [])
    ]


async def get_ptax_usd(d: date | None = None) -> list[PTAXQuote]:
    """USD/BRL PTAX for a date. Empty list on weekends/holidays."""
    dt = _fmt(d or date.today())
    raw = await get_json(
        f"{BASE_URL}/CotacaoDolarDia(dataCotacao=@dataCotacao)",
        {"@dataCotacao": f"'{dt}'", "$format": "json"},
    )
    return _parse_quotes(raw)


async def get_ptax_usd_period(start: date, end: date) -> list[PTAXQuote]:
    """USD/BRL PTAX for a date range."""
    raw = await get_json(
        f"{BASE_URL}/CotacaoDolarPeriodo("
        f"dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)",
        {
            "@dataInicial": f"'{_fmt(start)}'",
            "@dataFinalCotacao": f"'{_fmt(end)}'",
            "$format": "json",
        },
    )
    return _parse_quotes(raw)


async def get_ptax_currency(currency: str, d: date | None = None) -> list[PTAXQuote]:
    """PTAX for any currency (EUR, GBP, JPY, etc.)."""
    dt = _fmt(d or date.today())
    raw = await get_json(
        f"{BASE_URL}/CotacaoMoedaDia(moeda=@moeda,dataCotacao=@dataCotacao)",
        {"@moeda": f"'{currency.upper()}'", "@dataCotacao": f"'{dt}'", "$format": "json"},
    )
    return _parse_quotes(raw)


async def get_currencies() -> list[Currency]:
    raw = await get_json(f"{BASE_URL}/Moedas", {"$format": "json"})
    return [
        Currency(simbolo=c["simbolo"], nome=c["nomeFormatado"], tipo_moeda=c["tipoMoeda"])
        for c in raw.get("value", [])
    ]
