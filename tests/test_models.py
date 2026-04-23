"""Unit tests for Pydantic model parsing / validation."""

from __future__ import annotations

import pytest

from findata.sources.bcb import focus, sgs
from findata.sources.tesouro.bonds import _date_br, _float


def test_sgs_parse_valid_rows() -> None:
    raw = [{"data": "02/01/2026", "valor": "10.5"}, {"data": "03/01/2026", "valor": "10.51"}]
    out = sgs._parse(raw)
    assert len(out) == 2
    assert out[0].data == "02/01/2026"
    assert out[0].valor == 10.5


def test_sgs_parse_skips_invalid_rows() -> None:
    raw = [{"data": "02/01/2026", "valor": "ABC"}, {"data": "03/01/2026", "valor": "9.9"}]
    out = sgs._parse(raw)
    assert len(out) == 1
    assert out[0].valor == 9.9


def test_sgs_get_series_by_name_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown series"):
        import asyncio

        asyncio.run(sgs.get_series_by_name("nonexistent-series"))


def test_focus_validate_indicator_is_case_insensitive() -> None:
    assert focus._validate_indicator("ipca") == "IPCA"
    assert focus._validate_indicator("SELIC") == "Selic"


def test_focus_validate_indicator_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown indicator"):
        focus._validate_indicator("HACKED' or 1 eq 1 --")


def test_focus_parse_odata_coerces_int_data_referencia() -> None:
    raw = {
        "value": [
            {
                "Indicador": "IPCA",
                "Data": "2026-04-22",
                "DataReferencia": 2026,  # BCB occasionally returns int
                "Media": 3.8,
                "Mediana": 3.75,
            },
        ],
    }
    out = focus._parse_odata(raw, focus.FocusExpectation, focus._EXPECTATION_MAP)
    assert out[0].data_referencia == "2026"
    assert out[0].media == 3.8


def test_tesouro_date_br_converts_format() -> None:
    assert _date_br("15/03/2026") == "2026-03-15"
    assert _date_br("  15/03/2026 ") == "2026-03-15"


def test_tesouro_date_br_passthrough_on_malformed() -> None:
    assert _date_br("2026-03-15") == "2026-03-15"
    assert _date_br("") == ""


def test_tesouro_float_parses_brazilian_decimal() -> None:
    assert _float("3,14") == 3.14
    assert _float("1.000,50") is None  # thousands separator not supported (by design)
    assert _float("") is None
    assert _float("ABC") is None
