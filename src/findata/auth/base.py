"""Common exceptions for credential-aware data sources."""

from __future__ import annotations


class AuthError(Exception):
    """Authentication or authorization failed against the upstream."""


class MissingCredentialsError(AuthError):
    """Required credentials are not configured (env vars unset)."""

    def __init__(self, source: str, env_vars: list[str]) -> None:
        self.source = source
        self.env_vars = env_vars
        super().__init__(
            f"{source} requires credentials. Set environment variables: "
            f"{', '.join(env_vars)}. See docs/SOURCES_WITH_AUTH.md."
        )
