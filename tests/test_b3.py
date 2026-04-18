"""Tests for B3 stock quotes via yfinance."""

from findata.sources.b3 import quotes


class TestB3:
    async def test_get_quote_petr4(self):
        q = await quotes.get_quote("PETR4")
        assert q.ticker == "PETR4"
        assert q.preco is not None
        assert q.preco > 0

    async def test_get_history(self):
        data = await quotes.get_history("VALE3", period="5d")
        assert len(data) > 0
        assert all(p.close > 0 for p in data)

    async def test_ensure_sa_suffix(self):
        assert quotes._ensure_sa("PETR4") == "PETR4.SA"
        assert quotes._ensure_sa("petr4.sa") == "PETR4.SA"
        assert quotes._ensure_sa("VALE3.SA") == "VALE3.SA"

    async def test_multiple_quotes(self):
        data = await quotes.get_multiple_quotes(["PETR4", "VALE3"])
        assert len(data) == 2
        tickers = {q.ticker for q in data}
        assert "PETR4" in tickers
        assert "VALE3" in tickers
