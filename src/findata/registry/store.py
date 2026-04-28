"""Read-only async store over the embedded FTS5 ``registry.sqlite``.

One ``MATCH`` query handles exact-token (CNPJ, ticker, cod_cvm, FIP code)
and fuzzy-name lookups uniformly. The BM25 rank tells the caller which
kind they got — see :class:`findata.registry.models.Entity` for the
empirical rank buckets.

The SQLite file ships embedded inside the wheel at
``findata/data/registry.sqlite``. ``REGISTRY_PATH`` resolves it
relative to this module so tests can monkey-patch it to a fixture file.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import aiosqlite

from findata.registry.models import Entity, LookupResult

# Resolved at import time — but importable code can override before the first
# query (tests do this). The path layout reflects:
#   src/findata/registry/store.py   ← __file__
#   src/findata/data/registry.sqlite
REGISTRY_PATH: Path = Path(__file__).resolve().parent.parent / "data" / "registry.sqlite"

_MIN_QUERY_LEN = 2


def _normalize_query(q: str) -> str:
    """Turn a user query into FTS5 MATCH-ready text.

    Two variants get OR'd because we can't tell from a string alone whether
    a token-y input is a fragmented code or a multi-word name:

    * **spaced**: tokens joined with single spaces. FTS5 ``MATCH`` does
      implicit AND, so multi-word names like ``"banco do brasil"`` work.
    * **joined**: same tokens concatenated. Recovers codes the user typed
      with punctuation: ``"33.000.167/0001-01"`` → ``"33000167000101"`` —
      which is the literal token stored in the registry.

    The OR'd form ``(spaced) OR (joined)`` lets FTS5 try both. The branch
    that doesn't match contributes nothing; the matching branch wins on
    BM25 rank. Neither costs anything when both are empty.

    ASCII-fold + uppercase first because registry tokens are stored that
    way (build_registry's ``normalize_token`` / ``normalize_name``).

    Returns ``""`` for queries shorter than ``_MIN_QUERY_LEN`` chars or
    with no alphanumeric content — caller treats as "no useful query".
    """
    if not q or len(q.strip()) < _MIN_QUERY_LEN:
        return ""
    nfkd = unicodedata.normalize("NFKD", q)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    upper = ascii_only.upper()
    tokens = [t for t in re.split(r"[^A-Z0-9]+", upper) if t]
    if not tokens:
        return ""
    spaced = " ".join(tokens)
    joined = "".join(tokens)
    # Single token, or already collapsed: spaced and joined are identical.
    if spaced == joined:
        return spaced
    return f"({spaced}) OR ({joined})"


def _row_to_entity(row: aiosqlite.Row) -> Entity:
    """Decode one FTS5 row into an :class:`Entity` with rank attached."""
    payload = json.loads(row["payload"])
    payload["rank"] = row["rank"]
    return Entity(**payload)


async def lookup(query: str, limit: int = 20) -> LookupResult:
    """Resolve ``query`` against the registry, ordered by FTS5 BM25 rank.

    Args:
        query: user input — CNPJ (with or without mask), B3 ticker
            (PETR4, ITUB4), CVM code (9512), SUSEP FIP code, or a name
            fragment (substring of nome_social or nome_comercial).
        limit: cap on returned entities (default 20).

    Returns an empty result for queries shorter than 2 chars or with no
    alphanumeric content. Never raises for "no match" — empty list is
    the honest answer.
    """
    fts = _normalize_query(query)
    if not fts:
        return LookupResult(query=query, entities=[], total=0)

    async with aiosqlite.connect(str(REGISTRY_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT rank, payload FROM entities "
            "WHERE searchable MATCH ? ORDER BY rank LIMIT ?",
            (fts, limit),
        )
        rows = await cursor.fetchall()

    entities = [_row_to_entity(r) for r in rows]
    return LookupResult(query=query, entities=entities, total=len(entities))


async def get_meta() -> dict[str, str]:
    """Return the build metadata KV table — useful for /healthz and CI."""
    async with aiosqlite.connect(str(REGISTRY_PATH)) as db:
        cursor = await db.execute("SELECT key, value FROM meta")
        rows = await cursor.fetchall()
    return {k: v for (k, v) in rows}
