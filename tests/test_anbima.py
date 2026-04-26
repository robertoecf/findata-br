"""ANBIMA source — credentials guard + parsing + API smoke (respx-mocked)."""

from __future__ import annotations

import os

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from findata.api.app import app
from findata.auth.base import MissingCredentialsError
from findata.http_client import clear_cache
from findata.sources.anbima.client import close_default_clients
from findata.sources.anbima.credentials import load_anbima_credentials
from findata.sources.anbima.indices import (
    _parse_ettj,
    _parse_ihfa,
    _parse_ima,
    _value_array,
)


@pytest.fixture(autouse=True)
def _clean_anbima_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Wipe credentials and cached clients between tests."""
    monkeypatch.delenv("ANBIMA_CLIENT_ID", raising=False)
    monkeypatch.delenv("ANBIMA_CLIENT_SECRET", raising=False)
    clear_cache()


def test_load_credentials_raises_when_missing() -> None:
    with pytest.raises(MissingCredentialsError) as exc:
        load_anbima_credentials()
    assert exc.value.source == "ANBIMA"
    assert "ANBIMA_CLIENT_ID" in exc.value.env_vars


def test_load_credentials_strips_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANBIMA_CLIENT_ID", "  abc  ")
    monkeypatch.setenv("ANBIMA_CLIENT_SECRET", "  xyz  ")
    creds = load_anbima_credentials()
    assert creds.client_id == "abc"
    assert creds.client_secret == "xyz"


def test_value_array_unwraps_common_envelopes() -> None:
    assert _value_array([{"a": 1}]) == [{"a": 1}]
    assert _value_array({"data": [{"a": 1}]}) == [{"a": 1}]
    assert _value_array({"results": [{"b": 2}]}) == [{"b": 2}]
    assert _value_array({"unrecognized": "shape"}) == []


def test_parse_ima_handles_camel_and_snake_keys() -> None:
    p = _parse_ima(
        {
            "indice": "IMA-B",
            "dataReferencia": "2026-04-22",
            "valorIndice": "12345.67",
            "variacaoPercentual": 0.42,
            "duration": 8.7,
        }
    )
    assert p.indice == "IMA-B"
    assert p.valor_indice == 12345.67
    assert p.variacao_pct == 0.42
    assert p.duration == 8.7


def test_parse_ima_tolerates_missing_fields() -> None:
    p = _parse_ima({"indice": "IMA-B", "data": "2026-04-22"})
    assert p.indice == "IMA-B"
    assert p.data_referencia == "2026-04-22"
    assert p.valor_indice is None


def test_parse_ihfa_handles_alternate_keys() -> None:
    p = _parse_ihfa(
        {
            "data": "2026-04-22",
            "valor": 100.5,
            "variacao_dia_pct": 0.1,
            "variacao_mes_pct": 1.2,
            "variacao_ano_pct": 12.3,
        }
    )
    assert p.valor_indice == 100.5
    assert p.variacao_ano_pct == 12.3


def test_parse_ettj_coerces_vertice_to_int() -> None:
    p = _parse_ettj({"vertice": "252", "taxaPre": "0.115"})
    assert p.vertice == 252
    assert p.taxa_pre == 0.115


# ── API smoke tests ──────────────────────────────────────────────


def test_anbima_status_reports_unconfigured() -> None:
    client = TestClient(app)
    r = client.get("/anbima/status")
    assert r.status_code == 200
    assert r.json()["configured"] is False
    assert "ANBIMA_CLIENT_ID" in r.json()["env_vars_required"]


def test_anbima_routes_503_when_unconfigured() -> None:
    client = TestClient(app)
    r = client.get("/anbima/ima")
    assert r.status_code == 503
    body = r.json()["detail"]
    assert body["error"] == "credentials_missing"
    assert "ANBIMA_CLIENT_ID" in body["env_vars_required"]


def test_anbima_status_reports_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANBIMA_CLIENT_ID", "test_id")
    monkeypatch.setenv("ANBIMA_CLIENT_SECRET", "test_secret")
    client = TestClient(app)
    r = client.get("/anbima/status")
    assert r.status_code == 200
    assert r.json()["configured"] is True


@respx.mock
async def test_anbima_ima_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANBIMA_CLIENT_ID", "cid")
    monkeypatch.setenv("ANBIMA_CLIENT_SECRET", "sec")
    # Reset the cached client so the new env vars take effect.
    await close_default_clients()

    respx.post("https://api.anbima.com.br/oauth/access-token").mock(
        return_value=httpx.Response(201, json={"access_token": "TKN", "expires_in": 3600})
    )
    respx.get("https://api.anbima.com.br/feed/precos-indices/v1/indices/ima").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "indice": "IMA-B",
                    "dataReferencia": "2026-04-22",
                    "valorIndice": 9876.54,
                    "variacaoPercentual": 0.21,
                    "duration": 7.5,
                }
            ],
        )
    )
    from findata.sources.anbima import IMAFamily, get_ima

    out = await get_ima(IMAFamily.IMA_B)
    assert len(out) == 1
    assert out[0].indice == "IMA-B"
    assert out[0].valor_indice == 9876.54

    # Verify the request actually carried the Sensedia headers
    last_req = respx.calls.last.request
    assert last_req.headers["access_token"] == "TKN"
    assert last_req.headers["client_id"] == "cid"

    await close_default_clients()


def test_root_endpoint_lists_anbima_in_auth_sources() -> None:
    client = TestClient(app)
    body = client.get("/").json()
    assert "sources_with_auth" in body
    assert "anbima" in body["sources_with_auth"]


@pytest.fixture(scope="session", autouse=True)
def _final_anbima_cleanup() -> None:
    """Drop any stale event-loop-bound clients on session exit."""
    yield
    if os.environ.get("PYTEST_RUNNING_FINAL_CLEANUP") != "1":
        os.environ["PYTEST_RUNNING_FINAL_CLEANUP"] = "1"
