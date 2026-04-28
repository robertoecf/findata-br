"""Receita Federal arrecadação tests — federal-tax revenue parser."""

from __future__ import annotations

import httpx
import pytest
import respx

from findata.http_client import clear_cache
from findata.sources.receita.arrecadacao import (
    ARRECADACAO_URL,
    get_arrecadacao,
    list_tributos,
)


@pytest.fixture(autouse=True)
def _clean_caches() -> None:
    clear_cache()


# Receita CSV: ; delimiter, ISO-8859-1, integer values in R$, pt-BR month
# names, trailing empty column after the last value (model captures that).
_RECEITA_CSV = (
    "Ano;Mês;UF;IMPOSTO SOBRE IMPORTAÇÃO;IPI - AUTOMÓVEIS;IRPF;IRPJ - DEMAIS EMPRESAS;"
    "COFINS;CSLL;\n"
    "2024;Janeiro;SP;1500000;320000;9800000;15400000;42000000;8200000;\n"
    "2024;Janeiro;RJ;850000;180000;3200000;6800000;18000000;3500000;\n"
    "2024;Fevereiro;SP;1620000;305000;9100000;14200000;39000000;7900000;\n"
    "2024;Fevereiro;RJ;920000;195000;3000000;6500000;17400000;3300000;\n"
)


@respx.mock
async def test_arrecadacao_no_filter_returns_all_long_form() -> None:
    respx.get(ARRECADACAO_URL).mock(
        return_value=httpx.Response(200, content=_RECEITA_CSV.encode("iso-8859-1"))
    )
    rows = await get_arrecadacao()
    # 4 source rows × 6 tributos each = 24 long-form records.
    assert len(rows) == 24
    # Check pt-BR month → number conversion
    jan = [r for r in rows if r.mes == 1]
    assert len(jan) == 12
    feb = [r for r in rows if r.mes == 2]
    assert len(feb) == 12


@respx.mock
async def test_arrecadacao_filter_by_uf_and_tributo() -> None:
    respx.get(ARRECADACAO_URL).mock(
        return_value=httpx.Response(200, content=_RECEITA_CSV.encode("iso-8859-1"))
    )
    rows = await get_arrecadacao(uf="sp", tributo="COFINS")  # case-insensitive UF
    assert len(rows) == 2  # Jan + Fev
    assert all(r.uf == "SP" for r in rows)
    assert all(r.tributo == "COFINS" for r in rows)
    assert rows[0].valor == 42_000_000.0
    assert rows[1].valor == 39_000_000.0


@respx.mock
async def test_arrecadacao_filter_by_year_month() -> None:
    respx.get(ARRECADACAO_URL).mock(
        return_value=httpx.Response(200, content=_RECEITA_CSV.encode("iso-8859-1"))
    )
    rows = await get_arrecadacao(year=2024, month=1, tributo="IRPF")
    assert len(rows) == 2  # SP + RJ
    sp = next(r for r in rows if r.uf == "SP")
    assert sp.valor == 9_800_000.0
    assert sp.dt_referencia == "2024-01-01"


@respx.mock
async def test_arrecadacao_parses_brazilian_thousand_decimals() -> None:
    """Regression — Codex caught _f() returning None for 226.708.856,85
    (Brazilian decimal with thousand-dot separators), losing real revenue
    values. The fix strips thousand dots before swapping the decimal comma.
    """
    csv = (
        "Ano;Mês;UF;RECEITA PREVIDENCIÁRIA;ADMINISTRADAS POR OUTROS ÓRGÃOS;\n"
        "2024;Maio;TO;226.708.856,85;4.694.590,56;\n"
        "2024;Maio;SP;1500000;320000;\n"  # plain integer (no dots, no commas)
        "2024;Junho;TO;1.234.567;0,5;\n"  # lone dots = thousand sep; lone comma = decimal
    )
    respx.get(ARRECADACAO_URL).mock(
        return_value=httpx.Response(200, content=csv.encode("iso-8859-1"))
    )
    rows = await get_arrecadacao(uf="TO")
    by_period = {(r.ano, r.mes, r.tributo): r.valor for r in rows}
    assert by_period[(2024, 5, "RECEITA PREVIDENCIÁRIA")] == 226_708_856.85
    assert by_period[(2024, 5, "ADMINISTRADAS POR OUTROS ÓRGÃOS")] == 4_694_590.56
    assert by_period[(2024, 6, "RECEITA PREVIDENCIÁRIA")] == 1_234_567.0
    assert by_period[(2024, 6, "ADMINISTRADAS POR OUTROS ÓRGÃOS")] == 0.5
    # Plain integer style still works.
    sp = await get_arrecadacao(uf="SP")
    assert next(r.valor for r in sp if r.tributo == "RECEITA PREVIDENCIÁRIA") == 1_500_000.0


@respx.mock
async def test_arrecadacao_handles_empty_cells() -> None:
    csv = (
        "Ano;Mês;UF;IRPF;COFINS;\n"
        "2024;Janeiro;SP;;42000000;\n"  # IRPF empty
    )
    respx.get(ARRECADACAO_URL).mock(
        return_value=httpx.Response(200, content=csv.encode("iso-8859-1"))
    )
    rows = await get_arrecadacao(uf="SP")
    irpf = next(r for r in rows if r.tributo == "IRPF")
    assert irpf.valor is None
    cofins = next(r for r in rows if r.tributo == "COFINS")
    assert cofins.valor == 42_000_000.0


@respx.mock
async def test_arrecadacao_skips_rows_with_unknown_month() -> None:
    """Defense against header-style or malformed rows in the CSV."""
    csv = "Ano;Mês;UF;IRPF;\n2024;NotAMonth;SP;100;\n2024;Janeiro;SP;500;\n"
    respx.get(ARRECADACAO_URL).mock(
        return_value=httpx.Response(200, content=csv.encode("iso-8859-1"))
    )
    rows = await get_arrecadacao()
    assert len(rows) == 1
    assert rows[0].mes == 1


@respx.mock
async def test_list_tributos_strips_non_tax_columns_and_trailing_empty() -> None:
    respx.get(ARRECADACAO_URL).mock(
        return_value=httpx.Response(200, content=_RECEITA_CSV.encode("iso-8859-1"))
    )
    tributos = await list_tributos()
    assert "Ano" not in tributos
    assert "Mês" not in tributos
    assert "UF" not in tributos
    assert "" not in tributos  # trailing semicolon at line end
    assert "IMPOSTO SOBRE IMPORTAÇÃO" in tributos
    assert "COFINS" in tributos
    assert "IPI - AUTOMÓVEIS" in tributos
