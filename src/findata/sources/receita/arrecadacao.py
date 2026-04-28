"""Receita Federal — arrecadação por UF (federal tax revenue, monthly).

A single CSV with one row per (year, month, UF) and ~45 columns of
federal tax / contribution categories: IRPF, IRPJ, IRRF, COFINS, PIS,
CSLL, IPI sub-categories, IOF, CIDE, CPSSS, etc. Series since 2000.

We surface it as a long-form record — one row per (period × UF ×
tributo) — so callers can pivot however they need without committing
to today's column structure (Receita has added/renamed columns over
time; the long-form view is forward-compatible).

Source URL: ``https://www.gov.br/receitafederal/dados/arrecadacao-estado.csv``
"""

from __future__ import annotations

import csv
import io
from datetime import datetime

from pydantic import BaseModel

from findata.http_client import get_bytes

ARRECADACAO_URL = "https://www.gov.br/receitafederal/dados/arrecadacao-estado.csv"

# Columns that aren't tax categories — skipped when building rows.
_NON_TAX_COLS = {"Ano", "Mês", "UF"}

# Pt-BR month names → numbers (case-insensitive). Receita writes them
# capitalised; we normalise for lookup.
_MESES_PT = {
    "Janeiro": 1,
    "Fevereiro": 2,
    "Março": 3,
    "Abril": 4,
    "Maio": 5,
    "Junho": 6,
    "Julho": 7,
    "Agosto": 8,
    "Setembro": 9,
    "Outubro": 10,
    "Novembro": 11,
    "Dezembro": 12,
}


def _f(v: str | None) -> float | None:
    """Parse arrecadação cell. Empty / null → None. Values are integers
    in R$ (no decimal), but we cast to float for forward-compat with
    new columns that might use decimals."""
    if v is None or not v.strip():
        return None
    s = v.strip().replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _i_year(v: str) -> int | None:
    s = v.strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _i_month(v: str) -> int | None:
    """Accept ``"Janeiro"`` / ``"01"`` / ``"1"``."""
    s = v.strip()
    if not s:
        return None
    if s in _MESES_PT:
        return _MESES_PT[s]
    try:
        n = int(s)
        if 1 <= n <= 12:  # noqa: PLR2004 — calendar bound
            return n
    except ValueError:
        pass
    return None


class ArrecadacaoMensal(BaseModel):
    """One (year × month × UF × tributo) tuple with the value in R$."""

    ano: int
    mes: int
    uf: str
    tributo: str
    valor: float | None
    dt_referencia: str  # YYYY-MM-01 — for time-series convenience


def _row_to_records(row: dict[str, str]) -> list[ArrecadacaoMensal]:
    ano = _i_year(row.get("Ano", ""))
    mes = _i_month(row.get("Mês", ""))
    uf = (row.get("UF") or "").strip()
    if ano is None or mes is None or not uf:
        return []
    dt = datetime(ano, mes, 1).strftime("%Y-%m-%d")
    out: list[ArrecadacaoMensal] = []
    for col, raw in row.items():
        if col in _NON_TAX_COLS or col is None:
            continue
        # Trailing empty column ("...;\n") gives col=="", skip it.
        col_clean = col.strip()
        if not col_clean:
            continue
        out.append(
            ArrecadacaoMensal(
                ano=ano,
                mes=mes,
                uf=uf,
                tributo=col_clean,
                valor=_f(raw),
                dt_referencia=dt,
            )
        )
    return out


async def get_arrecadacao(
    year: int | None = None,
    month: int | None = None,
    uf: str | None = None,
    tributo: str | None = None,
) -> list[ArrecadacaoMensal]:
    """Federal-tax revenue, long-form (one row per period × UF × tributo).

    Args:
        year: Filter by year (4-digit). Default: all years (2000+).
        month: Filter by calendar month (1-12).
        uf: Filter by state UF (e.g. ``"SP"``, ``"RJ"``).
        tributo: Substring match against the tributo column label
            (case-sensitive, partial OK — e.g. ``"COFINS"`` or ``"IRPF"``).
            See :func:`list_tributos` for the full menu.

    The full file has ~25k rows × 45 columns ≈ 1.1M long-form records.
    Filter aggressively for big jobs.
    """
    raw = await get_bytes(ARRECADACAO_URL, cache_ttl=86400)
    text = raw.decode("iso-8859-1")
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    out: list[ArrecadacaoMensal] = []
    uf_target = uf.upper().strip() if uf else None
    for row in reader:
        if year is not None and _i_year(row.get("Ano", "")) != year:
            continue
        if month is not None and _i_month(row.get("Mês", "")) != month:
            continue
        if uf_target and (row.get("UF") or "").strip() != uf_target:
            continue
        records = _row_to_records(row)
        if tributo:
            records = [r for r in records if tributo in r.tributo]
        out.extend(records)
    return out


async def list_tributos() -> list[str]:
    """Return the current list of tributo column names from the CSV header."""
    raw = await get_bytes(ARRECADACAO_URL, cache_ttl=86400)
    text = raw.decode("iso-8859-1")
    reader = csv.reader(io.StringIO(text), delimiter=";")
    headers = next(reader, [])
    return [h.strip() for h in headers if h.strip() and h not in _NON_TAX_COLS]
