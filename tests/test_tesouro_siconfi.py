"""Tesouro SICONFI tests — RREO + RGF + entes pagination & filters.

Network calls mocked with respx. SICONFI returns ``items`` arrays with
``hasMore`` flag; we test that we paginate correctly and that empty
responses don't blow up.
"""

from __future__ import annotations

import re

import httpx
import pytest
import respx

from findata.http_client import clear_cache
from findata.sources.tesouro.siconfi import (
    SICONFI_BASE,
    get_entes,
    get_rgf,
    get_rreo,
)


@pytest.fixture(autouse=True)
def _clean_caches() -> None:
    clear_cache()


def _rreo_row(
    *,
    year: int = 2024,
    bimestre: int = 6,
    instituicao: str = "Governo Federal",
    cod_ibge: int = 1,
    uf: str = "BR",
    anexo: str = "RREO-Anexo 01",
    coluna: str = "PREVISÃO INICIAL",
    cod_conta: str = "ReceitasExcetoIntraOrcamentarias",
    conta: str = "RECEITAS (EXCETO INTRA-ORÇAMENTÁRIAS) (I)",
    valor: float = 3_644_201_071_542.0,
) -> dict[str, object]:
    return {
        "exercicio": year,
        "demonstrativo": "RREO",
        "periodo": bimestre,
        "periodicidade": "B",
        "instituicao": instituicao,
        "cod_ibge": cod_ibge,
        "uf": uf,
        "populacao": 8_569_324,
        "anexo": anexo,
        "esfera": "U",
        "rotulo": "Padrão",
        "coluna": coluna,
        "cod_conta": cod_conta,
        "conta": conta,
        "valor": valor,
    }


@respx.mock
async def test_rreo_parses_payload() -> None:
    payload = {
        "items": [_rreo_row(), _rreo_row(coluna="No Bimestre (b)", valor=692_556_754_562.62)],
        "hasMore": False,
        "limit": 5000,
        "offset": 0,
        "count": 2,
    }
    respx.get(re.compile(rf"^{re.escape(SICONFI_BASE)}/rreo")).mock(
        return_value=httpx.Response(200, json=payload)
    )

    rows = await get_rreo(2024, 6, cod_ibge=1)
    assert len(rows) == 2
    r = rows[0]
    assert r.exercicio == 2024
    assert r.periodo == 6
    assert r.instituicao == "Governo Federal"
    assert r.anexo == "RREO-Anexo 01"
    assert r.coluna == "PREVISÃO INICIAL"
    assert r.cod_conta == "ReceitasExcetoIntraOrcamentarias"
    assert r.valor == 3_644_201_071_542.0


@respx.mock
async def test_rreo_paginates_until_hasmore_false() -> None:
    """Regression — hasMore=true must trigger a follow-up offset call."""
    page1 = {
        "items": [_rreo_row(coluna=f"col{i}", valor=float(i)) for i in range(3)],
        "hasMore": True,
        "limit": 5000,
        "offset": 0,
        "count": 3,
    }
    page2 = {
        "items": [_rreo_row(coluna="col3", valor=3.0)],
        "hasMore": False,
        "limit": 5000,
        "offset": 5000,
        "count": 1,
    }
    call_count = {"n": 0}

    def _route(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        offset = request.url.params.get("offset", "0")
        return httpx.Response(200, json=page1 if offset == "0" else page2)

    respx.get(re.compile(rf"^{re.escape(SICONFI_BASE)}/rreo")).mock(side_effect=_route)
    rows = await get_rreo(2024, 6, cod_ibge=1)
    assert call_count["n"] == 2
    assert len(rows) == 4
    assert rows[-1].coluna == "col3"


@respx.mock
async def test_rreo_anexo_filter_passes_through() -> None:
    payload = {"items": [_rreo_row(anexo="RREO-Anexo 06")], "hasMore": False}
    captured: list[str] = []

    def _route(request: httpx.Request) -> httpx.Response:
        captured.append(str(request.url))
        return httpx.Response(200, json=payload)

    respx.get(re.compile(rf"^{re.escape(SICONFI_BASE)}/rreo")).mock(side_effect=_route)
    await get_rreo(2024, 6, cod_ibge=1, anexo="RREO-Anexo 06")
    assert "co_anexo=RREO-Anexo+06" in captured[0] or "co_anexo=RREO-Anexo%2006" in captured[0]


@respx.mock
async def test_rgf_passes_poder_param() -> None:
    payload = {"items": [_rreo_row(anexo="RGF-Anexo 01")], "hasMore": False}
    captured: list[str] = []

    def _route(request: httpx.Request) -> httpx.Response:
        captured.append(str(request.url))
        return httpx.Response(200, json=payload)

    respx.get(re.compile(rf"^{re.escape(SICONFI_BASE)}/rgf")).mock(side_effect=_route)
    rows = await get_rgf(2024, 3, cod_ibge=1, poder="L")
    assert "co_poder=L" in captured[0]
    assert len(rows) == 1


@respx.mock
async def test_rreo_empty_response_returns_empty_list() -> None:
    respx.get(re.compile(rf"^{re.escape(SICONFI_BASE)}/rreo")).mock(
        return_value=httpx.Response(200, json={"items": [], "hasMore": False})
    )
    rows = await get_rreo(2024, 6, cod_ibge=999)
    assert rows == []


@respx.mock
async def test_get_entes_filters_invalid_codes() -> None:
    """Rows without cod_ibge (defensive — shouldn't happen but) are skipped."""
    payload = {
        "items": [
            {"cod_ibge": 1, "uf": "BR", "instituicao": "Governo Federal", "esfera": "U"},
            {"cod_ibge": 35, "uf": "SP", "instituicao": "São Paulo", "esfera": "E"},
            {"uf": "??", "instituicao": "missing code", "esfera": "M"},  # skipped
            {
                "cod_ibge": 3550308,
                "uf": "SP",
                "instituicao": "São Paulo",
                "esfera": "M",
                "populacao": 12_396_000,
            },
        ],
        "hasMore": False,
    }
    respx.get(re.compile(rf"^{re.escape(SICONFI_BASE)}/entes")).mock(
        return_value=httpx.Response(200, json=payload)
    )
    entes = await get_entes()
    assert len(entes) == 3
    assert entes[0].cod_ibge == 1
    assert entes[-1].populacao == 12_396_000
