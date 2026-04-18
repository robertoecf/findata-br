"""IBGE Agregados API — Economic indicators with granular breakdowns.

Base URL: https://servicodados.ibge.gov.br/api/v3/agregados
No auth required. JSON format. Free.

The IBGE API provides IPCA breakdowns by category (9 groups, 365 sub-items),
GDP components, employment, and other economic series that BCB doesn't have.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from findata.http_client import get_json

BASE_URL = "https://servicodados.ibge.gov.br/api/v3/agregados"

# Key aggregate IDs and their variables
IBGE_INDICATORS: dict[str, dict[str, Any]] = {
    "ipca_mensal": {
        "agregado": 7060,
        "variavel": 63,  # Variação mensal (%)
        "description": "IPCA variação mensal por grupo",
        "classificacao": "315",  # Geral, grupos e subgrupos
    },
    "ipca_acumulado_ano": {
        "agregado": 7060,
        "variavel": 69,  # Variação acumulada no ano (%)
        "description": "IPCA acumulado no ano por grupo",
        "classificacao": "315",
    },
    "ipca_acumulado_12m": {
        "agregado": 7060,
        "variavel": 2265,  # Variação acumulada em 12 meses (%)
        "description": "IPCA acumulado 12 meses por grupo",
        "classificacao": "315",
    },
    "ipca_peso": {
        "agregado": 7060,
        "variavel": 66,  # Peso mensal
        "description": "IPCA peso mensal por grupo",
        "classificacao": "315",
    },
    "inpc_mensal": {
        "agregado": 7063,
        "variavel": 44,
        "description": "INPC variação mensal",
        "classificacao": "315",
    },
    "pib_trimestral": {
        "agregado": 5932,
        "variavel": 6561,  # Taxa acumulada em 4 trimestres (%)
        "description": "PIB taxa acumulada em 4 trimestres",
    },
}

# IPCA major groups (classificação 315)
IPCA_GROUPS = {
    "7169": "Índice geral",
    "7170": "1.Alimentação e bebidas",
    "7445": "2.Habitação",
    "7486": "3.Artigos de residência",
    "7558": "4.Vestuário",
    "7625": "5.Transportes",
    "7660": "6.Saúde e cuidados pessoais",
    "7712": "7.Despesas pessoais",
    "7766": "8.Educação",
    "7786": "9.Comunicação",
}


class IBGEDataPoint(BaseModel):
    periodo: str  # YYYYMM format
    valor: float | None
    localidade: str
    variavel: str
    classificacao: str | None = None  # Group/category name


async def get_indicator(
    name: str,
    periods: int = 12,
    localidade: str = "N1[all]",  # N1=Brasil, N3=State, N6=Municipality
) -> list[IBGEDataPoint]:
    """Get an IBGE economic indicator by name.

    Args:
        name: Indicator name from IBGE_INDICATORS catalog.
        periods: Number of recent periods to fetch.
        localidade: Geographic level (N1=Brasil, N3[33]=RJ, etc.).
    """
    if name not in IBGE_INDICATORS:
        available = ", ".join(sorted(IBGE_INDICATORS.keys()))
        raise ValueError(f"Unknown indicator '{name}'. Available: {available}")

    info = IBGE_INDICATORS[name]
    agregado = info["agregado"]
    variavel = info["variavel"]

    url = (
        f"{BASE_URL}/{agregado}/periodos/-{periods}"
        f"/variaveis/{variavel}"
    )
    params = {"localidades": localidade}

    raw = await get_json(url, params, cache_ttl=3600)
    return _parse_response(raw)


async def get_ipca_breakdown(
    periods: int = 6,
    groups: list[str] | None = None,
) -> list[IBGEDataPoint]:
    """Get IPCA monthly variation broken down by major groups.

    This is unique data that BCB SGS doesn't provide — the full IPCA
    breakdown by category (food, housing, transport, health, etc.).

    Args:
        periods: Number of recent months.
        groups: List of group codes from IPCA_GROUPS. Default: all 10 groups.
    """
    if groups is None:
        groups = list(IPCA_GROUPS.keys())

    group_str = ",".join(groups)
    url = (
        f"{BASE_URL}/7060/periodos/-{periods}"
        f"/variaveis/63"
    )
    params = {
        "localidades": "N1[all]",
        "classificacao": f"315[{group_str}]",
    }

    raw = await get_json(url, params, cache_ttl=3600)
    return _parse_response(raw)


def _parse_response(raw: Any) -> list[IBGEDataPoint]:
    """Parse IBGE Agregados API response.

    The response format is complex:
    [
      {
        "id": "63",
        "variavel": "IPCA - Variação mensal",
        "resultados": [
          {
            "classificacoes": [...],
            "series": [
              {
                "localidade": {"id": "1", "nome": "Brasil"},
                "serie": {"202601": "0.56", "202602": "1.31", ...}
              }
            ]
          }
        ]
      }
    ]
    """
    results = []
    for var_block in raw:
        variavel_name = var_block.get("variavel", "")
        for resultado in var_block.get("resultados", []):
            # Get classification name if present
            classif_name = None
            for classif in resultado.get("classificacoes", []):
                for cat in classif.get("categoria", {}).values():
                    classif_name = cat

            for serie in resultado.get("series", []):
                loc = serie.get("localidade", {}).get("nome", "Brasil")
                for periodo, valor_str in serie.get("serie", {}).items():
                    try:
                        valor = float(valor_str) if valor_str and valor_str != "..." else None
                    except (ValueError, TypeError):
                        valor = None
                    results.append(
                        IBGEDataPoint(
                            periodo=periodo,
                            valor=valor,
                            localidade=loc,
                            variavel=variavel_name,
                            classificacao=classif_name,
                        )
                    )
    return results
