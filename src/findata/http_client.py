"""Shared async HTTP client with retry, LRU cache, and connection pooling."""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections import OrderedDict
from typing import Any
from urllib.parse import quote

import httpx

# ── LRU Cache with per-entry TTL ─────────────────────────────────

MAX_CACHE_SIZE = 2048
CACHE_TTL = 900  # 15 min default

_cache: OrderedDict[str, tuple[float, float, Any]] = OrderedDict()  # key → (ts, ttl, data)


def _cache_key(url: str, params: dict[str, Any] | None) -> str:
    raw = f"{url}:{sorted(params.items()) if params else ''}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_get(key: str) -> Any | None:
    if key not in _cache:
        return None
    cached_at, ttl, data = _cache[key]
    if time.time() - cached_at < ttl:
        _cache.move_to_end(key)
        return data
    del _cache[key]
    return None


def _cache_set(key: str, data: Any, ttl: float = CACHE_TTL) -> None:
    _cache[key] = (time.time(), ttl, data)
    _cache.move_to_end(key)
    while len(_cache) > MAX_CACHE_SIZE:
        _cache.popitem(last=False)


# ── OData URL Builder ─────────────────────────────────────────────

_ODATA_SAFE = "$'@/,()"


def _build_url(url: str, params: dict[str, Any] | None) -> str:
    """Build URL preserving literal $ and @ for OData APIs.

    httpx encodes $ as %24, which BCB Olinda rejects.
    """
    if not params:
        return url
    if not any(k[0] in "$@" for k in params):
        return url
    qs = "&".join(f"{k}={quote(str(v), safe=_ODATA_SAFE)}" for k, v in params.items())
    return f"{url}{'?' if '?' not in url else '&'}{qs}"


# ── Retry ─────────────────────────────────────────────────────────


def _should_retry(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500 or exc.response.status_code == 429
    return isinstance(exc, httpx.TransportError)


async def _retry_loop(fn, retries: int = 3) -> Any:  # type: ignore[no-untyped-def]
    """Call async `fn()` with exponential backoff on retryable errors."""
    last_exc: Exception | None = None
    for attempt in range(max(retries, 1)):
        try:
            return await fn()
        except Exception as exc:
            last_exc = exc
            if not _should_retry(exc) or attempt >= retries - 1:
                break
            await asyncio.sleep(2**attempt)
    raise last_exc  # type: ignore[misc]


# ── Shared Client (event-loop-aware) ──────────────────────────────

_client: httpx.AsyncClient | None = None
_client_loop_id: int | None = None


def _get_client() -> httpx.AsyncClient:
    global _client, _client_loop_id
    try:
        loop_id = id(asyncio.get_running_loop())
    except RuntimeError:
        loop_id = None

    if _client is None or _client.is_closed or _client_loop_id != loop_id:
        _client = httpx.AsyncClient(
            timeout=30,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
        _client_loop_id = loop_id
    return _client


async def close_client() -> None:
    global _client, _client_loop_id
    if _client and not _client.is_closed:
        await _client.aclose()
    _client = None
    _client_loop_id = None


# ── Public API ────────────────────────────────────────────────────


async def get_json(
    url: str,
    params: dict[str, Any] | None = None,
    cache_ttl: int = CACHE_TTL,
    retries: int = 3,
) -> Any:
    """GET JSON with LRU cache, connection pooling, and smart retry."""
    key = _cache_key(url, params)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    full_url = _build_url(url, params)
    use_params = None if full_url != url else params
    client = _get_client()

    async def _do() -> Any:
        resp = await client.get(full_url, params=use_params)
        resp.raise_for_status()
        return resp.json()

    data = await _retry_loop(_do, retries)
    _cache_set(key, data, cache_ttl)
    return data


async def get_bytes(
    url: str,
    retries: int = 3,
    cache_ttl: int = CACHE_TTL,
) -> bytes:
    """GET raw bytes with LRU cache and retry."""
    key = _cache_key(url, None)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    async with httpx.AsyncClient(timeout=120) as dl_client:

        async def _do() -> bytes:
            resp = await dl_client.get(url)
            resp.raise_for_status()
            return resp.content

        data = await _retry_loop(_do, retries)

    _cache_set(key, data, cache_ttl)
    return data
