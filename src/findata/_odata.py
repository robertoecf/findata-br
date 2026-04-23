"""Shared helpers for OData JSON responses.

BCB Olinda (Focus, PTAX) and IPEA all return the familiar
`{"@odata.context": ..., "value": [{...}, ...]}` envelope. This module hosts
the one generic parser we use across those sources so no adapter has to
hand-roll its own dict→Pydantic unpacking.
"""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)


def parse_odata(
    raw: dict[str, Any],
    model: type[M],
    mapping: dict[str, str],
) -> list[M]:
    """Parse the `value` array of an OData response into Pydantic models.

    ``mapping`` is ``{local_field: remote_field}``. Pydantic v2 coerces
    scalar types (int → str, str → float) automatically, so callers can
    keep their models ergonomic without bespoke validators.
    """
    return [
        model(**{local: item.get(remote) for local, remote in mapping.items()})
        for item in raw.get("value", [])
    ]
