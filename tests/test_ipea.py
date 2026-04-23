"""IPEA source — parsing + API wiring tests (no network; respx-mocked)."""

from __future__ import annotations

import httpx
import respx
from fastapi.testclient import TestClient

from findata.api.app import app
from findata.http_client import clear_cache
from findata.sources.ipea import series as ipea_series


def test_parse_values_handles_missing_and_invalid() -> None:
    raw = {
        "@odata.context": "...",
        "value": [
            {"SERCODIGO": "XYZ", "VALDATA": "2026-01-01T00:00:00-03:00", "VALVALOR": 10.5},
            {"SERCODIGO": "XYZ", "VALDATA": "2026-02-01T00:00:00-03:00", "VALVALOR": None},
            {"SERCODIGO": "XYZ", "VALDATA": "2026-03-01T00:00:00-03:00", "VALVALOR": "abc"},
        ],
    }
    points = ipea_series._parse_values(raw)
    assert len(points) == 3
    assert points[0].valor == 10.5
    assert points[1].valor is None
    assert points[2].valor is None  # malformed → None


def test_parse_metadata_strips_fields() -> None:
    item = {
        "SERCODIGO": "BM12_TJOVER12",
        "SERNOME": "Taxa Selic over acumulada no mês",
        "SERCOMENTARIO": "Calculated by BCB",
        "UNINOME": "% a.m.",
        "PERNOME": "Mensal",
        "TEMNOME": "Moeda e crédito",
        "FNTNOME": "BCB",
    }
    m = ipea_series._parse_metadata(item)
    assert m.sercodigo == "BM12_TJOVER12"
    assert m.serunidade == "% a.m."
    assert m.serperiodicidade == "Mensal"
    assert m.serfonte == "BCB"


@respx.mock
def test_ipea_catalog_endpoint() -> None:
    clear_cache()
    client = TestClient(app)
    r = client.get("/ipea/catalog")
    assert r.status_code == 200
    body = r.json()
    assert "selic_over_mensal" in body
    assert body["selic_over_mensal"]["code"] == "BM12_TJOVER12"


@respx.mock
def test_ipea_series_happy_path_slices_client_side() -> None:
    clear_cache()
    respx.get(
        "http://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='BM12_TJOVER12')",
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "@odata.context": "...",
                "value": [
                    {
                        "SERCODIGO": "BM12_TJOVER12",
                        "VALDATA": "2026-01-01T00:00:00-03:00",
                        "VALVALOR": 1.00,
                    },
                    {
                        "SERCODIGO": "BM12_TJOVER12",
                        "VALDATA": "2026-03-01T00:00:00-03:00",
                        "VALVALOR": 1.05,
                    },
                    {
                        "SERCODIGO": "BM12_TJOVER12",
                        "VALDATA": "2026-02-01T00:00:00-03:00",
                        "VALVALOR": 1.02,
                    },
                ],
            },
        )
    )
    client = TestClient(app)
    r = client.get("/ipea/series/BM12_TJOVER12", params={"top": 2})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    # Client-side sorts desc by date, so March then February.
    assert data[0]["data"].startswith("2026-03")
    assert data[1]["data"].startswith("2026-02")


@respx.mock
def test_ipea_metadata_404() -> None:
    clear_cache()
    respx.get("http://www.ipeadata.gov.br/api/odata4/Metadados('DOES_NOT_EXIST')").mock(
        return_value=httpx.Response(200, json={"@odata.context": "...", "value": []})
    )
    client = TestClient(app)
    r = client.get("/ipea/metadata/DOES_NOT_EXIST")
    assert r.status_code == 404
