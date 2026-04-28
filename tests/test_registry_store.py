"""Tests for findata.registry.store — query normalization + FTS5 lookup."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from findata.registry import store

SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "findata"
    / "registry"
    / "schema.sql"
)


@pytest.fixture
def fixture_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a tiny isolated registry on disk + redirect the store to it."""
    db_path = tmp_path / "test_registry.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_PATH.read_text())
    conn.executemany(
        "INSERT INTO entities(searchable, payload) VALUES (?, ?)",
        [
            (
                "33000167000101 9512 PETR3 PETR4 PETROLEO BRASILEIRO SA PETROBRAS",
                json.dumps(
                    {
                        "cnpj": "33.000.167/0001-01",
                        "nome": "PETROBRAS",
                        "kind": "cvm_company",
                        "sources": ["cvm", "b3"],
                        "tickers": ["PETR3", "PETR4"],
                        "cod_cvm": "9512",
                        "extra": {},
                    }
                ),
            ),
            (
                "60746948000112 18520 ITUB3 ITUB4 ITAU UNIBANCO HOLDING SA",
                json.dumps(
                    {
                        "cnpj": "60.746.948/0001-12",
                        "nome": "ITAÚ UNIBANCO HOLDING",
                        "kind": "cvm_company",
                        "sources": ["cvm", "b3"],
                        "tickers": ["ITUB3", "ITUB4"],
                        "cod_cvm": "18520",
                        "extra": {},
                    }
                ),
            ),
            (
                "61198164000160 05886 PORTO SEGURO COMPANHIA DE SEGUROS GERAIS",
                json.dumps(
                    {
                        "cnpj": "61198164000160",
                        "nome": "PORTO SEGURO COMPANHIA DE SEGUROS GERAIS",
                        "kind": "susep",
                        "sources": ["susep"],
                        "tickers": [],
                        "codigo_fip": "05886",
                        "extra": {},
                    }
                ),
            ),
        ],
    )
    conn.executemany(
        "INSERT INTO meta(key, value) VALUES (?, ?)",
        [
            ("schema_version", "1"),
            ("built_at", "2026-04-28T00:00:00Z"),
            ("sources_json", '{"cvm_companies": 2, "susep": 1}'),
            ("content_sha256", "test_hash_abc"),
        ],
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(store, "REGISTRY_PATH", db_path)
    return db_path


# ── _normalize_query unit (no DB) ─────────────────────────────────


def test_normalize_query_single_word_uppercases() -> None:
    assert store._normalize_query("petrobras") == "PETROBRAS"


def test_normalize_query_strips_diacritics() -> None:
    assert store._normalize_query("itaú") == "ITAU"


def test_normalize_query_keeps_clean_cnpj_as_one_token() -> None:
    assert store._normalize_query("33000167000101") == "33000167000101"


def test_normalize_query_handles_masked_cnpj_with_or() -> None:
    """Masked CNPJ produces (spaced) OR (joined) — joined wins on real data."""
    result = store._normalize_query("33.000.167/0001-01")
    assert "33000167000101" in result
    assert " OR " in result


def test_normalize_query_multi_word_name_with_or() -> None:
    """Multi-word name produces both spaced and joined variants."""
    result = store._normalize_query("banco do brasil")
    assert "BANCO DO BRASIL" in result
    assert "BANCODOBRASIL" in result


def test_normalize_query_too_short_returns_empty() -> None:
    assert store._normalize_query("x") == ""
    assert store._normalize_query("") == ""
    assert store._normalize_query("   ") == ""


def test_normalize_query_punctuation_only_returns_empty() -> None:
    assert store._normalize_query("!!!") == ""
    assert store._normalize_query("...") == ""


# ── lookup integration ────────────────────────────────────────────


async def test_lookup_cnpj_exact_no_mask(fixture_registry: Path) -> None:
    r = await store.lookup("33000167000101")
    assert r.total == 1
    assert r.entities[0].nome == "PETROBRAS"
    assert r.entities[0].cnpj == "33.000.167/0001-01"
    assert "PETR4" in r.entities[0].tickers


async def test_lookup_cnpj_with_mask(fixture_registry: Path) -> None:
    """User pasted the formatted CNPJ — should resolve same as bare digits."""
    r = await store.lookup("33.000.167/0001-01")
    assert r.total == 1
    assert r.entities[0].nome == "PETROBRAS"


async def test_lookup_by_ticker(fixture_registry: Path) -> None:
    r = await store.lookup("PETR4")
    assert r.total == 1
    assert r.entities[0].nome == "PETROBRAS"


async def test_lookup_by_cod_cvm(fixture_registry: Path) -> None:
    r = await store.lookup("9512")
    assert r.total == 1
    assert r.entities[0].cod_cvm == "9512"


async def test_lookup_by_codigo_fip(fixture_registry: Path) -> None:
    r = await store.lookup("05886")
    assert r.total == 1
    assert r.entities[0].kind == "susep"
    assert r.entities[0].codigo_fip == "05886"


async def test_lookup_name_with_diacritic_input(fixture_registry: Path) -> None:
    """Query 'itaú' folds to ITAU; finds Itaú Unibanco."""
    r = await store.lookup("itaú")
    assert r.total == 1
    assert "ITAÚ" in r.entities[0].nome


async def test_lookup_multi_word_name(fixture_registry: Path) -> None:
    r = await store.lookup("porto seguro")
    assert r.total == 1
    assert "PORTO SEGURO" in r.entities[0].nome


async def test_lookup_no_match_returns_empty(fixture_registry: Path) -> None:
    r = await store.lookup("99999999999999")
    assert r.total == 0
    assert r.entities == []


async def test_lookup_short_query_returns_empty(fixture_registry: Path) -> None:
    r = await store.lookup("x")
    assert r.total == 0


async def test_lookup_rank_discriminates_exact_from_fuzzy(
    fixture_registry: Path,
) -> None:
    """Rank on a unique-token match should be more negative than a shared-token match.

    BM25 IDF weighs unique tokens (CNPJ) much more strongly than common tokens
    (the 'S A' suffix that appears across multiple companies). The absolute
    threshold varies with corpus size; we assert the *gap*, not the value.
    """
    r_exact = await store.lookup("33000167000101")  # unique CNPJ token
    r_fuzzy = await store.lookup("S A")  # 'SA' suffix shared across docs
    assert r_exact.entities[0].rank is not None
    assert r_fuzzy.entities[0].rank is not None
    # More negative = more relevant. Exact must beat fuzzy by a clear margin.
    assert r_exact.entities[0].rank < r_fuzzy.entities[0].rank


async def test_lookup_respects_limit(fixture_registry: Path) -> None:
    """Limit caps results even when more matches exist."""
    # "SA" appears in multiple searchables (Petrobras, Itaú, Porto Seguro)
    r = await store.lookup("SA", limit=1)
    assert r.total <= 1


async def test_lookup_query_field_echoes_user_input(fixture_registry: Path) -> None:
    """Response includes the original (unnormalized) query."""
    r = await store.lookup("33.000.167/0001-01")
    assert r.query == "33.000.167/0001-01"


async def test_get_meta_returns_build_metadata(fixture_registry: Path) -> None:
    meta = await store.get_meta()
    assert meta["schema_version"] == "1"
    assert meta["built_at"] == "2026-04-28T00:00:00Z"
    assert meta["content_sha256"] == "test_hash_abc"
