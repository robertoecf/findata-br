"""CVM `dados.cvm.gov.br` directory listing helper.

CVM publishes everything under predictable paths like
`/dados/FI/DOC/<PRODUCT>/DADOS/<file>.zip` — but the *available* periods
(years or YYYYMM stamps) drift over time. Hard-coding date ranges goes
stale; HTTP-HEAD'ing every potential file is wasteful. So we scrape the
parent directory's HTML index once per call and let the listing tell us
what's actually there.

Inspired by gabrielguarisa/brdata's `_get_table_links` pattern.
"""

from __future__ import annotations

import re

from findata._cache import TTLCache
from findata.http_client import get_bytes

CVM_BASE = "https://dados.cvm.gov.br/dados"

_LISTING_PATTERN = re.compile(r'<a\s+href="([^"]+\.(?:zip|csv|txt|xls|xlsx))"', re.IGNORECASE)
_PERIOD_RE = re.compile(r"(\d{4}\d{2}|\d{4})(?:\D|$)")

# Cache HTML directory listings for 6h — they change at most once per month.
_listing_cache: TTLCache[dict[str, list[str]]] = TTLCache(ttl=6 * 3600)


async def list_files(category: str, product: str, sub: str = "DADOS") -> list[str]:
    """List every data file in a CVM directory.

    Args:
        category: top-level (e.g. ``"FI"``, ``"CIA_ABERTA"``).
        product: sub-category (e.g. ``"DOC/CDA"``, ``"DOC/LAMINA"``, ``"CAD"``).
        sub:     subdir under the product (defaults to the canonical ``"DADOS"``).

    Returns: list of filenames (just the last path component) sorted asc.
    """
    cached = _listing_cache.get()
    cached_dict = cached if cached is not None else {}
    key = f"{category}/{product}/{sub}"
    if key in cached_dict:
        return cached_dict[key]

    url = f"{CVM_BASE}/{category}/{product}/{sub}/"
    raw = await get_bytes(url, cache_ttl=6 * 3600)
    html = raw.decode("utf-8", errors="replace")
    files = sorted(set(_LISTING_PATTERN.findall(html)))
    cached_dict[key] = files
    _listing_cache.set(cached_dict)
    return files


async def list_periods(category: str, product: str) -> list[str]:
    """Extract just the period stamps (YYYYMM or YYYY) from a directory listing.

    e.g. listing ``[cda_fi_202601.zip, cda_fi_202602.zip]`` →
    ``["202601", "202602"]``.
    """
    files = await list_files(category, product)
    periods: set[str] = set()
    for name in files:
        match = _PERIOD_RE.search(name)
        if match:
            periods.add(match.group(1))
    return sorted(periods)


async def latest_period(category: str, product: str) -> str | None:
    """Most recent period stamp available for a CVM product, or None if empty."""
    periods = await list_periods(category, product)
    return periods[-1] if periods else None
