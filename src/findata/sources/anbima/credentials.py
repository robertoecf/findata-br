"""ANBIMA credential loading from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass

from findata.auth.base import MissingCredentialsError


@dataclass(frozen=True)
class ANBIMACredentials:
    client_id: str
    client_secret: str


def load_anbima_credentials() -> ANBIMACredentials:
    """Read ANBIMA_* env vars or raise MissingCredentialsError."""
    cid = os.environ.get("ANBIMA_CLIENT_ID", "").strip()
    sec = os.environ.get("ANBIMA_CLIENT_SECRET", "").strip()
    if not cid or not sec:
        raise MissingCredentialsError(
            source="ANBIMA",
            env_vars=["ANBIMA_CLIENT_ID", "ANBIMA_CLIENT_SECRET"],
        )
    return ANBIMACredentials(client_id=cid, client_secret=sec)
