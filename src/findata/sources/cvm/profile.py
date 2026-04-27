"""CVM PERFIL_MENSAL — Monthly investor / profile breakdown per fund."""

from __future__ import annotations

import csv
import io
from typing import Any

from pydantic import BaseModel

from findata.http_client import get_bytes
from findata.sources.cvm._directory import CVM_BASE

PROFILE_URL = f"{CVM_BASE}/FI/DOC/PERFIL_MENSAL/DADOS/perfil_mensal_fi_{{ym}}.csv"


def _i(v: Any) -> int | None:
    if v is None or v == "":
        return None
    try:
        return int(float(str(v).replace(",", ".")))
    except ValueError:
        return None


class FundProfile(BaseModel):
    """Cotistas breakdown plus other monthly profile metrics."""

    cnpj: str
    denom_social: str
    dt_referencia: str
    versao: str | None = None
    cotistas_pf_private: int | None = None
    cotistas_pf_varejo: int | None = None
    cotistas_pj_nao_financ_private: int | None = None
    cotistas_pj_nao_financ_varejo: int | None = None
    cotistas_banco: int | None = None
    cotistas_corretora_distrib: int | None = None
    cotistas_pj_financ: int | None = None


def _parse(row: dict[str, str]) -> FundProfile:
    return FundProfile(
        cnpj=(row.get("CNPJ_FUNDO_CLASSE") or row.get("CNPJ_FUNDO", "")).strip(),
        denom_social=row.get("DENOM_SOCIAL", "").strip(),
        dt_referencia=row.get("DT_COMPTC", "").strip(),
        versao=row.get("VERSAO") or None,
        cotistas_pf_private=_i(row.get("NR_COTST_PF_PB")),
        cotistas_pf_varejo=_i(row.get("NR_COTST_PF_VAREJO")),
        cotistas_pj_nao_financ_private=_i(row.get("NR_COTST_PJ_NAO_FINANC_PB")),
        cotistas_pj_nao_financ_varejo=_i(row.get("NR_COTST_PJ_NAO_FINANC_VAREJO")),
        cotistas_banco=_i(row.get("NR_COTST_BANCO")),
        cotistas_corretora_distrib=_i(row.get("NR_COTST_CORRETORA_DISTRIB")),
        cotistas_pj_financ=_i(row.get("NR_COTST_PJ_FINANC")),
    )


async def get_fund_profile(
    year: int,
    month: int,
    cnpj: str | None = None,
) -> list[FundProfile]:
    """Monthly investor profile breakdown for one fund or all of them."""
    ym = f"{year}{month:02d}"
    raw = await get_bytes(PROFILE_URL.format(ym=ym), cache_ttl=86400)
    text = raw.decode("iso-8859-1", errors="replace")
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    out: list[FundProfile] = []
    target = cnpj.strip() if cnpj else None
    for row in reader:
        row_cnpj = (row.get("CNPJ_FUNDO_CLASSE") or row.get("CNPJ_FUNDO", "")).strip()
        if target is not None and row_cnpj != target:
            continue
        out.append(_parse(row))
    return out
