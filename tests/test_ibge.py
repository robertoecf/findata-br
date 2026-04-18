"""Tests for IBGE data source."""

import pytest

from findata.sources.ibge import indicators


class TestIBGE:
    async def test_get_ipca_mensal(self):
        data = await indicators.get_indicator("ipca_mensal", periods=3)
        assert len(data) > 0
        assert any(d.valor is not None for d in data)

    async def test_get_ipca_breakdown(self):
        data = await indicators.get_ipca_breakdown(periods=2)
        assert len(data) > 0
        # Should have data for multiple groups
        groups = {d.classificacao for d in data if d.classificacao}
        assert len(groups) >= 5  # At least 5 of the 10 major groups

    async def test_invalid_indicator(self):
        with pytest.raises(ValueError, match="Unknown indicator"):
            await indicators.get_indicator("fake_indicator")

    async def test_indicator_catalog(self):
        assert "ipca_mensal" in indicators.IBGE_INDICATORS
        assert "pib_trimestral" in indicators.IBGE_INDICATORS
