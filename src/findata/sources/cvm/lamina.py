"""CVM LAMINA — Lâmina de Informações Essenciais (regulatory factsheet).

The monthly LAMINA zip contains four CSVs: the main factsheet,
a portfolio-summary view, and yearly + monthly returns. Each fund
appears in every CSV at most once per period, so the files are small
(~10 MB total unzipped). Per-CNPJ filter is optional but recommended.
"""

from __future__ import annotations

import csv
import io
import zipfile
from typing import Any

from pydantic import BaseModel

from findata.http_client import get_bytes
from findata.sources.cvm._directory import CVM_BASE

LAMINA_URL = f"{CVM_BASE}/FI/DOC/LAMINA/DADOS/lamina_fi_{{ym}}.zip"


def _f(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def _i(v: Any) -> int | None:
    if v is None or v == "":
        return None
    try:
        return int(float(str(v).replace(",", ".")))
    except ValueError:
        return None


class FundLamina(BaseModel):
    """Main factsheet record — strategy, restrictions, alavancagem caps."""

    cnpj: str
    denom_social: str
    dt_referencia: str
    nome_fantasia: str | None = None
    publico_alvo: str | None = None
    restricao_investimento: str | None = None
    objetivo: str | None = None
    politica_investimento: str | None = None
    pct_pl_ativo_exterior: float | None = None
    pct_pl_ativo_credito_privado: float | None = None
    pct_pl_alavancagem: float | None = None


class FundLaminaReturnYear(BaseModel):
    cnpj: str
    dt_referencia: str
    ano: int | None = None
    rentabilidade_pct: float | None = None
    bench_pct: float | None = None
    bench_nome: str | None = None


class FundLaminaReturnMonth(BaseModel):
    cnpj: str
    dt_referencia: str
    mes_competencia: str | None = None
    rentabilidade_pct: float | None = None
    bench_pct: float | None = None


def _parse_main(row: dict[str, str]) -> FundLamina:
    return FundLamina(
        cnpj=(row.get("CNPJ_FUNDO_CLASSE") or row.get("CNPJ_FUNDO", "")).strip(),
        denom_social=row.get("DENOM_SOCIAL", "").strip(),
        dt_referencia=row.get("DT_COMPTC", "").strip(),
        nome_fantasia=row.get("NM_FANTASIA") or None,
        publico_alvo=row.get("PUBLICO_ALVO") or None,
        restricao_investimento=row.get("RESTR_INVEST") or None,
        objetivo=row.get("OBJETIVO") or None,
        politica_investimento=row.get("POLIT_INVEST") or None,
        pct_pl_ativo_exterior=_f(row.get("PR_PL_ATIVO_EXTERIOR")),
        pct_pl_ativo_credito_privado=_f(row.get("PR_PL_ATIVO_CRED_PRIV")),
        pct_pl_alavancagem=_f(row.get("PR_PL_ALAVANCAGEM")),
    )


def _parse_year(row: dict[str, str]) -> FundLaminaReturnYear:
    return FundLaminaReturnYear(
        cnpj=(row.get("CNPJ_FUNDO_CLASSE") or row.get("CNPJ_FUNDO", "")).strip(),
        dt_referencia=row.get("DT_COMPTC", "").strip(),
        ano=_i(row.get("ANO_RENTAB") or row.get("ANO")),
        rentabilidade_pct=_f(row.get("PR_RENTAB_ANO") or row.get("PR_RENTAB")),
        bench_pct=_f(row.get("PR_RENTAB_INDX") or row.get("PR_BENCH")),
        bench_nome=row.get("DS_INDX") or row.get("NM_BENCH") or None,
    )


def _parse_month(row: dict[str, str]) -> FundLaminaReturnMonth:
    return FundLaminaReturnMonth(
        cnpj=(row.get("CNPJ_FUNDO_CLASSE") or row.get("CNPJ_FUNDO", "")).strip(),
        dt_referencia=row.get("DT_COMPTC", "").strip(),
        mes_competencia=row.get("MES") or row.get("MES_RENTAB") or None,
        rentabilidade_pct=_f(row.get("PR_RENTAB_MES") or row.get("PR_RENTAB")),
        bench_pct=_f(row.get("PR_RENTAB_INDX") or row.get("PR_BENCH")),
    )


async def _read_csv(zf: zipfile.ZipFile, suffix: str) -> list[dict[str, str]]:
    for name in zf.namelist():
        if name.endswith(f"{suffix}.csv"):
            with zf.open(name) as f:
                return list(
                    csv.DictReader(io.StringIO(f.read().decode("iso-8859-1")), delimiter=";")
                )
    return []


async def get_fund_lamina(
    year: int,
    month: int,
    cnpj: str | None = None,
) -> list[FundLamina]:
    """Fund factsheet records for the given period (optionally filtered)."""
    ym = f"{year}{month:02d}"
    raw = await get_bytes(LAMINA_URL.format(ym=ym), cache_ttl=86400)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        rows = await _read_csv(zf, f"lamina_fi_{ym}")
    out = [_parse_main(r) for r in rows]
    if cnpj:
        out = [r for r in out if r.cnpj == cnpj.strip()]
    return out


async def get_fund_yearly_returns(
    year: int,
    month: int,
    cnpj: str | None = None,
) -> list[FundLaminaReturnYear]:
    """Per-year return rows attached to the lâmina."""
    ym = f"{year}{month:02d}"
    raw = await get_bytes(LAMINA_URL.format(ym=ym), cache_ttl=86400)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        rows = await _read_csv(zf, f"rentab_ano_{ym}")
    out = [_parse_year(r) for r in rows]
    if cnpj:
        out = [r for r in out if r.cnpj == cnpj.strip()]
    return out


async def get_fund_monthly_returns(
    year: int,
    month: int,
    cnpj: str | None = None,
) -> list[FundLaminaReturnMonth]:
    """Per-month return rows attached to the lâmina."""
    ym = f"{year}{month:02d}"
    raw = await get_bytes(LAMINA_URL.format(ym=ym), cache_ttl=86400)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        rows = await _read_csv(zf, f"rentab_mes_{ym}")
    out = [_parse_month(r) for r in rows]
    if cnpj:
        out = [r for r in out if r.cnpj == cnpj.strip()]
    return out
