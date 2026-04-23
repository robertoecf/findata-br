"""Sync-only B3 helper tests (no network)."""

from __future__ import annotations


def test_ensure_sa_adds_suffix() -> None:
    import pytest

    pytest.importorskip("yfinance")
    from findata.sources.b3.quotes import _ensure_sa

    assert _ensure_sa("PETR4") == "PETR4.SA"
    assert _ensure_sa("petr4") == "PETR4.SA"
    assert _ensure_sa("  VALE3  ") == "VALE3.SA"
    assert _ensure_sa("PETR4.SA") == "PETR4.SA"
    assert _ensure_sa("petr4.sa") == "PETR4.SA"
