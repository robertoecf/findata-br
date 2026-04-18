"""Tests for BCB data sources — hits real APIs."""

import pytest

from findata.sources.bcb import sgs, ptax, focus
from datetime import date


class TestSGS:
    async def test_get_series_last_selic(self):
        data = await sgs.get_series_last(432, n=5)
        assert len(data) == 5
        assert all(d.valor > 0 for d in data)

    async def test_get_series_by_name(self):
        data = await sgs.get_series_by_name("ipca", n=3)
        assert len(data) == 3

    async def test_get_series_by_name_invalid(self):
        with pytest.raises(ValueError, match="Unknown series"):
            await sgs.get_series_by_name("nonexistent")

    async def test_get_series_with_date_range(self):
        data = await sgs.get_series(
            432,
            start=date(2026, 1, 2),
            end=date(2026, 1, 31),
        )
        assert len(data) > 0
        assert all(d.valor > 0 for d in data)

    async def test_catalog_has_expected_keys(self):
        expected = {"selic", "ipca", "cdi", "dolar_ptax", "igpm"}
        assert expected.issubset(set(sgs.SERIES_CATALOG.keys()))


class TestPTAX:
    async def test_get_currencies(self):
        currencies = await ptax.get_currencies()
        assert len(currencies) > 0
        symbols = [c.simbolo for c in currencies]
        assert "USD" in symbols
        assert "EUR" in symbols

    async def test_get_ptax_usd_weekday(self):
        data = await ptax.get_ptax_usd(date(2026, 3, 27))
        assert len(data) > 0
        assert data[0].cotacao_venda > 0

    async def test_get_ptax_usd_weekend_returns_empty(self):
        data = await ptax.get_ptax_usd(date(2026, 3, 28))
        assert len(data) == 0

    async def test_get_ptax_usd_period(self):
        data = await ptax.get_ptax_usd_period(
            start=date(2026, 3, 23),
            end=date(2026, 3, 27),
        )
        assert len(data) >= 3


class TestFocus:
    async def test_focus_annual_ipca(self):
        data = await focus.get_focus_annual("IPCA", top=5)
        assert len(data) == 5
        assert all(e.indicador == "IPCA" for e in data)

    async def test_focus_selic(self):
        data = await focus.get_focus_selic(top=5)
        assert len(data) == 5
        assert all(e.reuniao for e in data)

    async def test_focus_indicators_list(self):
        assert "IPCA" in focus.FOCUS_INDICATORS
        assert "Selic" in focus.FOCUS_INDICATORS

    async def test_focus_invalid_indicator(self):
        with pytest.raises(ValueError, match="Unknown indicator"):
            await focus.get_focus_annual("HACKED' or 1 eq 1 or '")
