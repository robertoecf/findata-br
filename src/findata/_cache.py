"""Tiny TTL cache helper for parsed-data caches.

Several sources (CVM companies, CVM funds, Tesouro bonds) used to each carry
their own `_data / _data_at / _TTL` module-level triple protected by the
`global` keyword. This module exposes a single `TTLCache` class that does the
same job, typed and dependency-free, so every source reuses one implementation.

It is deliberately minimal — no eviction policy, no metrics, no async locks.
Callers that need those should reach for `findata.http_client`'s LRU cache
(which is the right layer for per-URL response caching).
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    """Hold the result of an expensive async loader for ``ttl`` seconds.

    Usage:
        _catalog: TTLCache[list[Fund]] = TTLCache(ttl=3600)

        async def get_fund_catalog() -> list[Fund]:
            return await _catalog.get_or_load(_fetch_and_parse_catalog)
    """

    __slots__ = ("_data", "_loaded_at", "ttl")

    def __init__(self, ttl: float) -> None:
        self.ttl = ttl
        self._data: T | None = None
        self._loaded_at: float = 0.0

    def get(self) -> T | None:
        if self._data is None:
            return None
        if time.time() - self._loaded_at >= self.ttl:
            return None
        return self._data

    def set(self, value: T) -> None:
        self._data = value
        self._loaded_at = time.time()

    def invalidate(self) -> None:
        self._data = None
        self._loaded_at = 0.0

    async def get_or_load(self, loader: Callable[[], Awaitable[T]]) -> T:
        """Return the cached value or refresh via ``loader()`` if stale."""
        cached = self.get()
        if cached is not None:
            return cached
        value = await loader()
        self.set(value)
        return value
