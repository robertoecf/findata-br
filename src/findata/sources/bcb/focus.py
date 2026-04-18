"""BCB Focus/Expectativas — Market consensus forecasts via Olinda/OData.

Public API, no auth. Weekly survey of ~130 financial institutions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from findata.http_client import get_json

BASE_URL = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata"

FOCUS_INDICATORS = [
    "IPCA", "IGP-DI", "IGP-M", "INPC", "IPA-DI", "IPA-M",
    "Câmbio", "PIB Total", "Produção industrial", "Selic",
    "Taxa de desocupação", "Balança comercial", "Conta corrente",
    "Investimento direto no país", "Dívida líquida do setor público",
]


def _validate_indicator(indicator: str) -> str:
    """Validate against known list to prevent OData injection."""
    for known in FOCUS_INDICATORS:
        if known.upper() == indicator.upper():
            return known
    raise ValueError(
        f"Unknown indicator '{indicator}'. Available: {', '.join(FOCUS_INDICATORS)}"
    )


class FocusExpectation(BaseModel):
    indicador: str
    data: str
    data_referencia: str
    media: float | None = None
    mediana: float | None = None
    desvio_padrao: float | None = None
    minimo: float | None = None
    maximo: float | None = None
    numero_respondentes: int | None = None
    base_calculo: int | None = None


class FocusSelic(BaseModel):
    indicador: str
    data: str
    reuniao: str
    media: float | None = None
    mediana: float | None = None
    minimo: float | None = None
    maximo: float | None = None


def _parse_odata(raw: dict[str, Any], model: type[BaseModel], mapping: dict[str, str]) -> list:
    """Generic OData value→Pydantic parser. Eliminates per-endpoint parsers."""
    return [
        model(**{local: item.get(remote) for local, remote in mapping.items()})
        for item in raw.get("value", [])
    ]


_EXPECTATION_MAP = {
    "indicador": "Indicador", "data": "Data",
    "data_referencia": "DataReferencia", "media": "Media",
    "mediana": "Mediana", "desvio_padrao": "DesvioPadrao",
    "minimo": "Minimo", "maximo": "Maximo",
    "numero_respondentes": "numeroRespondentes", "base_calculo": "baseCalculo",
}

_SELIC_MAP = {
    "indicador": "Indicador", "data": "Data", "reuniao": "Reuniao",
    "media": "Media", "mediana": "Mediana", "minimo": "Minimo", "maximo": "Maximo",
}


# ── Single parameterized fetcher replaces 3 copy-paste functions ──


async def _fetch_expectations(
    endpoint: str, indicator: str, top: int,
) -> list[FocusExpectation]:
    safe = _validate_indicator(indicator)
    raw = await get_json(f"{BASE_URL}/{endpoint}", {
        "$top": str(top), "$format": "json",
        "$orderby": "Data desc", "$filter": f"Indicador eq '{safe}'",
    })
    results = _parse_odata(raw, FocusExpectation, _EXPECTATION_MAP)
    # DataReferencia comes as int/str depending on endpoint — normalize
    for r in results:
        r.data_referencia = str(r.data_referencia)
    return results


async def get_focus_annual(indicator: str = "IPCA", top: int = 20) -> list[FocusExpectation]:
    return await _fetch_expectations("ExpectativasMercadoAnuais", indicator, top)


async def get_focus_monthly(indicator: str = "IPCA", top: int = 20) -> list[FocusExpectation]:
    # Singular "Expectativa" — BCB naming inconsistency
    return await _fetch_expectations("ExpectativaMercadoMensais", indicator, top)


async def get_focus_top5_annual(indicator: str = "IPCA", top: int = 20) -> list[FocusExpectation]:
    return await _fetch_expectations("ExpectativasMercadoTop5Anuais", indicator, top)


async def get_focus_selic(top: int = 20) -> list[FocusSelic]:
    raw = await get_json(f"{BASE_URL}/ExpectativasMercadoSelic", {
        "$top": str(top), "$format": "json", "$orderby": "Data desc",
    })
    return _parse_odata(raw, FocusSelic, _SELIC_MAP)
