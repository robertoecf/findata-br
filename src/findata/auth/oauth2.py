"""OAuth2 client_credentials flow with in-process token caching.

Generic enough to fit ANBIMA, B3, SUSEP — every BR financial provider that
exposes the spec-compliant client_credentials grant. The provider quirks
(non-standard headers, alternate token-field names) are handled by
subclasses or by passing a `header_name` override.
"""

from __future__ import annotations

import asyncio
import base64
import time
from dataclasses import dataclass

import httpx

from findata.auth.base import AuthError

_HTTP_BAD_REQUEST = 400


@dataclass(frozen=True)
class OAuth2Token:
    access_token: str
    expires_at: float  # epoch seconds when this token becomes invalid

    def is_expired(self, safety_margin: float = 60.0) -> bool:
        """True if the token expires in less than `safety_margin` seconds."""
        return time.time() + safety_margin >= self.expires_at


class OAuth2ClientCredentials:
    """Reusable async client_credentials grant + token cache.

    Subclass and override `_token_url`, `_extra_token_form`, or
    `header_name` for provider-specific quirks (Sensedia gateways like
    ANBIMA, for instance, expect the token in the `access_token` header
    instead of `Authorization: Bearer`).
    """

    #: Fully-qualified token endpoint URL.
    _token_url: str = ""

    #: Extra form fields appended to the body of the token request.
    _extra_token_form: dict[str, str] = {}  # noqa: RUF012 — class-level constant

    #: HTTP header name expected by the upstream resource server.
    header_name: str = "Authorization"

    #: Prefix prepended to the token value (Bearer / "" / etc.)
    header_prefix: str = "Bearer "

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: OAuth2Token | None = None
        self._lock = asyncio.Lock()

    # ── Public API ────────────────────────────────────────────────

    async def get_token(self, http: httpx.AsyncClient) -> OAuth2Token:
        """Return a non-expired token, refreshing if necessary."""
        async with self._lock:
            if self._token is None or self._token.is_expired():
                self._token = await self._fetch(http)
            return self._token

    async def auth_headers(self, http: httpx.AsyncClient) -> dict[str, str]:
        """Build the headers a resource request needs to be authenticated."""
        token = await self.get_token(http)
        return {self.header_name: f"{self.header_prefix}{token.access_token}"}

    def reset(self) -> None:
        """Drop the cached token (forcing the next call to refresh)."""
        self._token = None

    # ── Internals ─────────────────────────────────────────────────

    def _basic_auth_header(self) -> str:
        creds = f"{self._client_id}:{self._client_secret}".encode()
        return "Basic " + base64.b64encode(creds).decode()

    async def _fetch(self, http: httpx.AsyncClient) -> OAuth2Token:
        if not self._token_url:
            raise AuthError(f"{type(self).__name__} did not set a _token_url")
        body = {"grant_type": "client_credentials", **self._extra_token_form}
        headers = {
            "Authorization": self._basic_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        resp = await http.post(self._token_url, data=body, headers=headers, timeout=15)
        if resp.status_code >= _HTTP_BAD_REQUEST:
            raise AuthError(
                f"OAuth2 token request to {self._token_url} failed "
                f"({resp.status_code}): {resp.text[:200]}"
            )
        payload = resp.json()
        try:
            access = str(payload["access_token"])
            ttl = int(payload.get("expires_in", 3600))
        except (KeyError, TypeError, ValueError) as exc:
            raise AuthError(f"unexpected token response shape: {payload!r}") from exc
        return OAuth2Token(access_token=access, expires_at=time.time() + ttl)
