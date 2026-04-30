from __future__ import annotations

import importlib.util
import io
import sys
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from typing import Any

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_public_surface.py"
_SPEC = importlib.util.spec_from_file_location("benchmark_public_surface", _SCRIPT_PATH)
assert _SPEC is not None
assert _SPEC.loader is not None
benchmark = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = benchmark
_SPEC.loader.exec_module(benchmark)


def test_slug_from_url_normalizes_hostname() -> None:
    assert benchmark.slug_from_url("https://www.dadosdemercado.com.br/") == "dadosdemercado_com_br"


def test_fetch_text_records_http_error_status_and_body(monkeypatch: Any) -> None:
    def raise_forbidden(_request: object, timeout: int) -> object:
        raise urllib.error.HTTPError(
            url="https://example.com/robots.txt",
            code=403,
            msg="Forbidden",
            hdrs={"content-type": "text/plain"},
            fp=io.BytesIO(b"blocked"),
        )

    monkeypatch.setattr(benchmark.urllib.request, "urlopen", raise_forbidden)

    result = benchmark.fetch_text("https://example.com/robots.txt")

    assert result.status == 403
    assert result.content_type == "text/plain"
    assert result.body == "blocked"
    assert "HTTPError" in str(result.error)


def test_collect_authorized_targets_uses_configured_prefixes_only() -> None:
    targets = benchmark.collect_authorized_targets(
        [
            "https://www.dadosdemercado.com.br/api/foo",
            "https://www.dadosdemercado.com.br/_next/data/build/page.json",
            "https://www.dadosdemercado.com.br/acoes",
            "https://example.com/api/foo",
        ],
        "https://www.dadosdemercado.com.br",
        ["/api/", "/_next/data/"],
    )

    assert targets == [
        "https://www.dadosdemercado.com.br/_next/data/build/page.json",
        "https://www.dadosdemercado.com.br/api/foo",
    ]


def test_build_payload_skips_passive_fetches_when_robots_is_unavailable(monkeypatch: Any) -> None:
    def fake_fetch_text(url: str, timeout: int = 20) -> object:
        if url.endswith("/robots.txt"):
            return benchmark.FetchResult(
                url=url,
                status=403,
                content_type="text/plain",
                body="blocked",
                error="HTTPError 403",
            )
        return benchmark.FetchResult(
            url=url,
            status=200,
            content_type="application/xml",
            body="<urlset><url><loc>https://example.com/acoes</loc></url></urlset>",
        )

    def fail_if_called(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("passive page/static fetch should be skipped")

    monkeypatch.setattr(benchmark, "fetch_text", fake_fetch_text)
    monkeypatch.setattr(benchmark, "inspect_pages", fail_if_called)
    monkeypatch.setattr(benchmark, "collect_static_assets", fail_if_called)
    monkeypatch.setattr(benchmark, "browser_network_urls", fail_if_called)

    payload = benchmark.build_payload(
        SimpleNamespace(
            base_url="https://example.com/",
            sleep=0.0,
            probe_path_prefix=["/api/"],
            browser_network=True,
            browser_path=["/"],
            chrome=None,
            browser_timeout=1,
            authorized_probe=False,
            probe_max_bytes=benchmark.DEFAULT_API_MAX_BYTES,
            output="docs/snapshots/example_public_surface.json",
            markdown="docs/EXAMPLE_ENDPOINT_BENCHMARK.md",
        )
    )

    assert payload["robots"]["available"] is False
    assert payload["inspected_pages"] == []
    assert payload["static_assets_fetched"] == []
    assert payload["browser_network"]["enabled"] is False
    assert payload["referenced_urls"]["same_origin_blocked_by_robots"] == []
