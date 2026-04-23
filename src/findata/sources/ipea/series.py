"""IPEA Data OData v4 API — macroeconomic series by SERCODIGO."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from findata.http_client import get_json

# IPEA hosts OData over plain HTTP — HTTPS is not advertised by the service
# (as of 2026-04). See ipeadata.gov.br/api
BASE_URL = "http://www.ipeadata.gov.br/api/odata4"


class IPEADataPoint(BaseModel):
    sercodigo: str
    data: str  # ISO 8601 (e.g., "2026-03-01T00:00:00-03:00")
    valor: float | None = None


class IPEAMetadata(BaseModel):
    sercodigo: str
    sernome: str
    sercomentario: str | None = None
    serunidade: str | None = None
    serperiodicidade: str | None = None
    sertema: str | None = None
    serfonte: str | None = None
    seratualizacao: str | None = None
    seratualizador: str | None = None


# Curated catalog of useful series. Full catalog has ~8k; these are the ones
# that complement BCB SGS / IBGE with longer history or unique coverage.
IPEA_CATALOG: dict[str, dict[str, str]] = {
    "selic_over_mensal": {
        "code": "BM12_TJOVER12",
        "description": "Taxa Selic over acumulada no mês",
        "unidade": "% a.m.",
        "periodicidade": "mensal",
    },
    "ipca_anual_ipea": {
        "code": "PAN12_IPCAG12",
        "description": "IPCA acumulado 12 meses (IPEA)",
        "unidade": "% a.a.",
        "periodicidade": "mensal",
    },
    "pib_real_anual": {
        "code": "SCN10_PIBG10",
        "description": "PIB - variação real anual (IBGE/SCN)",
        "unidade": "% a.a.",
        "periodicidade": "anual",
    },
    "desemprego_pme": {
        "code": "PME12_TDESOC12",
        "description": "Taxa de desocupação - PME (série longa, descontinuada em 2016)",
        "unidade": "%",
        "periodicidade": "mensal",
    },
    "salario_minimo_real": {
        "code": "GAC12_SALMINRE12",
        "description": "Salário mínimo real (base=jul/1994)",
        "unidade": "R$",
        "periodicidade": "mensal",
    },
    "divida_externa_pib": {
        "code": "BM12_DEXTT12",
        "description": "Dívida externa / PIB",
        "unidade": "% do PIB",
        "periodicidade": "mensal",
    },
}


def _parse_values(raw: dict[str, Any]) -> list[IPEADataPoint]:
    results: list[IPEADataPoint] = []
    for item in raw.get("value", []):
        try:
            valor = item.get("VALVALOR")
            valor_f = float(valor) if valor is not None else None
        except (TypeError, ValueError):
            valor_f = None
        results.append(
            IPEADataPoint(
                sercodigo=item.get("SERCODIGO", ""),
                data=item.get("VALDATA", ""),
                valor=valor_f,
            )
        )
    return results


def _parse_metadata(item: dict[str, Any]) -> IPEAMetadata:
    return IPEAMetadata(
        sercodigo=item.get("SERCODIGO", ""),
        sernome=item.get("SERNOME", ""),
        sercomentario=item.get("SERCOMENTARIO"),
        serunidade=item.get("UNINOME"),
        serperiodicidade=item.get("PERNOME"),
        sertema=item.get("TEMNOME"),
        serfonte=item.get("FNTNOME"),
        seratualizacao=item.get("SERATUALIZACAO"),
        seratualizador=item.get("BASNOME"),
    )


async def get_series_values(
    sercodigo: str,
    top: int | None = None,
) -> list[IPEADataPoint]:
    """Fetch values for an IPEA series by SERCODIGO.

    Args:
        sercodigo: Series code (e.g., 'BM12_TJOVER12' for monthly Selic over).
        top: Optional cap on number of most-recent rows returned.

    Note: IPEA's OData `ValoresSerie(SERCODIGO=...)` route ignores `$top` and
    `$orderby` server-side, so we slice/sort the full series client-side.
    Series are typically small (hundreds of rows) so this is cheap and the
    LRU cache keeps it cheaper.
    """
    url = f"{BASE_URL}/ValoresSerie(SERCODIGO='{sercodigo}')"
    raw = await get_json(url, cache_ttl=3600)
    points = _parse_values(raw)
    if top is not None:
        points = sorted(points, key=lambda p: p.data, reverse=True)[:top]
    return points


async def get_metadata(sercodigo: str) -> IPEAMetadata | None:
    """Fetch metadata for an IPEA series (name, unit, periodicity, source)."""
    url = f"{BASE_URL}/Metadados('{sercodigo}')"
    raw = await get_json(url, cache_ttl=86400)  # metadata changes rarely
    items = raw.get("value", [])
    if not items:
        return None
    return _parse_metadata(items[0])


async def search_series(
    query: str,
    top: int = 25,
) -> list[IPEAMetadata]:
    """Full-text search across the IPEA series catalog (name + code).

    IPEA's `/api/odata4/` endpoint actually speaks OData v3 syntax, so we
    use `substringof('needle', field)` rather than v4's `contains(field, 'needle')`.
    String functions like `toupper()` are not supported either — we fake
    case-insensitivity by running a few common casings in a single OR filter.
    """
    q = query.replace("'", "''")
    variants = {q, q.lower(), q.upper(), q.title()}
    filter_parts: list[str] = []
    for v in variants:
        filter_parts.append(f"substringof('{v}', SERNOME)")
        filter_parts.append(f"substringof('{v}', SERCODIGO)")
    f = " or ".join(filter_parts)
    url = f"{BASE_URL}/Metadados"
    raw = await get_json(
        url,
        {"$top": str(max(top * 2, top)), "$filter": f},
        cache_ttl=3600,
    )
    results = [_parse_metadata(item) for item in raw.get("value", [])]
    seen: set[str] = set()
    deduped: list[IPEAMetadata] = []
    for m in results:
        if m.sercodigo not in seen:
            seen.add(m.sercodigo)
            deduped.append(m)
        if len(deduped) >= top:
            break
    return deduped
