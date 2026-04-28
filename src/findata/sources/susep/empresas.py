"""SUSEP LISTAEMPRESAS — supervised entities lookup table.

A single CSV with three fields: ``CodigoFIP``, ``NomeEntidade``, ``CNPJ``.
Covers all insurance companies, open pension funds, capitalization
companies, and resseguradoras under SUSEP's supervision. Useful as a
ticker-style code → CNPJ resolver and for sanity-checking other data
feeds that reference the FIP code.

Source: ``https://www2.susep.gov.br/menuestatistica/ses/download/LISTAEMPRESAS.csv``
"""

from __future__ import annotations

import csv
import io

from pydantic import BaseModel

from findata.http_client import get_bytes

LISTAEMPRESAS_URL = "https://www2.susep.gov.br/menuestatistica/ses/download/LISTAEMPRESAS.csv"


class EmpresaSusep(BaseModel):
    """One SUSEP-supervised entity."""

    codigo_fip: str  # SUSEP's internal "Ficha de Identificação do Participante" code
    nome: str
    cnpj: str  # raw 14-digit string (no formatting)


async def get_susep_empresas() -> list[EmpresaSusep]:
    """Full list of SUSEP-supervised entities. Cached for 24h."""
    raw = await get_bytes(LISTAEMPRESAS_URL, cache_ttl=86400)
    # The live SUSEP file ships with a leading blank line before the header
    # — strip it so csv.DictReader uses CodigoFIP/NomeEntidade/CNPJ as keys.
    text = raw.decode("iso-8859-1").lstrip()
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    out: list[EmpresaSusep] = []
    for r in reader:
        cod = (r.get("CodigoFIP") or "").strip()
        nome = (r.get("NomeEntidade") or "").strip()
        cnpj = (r.get("CNPJ") or "").strip()
        if not cod or not nome:
            continue
        out.append(EmpresaSusep(codigo_fip=cod, nome=nome, cnpj=cnpj))
    return out


async def search_susep_empresa(query: str) -> list[EmpresaSusep]:
    """Substring search against the entity name (case-insensitive)."""
    if len(query) < 2:  # noqa: PLR2004
        return []
    needle = query.upper()
    return [e for e in await get_susep_empresas() if needle in e.nome.upper()]
