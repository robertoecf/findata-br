"""ANBIMA IMA historical-series fetcher — respx-mocked unit tests."""

from __future__ import annotations

from datetime import date

import httpx
import pytest
import respx

from findata.http_client import clear_cache
from findata.sources.anbima.indices import (
    IMA_HISTORY_DOWNLOAD_URL,
    IMAFamily,
    _ima_history_cache_clear,
    _parse_ima_history_csv,
    get_ima_history,
)


@pytest.fixture(autouse=True)
def _reset_caches() -> None:
    clear_cache()
    _ima_history_cache_clear()


# ── Sample payloads (latin-1 in production; tests use already-decoded text) ──

# Real ANBIMA "ima-sh-down.asp?saida=csv" payload, trimmed to the families we
# care about. Keeps the leading "TOTAIS - QUADRO RESUMO" banner and the actual
# header row so the parser exercises its lookahead.
_CSV_HEADER = (
    "TOTAIS - QUADRO RESUMO\r\n"
    "Índice;Data de Referência;Número Índice;Variação Diária(%);"
    "Variação no Mês(%);Variação no Ano(%);Variação 12 Meses(%);"
    "Variação 24 Meses(%);Peso(%);Duration(d.u.);Carteira a Mercado (R$ mil);"
    "Número de<BR>Operações *;Quant. Negociada (1.000 títulos) *;"
    "Valor Negociado (R$ mil) *;PMR;Convexidade;Yield;Redemption Yield\r\n"
)


def _csv_for(d: str) -> str:
    """Build a CSV body for the given DD/MM/YYYY reference date."""
    return _CSV_HEADER + (
        f"IRF-M 1;{d};17.000,000000;0,0319;0,7079;4,0659;10,8844;24,2713;"
        "6,66;145;445.581.377;50;2.961,72;2.742.247,15;211;0,7428;14,5929;14,6417\r\n"
        f"IMA-B;{d};10.000,000000;-0,1645;0,7607;4,2360;2,3125;11,8838;"
        "25,73;1.511;1.721.708.951;2.465;9.432,42;39.523.925,88;2.868;74,6;7,9;7,5\r\n"
        f"IMA-S;{d};7.300,000000;0,0528;0,5828;3,6916;11,6965;25,7622;"
        "52,42;1;3.507.006.248;425;1.248,85;20.426.819,32;1;0,0;--;--\r\n"
    )


_NO_DATA_BODY = "Não há dados disponíveis para [01/01/2025] !"


# ── Parser unit test ─────────────────────────────────────────────


def test_parse_ima_history_csv_extracts_three_indices() -> None:
    rows = _parse_ima_history_csv(_csv_for("15/04/2025"), "2025-04-15")
    indices = sorted(r.indice for r in rows)
    assert indices == ["IMA-B", "IMA-S", "IRF-M 1"]
    by_index = {r.indice: r for r in rows}
    assert by_index["IRF-M 1"].numero_indice == pytest.approx(17000.0)
    assert by_index["IRF-M 1"].peso_pct == pytest.approx(6.66)
    assert by_index["IRF-M 1"].duration_du == pytest.approx(145)
    assert by_index["IRF-M 1"].variacao_dia_pct == pytest.approx(0.0319)
    assert by_index["IMA-B"].variacao_dia_pct == pytest.approx(-0.1645)
    # "--" → None for sparse fields
    assert by_index["IMA-S"].duration_du == pytest.approx(1)


def test_parse_ima_history_csv_handles_no_data_banner() -> None:
    assert _parse_ima_history_csv(_NO_DATA_BODY, "2025-01-01") == []


# ── End-to-end fetch via respx ────────────────────────────────────


def _stub_post(date_to_body: dict[str, str]) -> None:
    """Mock the ANBIMA POST endpoint: response depends on the form's Dt_Ref."""

    def _resolve(request: httpx.Request) -> httpx.Response:
        body = request.content.decode("latin1")
        # Form is x-www-form-urlencoded; pull out Dt_Ref by simple parse.
        dtref = ""
        for part in body.split("&"):
            if part.startswith("Dt_Ref="):
                dtref = part.split("=", 1)[1].replace("%2F", "/")
                break
        text = date_to_body.get(dtref)
        if text is None:
            return httpx.Response(404, text="not found")
        # ANBIMA serves latin-1 — encode so the client decode path is real.
        return httpx.Response(
            200,
            content=text.encode("latin1"),
            headers={"Content-Type": "text/csv; charset=ISO-8859-1"},
        )

    respx.post(IMA_HISTORY_DOWNLOAD_URL).mock(side_effect=_resolve)


@respx.mock
async def test_get_ima_history_full_range_returns_sorted_rows() -> None:
    _stub_post(
        {
            "14/04/2025": _csv_for("14/04/2025"),
            "15/04/2025": _csv_for("15/04/2025"),
            "16/04/2025": _csv_for("16/04/2025"),
        }
    )
    rows = await get_ima_history(None, date(2025, 4, 14), date(2025, 4, 16))
    # 3 days × 3 indices each
    assert len(rows) == 9
    # Sorted by data_referencia ascending
    dates = [r.data_referencia for r in rows]
    assert dates == sorted(dates)
    assert dates[0] == "2025-04-14"
    assert dates[-1] == "2025-04-16"


@respx.mock
async def test_get_ima_history_skips_weekends_without_requesting_them() -> None:
    # 12 Apr 2025 = Saturday, 13 Apr 2025 = Sunday — should never be POSTed.
    route = respx.post(IMA_HISTORY_DOWNLOAD_URL).mock(
        return_value=httpx.Response(
            200,
            content=_csv_for("11/04/2025").encode("latin1"),
            headers={"Content-Type": "text/csv"},
        )
    )
    rows = await get_ima_history(None, date(2025, 4, 12), date(2025, 4, 13))
    assert rows == []
    assert route.call_count == 0


@respx.mock
async def test_get_ima_history_filters_by_family() -> None:
    _stub_post(
        {
            "14/04/2025": _csv_for("14/04/2025"),
            "15/04/2025": _csv_for("15/04/2025"),
        }
    )
    rows = await get_ima_history(IMAFamily.IMA_B, date(2025, 4, 14), date(2025, 4, 15))
    assert len(rows) == 2
    assert {r.indice for r in rows} == {"IMA-B"}
    # String input should match too (case-insensitive)
    rows2 = await get_ima_history("ima-b", date(2025, 4, 14), date(2025, 4, 15))
    assert {r.indice for r in rows2} == {"IMA-B"}


@respx.mock
async def test_get_ima_history_resilient_to_404_and_no_data_banner() -> None:
    # Wed 16 Apr 2025: data. Thu 17 Apr 2025: holiday (no-data banner).
    # Fri 18 Apr 2025: 404 from the upstream.
    def _resolve(request: httpx.Request) -> httpx.Response:
        body = request.content.decode("latin1")
        if "17%2F04%2F2025" in body or "17/04/2025" in body:
            return httpx.Response(
                200,
                content=_NO_DATA_BODY.encode("latin1"),
                headers={"Content-Type": "text/csv"},
            )
        if "18%2F04%2F2025" in body or "18/04/2025" in body:
            return httpx.Response(404, text="not found")
        return httpx.Response(
            200,
            content=_csv_for("16/04/2025").encode("latin1"),
            headers={"Content-Type": "text/csv"},
        )

    respx.post(IMA_HISTORY_DOWNLOAD_URL).mock(side_effect=_resolve)

    rows = await get_ima_history(None, date(2025, 4, 16), date(2025, 4, 18))
    # Only Wed contributes — Thu/Fri are silently skipped.
    assert {r.data_referencia for r in rows} == {"2025-04-16"}
    assert len(rows) == 3  # 3 indices for that one day


@respx.mock
async def test_get_ima_history_partial_range_only_returns_within_dates() -> None:
    # Provide CSVs for a wide span, request a narrow one; ensure no leakage.
    _stub_post(
        {
            "14/04/2025": _csv_for("14/04/2025"),
            "15/04/2025": _csv_for("15/04/2025"),
            "16/04/2025": _csv_for("16/04/2025"),
        }
    )
    rows = await get_ima_history(IMAFamily.IRF_M_1, date(2025, 4, 15), date(2025, 4, 15))
    assert [r.data_referencia for r in rows] == ["2025-04-15"]
    assert all(r.indice == "IRF-M 1" for r in rows)


async def test_get_ima_history_swapped_dates_returns_empty() -> None:
    # No HTTP traffic at all — guard rail.
    rows = await get_ima_history(None, date(2025, 4, 16), date(2025, 4, 14))
    assert rows == []
