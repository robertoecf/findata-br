"""SUSEP empresas tests — supervised-entities lookup table."""

from __future__ import annotations

import httpx
import pytest
import respx

from findata.http_client import clear_cache
from findata.sources.susep.empresas import (
    LISTAEMPRESAS_URL,
    get_susep_empresas,
    search_susep_empresa,
)


@pytest.fixture(autouse=True)
def _clean_caches() -> None:
    clear_cache()


_LISTAEMPRESAS_CSV = (
    "CodigoFIP;NomeEntidade;CNPJ\n"
    "01007;SABEMI SEGURADORA S.A.;87163234000138\n"
    "00603;PORTO SEGURO COMPANHIA DE SEGUROS GERAIS;61198164000160\n"
    "08745;BRASILPREV SEGUROS E PREVIDENCIA S.A.;27665207000131\n"
    ";INVALID - empty FIP;00000000000000\n"
    "99999;;11111111111111\n"  # missing name → skipped
)


@respx.mock
async def test_get_empresas_parses_and_skips_invalid_rows() -> None:
    respx.get(LISTAEMPRESAS_URL).mock(
        return_value=httpx.Response(200, content=_LISTAEMPRESAS_CSV.encode("iso-8859-1"))
    )
    empresas = await get_susep_empresas()
    assert len(empresas) == 3  # the 2 invalid rows skipped
    sabemi = empresas[0]
    assert sabemi.codigo_fip == "01007"
    assert sabemi.nome == "SABEMI SEGURADORA S.A."
    assert sabemi.cnpj == "87163234000138"


@respx.mock
async def test_search_empresa_case_insensitive_substring() -> None:
    respx.get(LISTAEMPRESAS_URL).mock(
        return_value=httpx.Response(200, content=_LISTAEMPRESAS_CSV.encode("iso-8859-1"))
    )
    hits = await search_susep_empresa("porto")
    assert len(hits) == 1
    assert hits[0].nome == "PORTO SEGURO COMPANHIA DE SEGUROS GERAIS"

    hits = await search_susep_empresa("SEGUROS")
    assert {e.codigo_fip for e in hits} == {"00603", "08745"}


async def test_search_empresa_short_query_returns_empty() -> None:
    """Defensive — refuse to scan the whole list for a single-char query."""
    hits = await search_susep_empresa("a")
    assert hits == []
