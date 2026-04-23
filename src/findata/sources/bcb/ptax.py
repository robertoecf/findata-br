"""BCB PTAX — Exchange rates via Olinda/OData.

Public API, no auth. Date format: MM-DD-YYYY (not DD/MM/YYYY like SGS).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from findata._odata import parse_odata
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


_QUOTE_MAP = {
    "cotacao_compra": "cotacaoCompra",
    "cotacao_venda": "cotacaoVenda",
    "data_hora_cotacao": "dataHoraCotacao",
}

_CURRENCY_MAP = {
    "simbolo": "simbolo",
    "nome": "nomeFormatado",
    "tipo_moeda": "tipoMoeda",
}


async def get_ptax_usd(d: date | None = None) -> list[PTAXQuote]:
    """USD/BRL PTAX for a date. Empty list on weekends/holidays."""
    dt = _fmt(d or date.today())
    raw = await get_json(
        f"{BASE_URL}/CotacaoDolarDia(dataCotacao=@dataCotacao)",
        {"@dataCotacao": f"'{dt}'", "$format": "json"},
    )
    return parse_odata(raw, PTAXQuote, _QUOTE_MAP)


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
    return parse_odata(raw, PTAXQuote, _QUOTE_MAP)


async def get_ptax_currency(currency: str, d: date | None = None) -> list[PTAXQuote]:
    """PTAX for any currency (EUR, GBP, JPY, etc.)."""
    dt = _fmt(d or date.today())
    raw = await get_json(
        f"{BASE_URL}/CotacaoMoedaDia(moeda=@moeda,dataCotacao=@dataCotacao)",
        {"@moeda": f"'{currency.upper()}'", "@dataCotacao": f"'{dt}'", "$format": "json"},
    )
    return parse_odata(raw, PTAXQuote, _QUOTE_MAP)


async def get_currencies() -> list[Currency]:
    """List all currencies available in PTAX."""
    raw = await get_json(f"{BASE_URL}/Moedas", {"$format": "json"})
    return parse_odata(raw, Currency, _CURRENCY_MAP)
