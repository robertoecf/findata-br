"""Pydantic models for registry payloads."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Entity(BaseModel):
    """One unified entity profile, as stored in the FTS5 registry.

    The ``rank`` field is added at query time from FTS5's BM25 score —
    more negative means more relevant. Empirical buckets on our data:

    * ``rank < -5.0`` — exact match on a unique token (CNPJ, ticker,
      cod_cvm, codigo_fip). High confidence "this is THE entity".
    * ``-5.0 <= rank < -1.0`` — phrase / multi-token name match.
      Medium confidence; usually a list rather than a single hit.
    * ``rank >= -1.0`` — broad / common-token match. Low confidence,
      treat as candidate list to be browsed.

    Schema mirrors the JSON payload written by ``scripts/build_registry.py``;
    keeping them in lockstep is a contract, not an accident — break it and
    new builds will fail validation here.
    """

    cnpj: str | None = None
    nome: str
    kind: str = Field(description="cvm_company | cvm_fund | susep")
    sources: list[str] = Field(default_factory=list)
    tickers: list[str] = Field(default_factory=list)
    cod_cvm: str | None = None
    codigo_fip: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
    rank: float | None = None


class LookupResult(BaseModel):
    """Response shape for ``/registry/lookup`` and the Python ``lookup()`` API."""

    query: str
    entities: list[Entity]
    total: int
