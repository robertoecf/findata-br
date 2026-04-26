"""ANBIMA HTTP client — Sensedia gateway with non-standard `access_token` header.

ANBIMA's API is fronted by a Sensedia API gateway. Two quirks worth noting:

1. The OAuth2 client_credentials token endpoint lives at
   `/oauth/access-token` (not `/oauth/token`).

2. Resource requests authenticate via two custom headers — `access_token`
   and `client_id` — instead of the spec-compliant `Authorization: Bearer`
   and no client_id. We model this with `header_name="access_token"` and
   `header_prefix=""` on the OAuth helper, plus an extra `client_id`
   header on every request.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

import httpx

from findata.auth.oauth2 import OAuth2ClientCredentials
from findata.sources.anbima.credentials import ANBIMACredentials, load_anbima_credentials

API_BASE = "https://api.anbima.com.br"
TOKEN_URL = f"{API_BASE}/oauth/access-token"


class ANBIMAOAuth(OAuth2ClientCredentials):
    """Client_credentials grant adapted to ANBIMA's Sensedia gateway."""

    _token_url = TOKEN_URL
    header_name = "access_token"
    header_prefix = ""  # raw token, no `Bearer ` prefix


class ANBIMAClient:
    """Async client that auto-injects the Sensedia auth headers."""

    def __init__(self, credentials: ANBIMACredentials) -> None:
        self._creds = credentials
        self._oauth = ANBIMAOAuth(credentials.client_id, credentials.client_secret)
        self._http = httpx.AsyncClient(
            base_url=API_BASE,
            timeout=30,
            headers={
                "User-Agent": "findata-br/0.1 (+https://github.com/robertoecf/findata-br)",
            },
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET an ANBIMA resource and return parsed JSON.

        Automatically injects the auth pair (`access_token` + `client_id`)
        and refreshes the token when it nears expiry. Caller deals with
        4xx/5xx by inspecting the raised `httpx.HTTPStatusError`.
        """
        headers = await self._oauth.auth_headers(self._http)
        headers["client_id"] = self._creds.client_id
        resp = await self._http.get(path, params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()


# ── Module-level lazy singleton ────────────────────────────────────
# Cached per event loop, since httpx.AsyncClient is loop-bound.
_clients: dict[int, ANBIMAClient] = {}


def get_default_client() -> ANBIMAClient:
    """Return a cached ANBIMAClient bound to the current event loop.

    Reads credentials from env vars on first use; raises
    MissingCredentialsError if they're absent.
    """
    try:
        loop_id = id(asyncio.get_running_loop())
    except RuntimeError:
        loop_id = -1
    client = _clients.get(loop_id)
    if client is None:
        client = ANBIMAClient(load_anbima_credentials())
        _clients[loop_id] = client
    return client


async def close_default_clients() -> None:
    """Close every cached ANBIMA client. Used in API shutdown hook."""
    for c in list(_clients.values()):
        with contextlib.suppress(Exception):
            await c.aclose()
    _clients.clear()
