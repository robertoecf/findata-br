"""Shared test fixtures.

Integration tests (marked with `@pytest.mark.integration`) hit the real
public APIs. They are skipped by default — enable with:

    pytest -m integration
    pytest -m ""          # run all
"""

from __future__ import annotations

import pytest

from findata import http_client


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Ensure a clean HTTP cache between tests."""
    http_client.clear_cache()


@pytest.fixture
async def _shutdown_http_client() -> None:
    """Close the shared httpx client after the test."""
    yield
    await http_client.close_client()
