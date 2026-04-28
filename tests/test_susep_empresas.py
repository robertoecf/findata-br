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


@respx.mock
async def test_susep_decodes_cp1252_endash_in_entity_names() -> None:
    """Regression — Codex found SUSEP's CSV uses CP1252 (byte 0x96 = en-dash)
    in names like "ABGF – AGÊNCIA BRASILEIRA …". With iso-8859-1 it became
    a control char and broke string searches downstream.
    """
    # Build as bytes — Python's Unicode→CP1252 encoder won't accept \x96.
    head = "\r\nCodigoFIP;NomeEntidade;CNPJ\r\n31976;".encode("cp1252")
    body = b"AG\xcaNCIA BRASILEIRA GESTORA DE FUNDOS S.A. \x96 ABGF;17909518000145\n"
    respx.get(LISTAEMPRESAS_URL).mock(return_value=httpx.Response(200, content=head + body))
    empresas = await get_susep_empresas()
    assert len(empresas) == 1
    assert "\x96" not in empresas[0].nome
    assert "–" in empresas[0].nome  # proper en-dash, decoded from CP1252


@respx.mock
async def test_search_empresa_strips_query_whitespace() -> None:
    """Regression — Codex found ' youse ' with surrounding spaces missed
    'YOUSE SEGURADORA S.A.' because the query wasn't stripped.
    """
    respx.get(LISTAEMPRESAS_URL).mock(
        return_value=httpx.Response(200, content=_LISTAEMPRESAS_CSV.encode("iso-8859-1"))
    )
    clean = await search_susep_empresa("YOUSE")
    spaced = await search_susep_empresa(" youse ")
    # Both queries hit the legacy CSV — no YOUSE row in the fixture, so 0 each.
    assert len(clean) == len(spaced)
    # Query that does have a hit, with whitespace
    porto_clean = await search_susep_empresa("porto")
    porto_spaced = await search_susep_empresa("  PORTO\t")
    assert len(porto_clean) == len(porto_spaced) == 1
