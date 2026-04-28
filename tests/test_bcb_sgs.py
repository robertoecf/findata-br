"""BCB SGS source — catalog + lookup tests (no network; respx-mocked)."""

from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

from findata.http_client import clear_cache
from findata.sources.bcb import sgs


def test_catalog_has_at_least_seventy_entries() -> None:
    """Smoke test: catalog should cover the most-needed BCB SGS series."""
    assert len(sgs.SERIES_CATALOG) >= 70


def test_catalog_schema_is_strict() -> None:
    """Every entry must expose exactly {code, name, unit, freq} — nothing else."""
    expected_keys = {"code", "name", "unit", "freq"}
    for short_name, entry in sgs.SERIES_CATALOG.items():
        assert set(entry.keys()) == expected_keys, f"{short_name} has wrong keys"
        assert isinstance(entry["code"], int)
        assert isinstance(entry["name"], str) and entry["name"]
        assert isinstance(entry["unit"], str) and entry["unit"]
        assert isinstance(entry["freq"], str) and entry["freq"]


def test_catalog_keys_are_snake_case_ascii() -> None:
    """Keys must be lowercase snake_case ASCII (no accents, no spaces)."""
    for key in sgs.SERIES_CATALOG:
        assert key == key.lower()
        assert key.replace("_", "").isascii()
        assert key.replace("_", "").isalnum()
        assert " " not in key


def test_catalog_codes_are_unique() -> None:
    """Two short names must never point at the same SGS code."""
    codes = [entry["code"] for entry in sgs.SERIES_CATALOG.values()]
    assert len(codes) == len(set(codes))


def test_known_priority_series_present() -> None:
    """Spot-check a handful of newly-added high-priority short names."""
    expected = {
        "ipca_livres": 11428,
        "ipca_monitorados": 4449,
        "m1": 1828,
        "m4": 1833,
        "credito_total": 20539,
        "spread_medio": 20783,
        "balanca_comercial": 22707,
        "reservas_internacionais": 3546,
        "dbgg_pib": 13762,
        "tjlp": 256,
    }
    for name, code in expected.items():
        assert name in sgs.SERIES_CATALOG, f"missing {name}"
        assert sgs.SERIES_CATALOG[name]["code"] == code


def _mock_sgs_last(code: int, value: float = 1.23, data: str = "01/03/2026") -> None:
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados/ultimos/10"
    respx.get(url).mock(
        return_value=httpx.Response(200, json=[{"data": data, "valor": str(value)}])
    )


@respx.mock
def test_get_series_by_name_resolves_ipca_livres() -> None:
    clear_cache()
    _mock_sgs_last(11428, value=0.75)
    points = asyncio.run(sgs.get_series_by_name("ipca_livres"))
    assert len(points) == 1
    assert points[0].valor == pytest.approx(0.75)


@respx.mock
def test_get_series_by_name_resolves_m1() -> None:
    clear_cache()
    _mock_sgs_last(1828, value=672222.02)
    points = asyncio.run(sgs.get_series_by_name("m1"))
    assert len(points) == 1
    assert points[0].valor == pytest.approx(672222.02)


@respx.mock
def test_get_series_by_name_resolves_balanca_comercial() -> None:
    clear_cache()
    _mock_sgs_last(22707, value=5619.9)
    points = asyncio.run(sgs.get_series_by_name("balanca_comercial"))
    assert len(points) == 1
    assert points[0].valor == pytest.approx(5619.9)


@respx.mock
def test_get_series_by_name_resolves_dbgg_pib() -> None:
    clear_cache()
    _mock_sgs_last(13762, value=79.20)
    points = asyncio.run(sgs.get_series_by_name("dbgg_pib"))
    assert len(points) == 1
    assert points[0].valor == pytest.approx(79.20)


def test_get_series_by_name_unknown_raises() -> None:
    """Unknown short name surfaces a helpful ValueError listing valid names."""
    with pytest.raises(ValueError, match="Unknown series 'not_a_real_series'"):
        asyncio.run(sgs.get_series_by_name("not_a_real_series"))
