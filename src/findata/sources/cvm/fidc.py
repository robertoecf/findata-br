"""CVM FIDC — Fundos de Investimento em Direitos Creditórios.

The FIDC monthly ZIP fans out into 12 specialised CSVs (``tab_I`` through
``tab_X``, plus two sub-tables of TAB_X). Each tab is a structured view
of one regulatory schedule:

| Tab          | Schedule                                                 |
|--------------|----------------------------------------------------------|
| TAB_I        | Cadastral — admin, classe, condomínio                    |
| TAB_II       | Composição da carteira (industrial / imobiliário / …)    |
| TAB_III      | Passivo + derivativos                                    |
| TAB_IV       | Patrimônio líquido (final + médio)                       |
| TAB_V / VI   | Direitos creditórios a vencer (30/60/90/120/150+ dias)   |
| TAB_VII      | Direitos creditórios com / sem risco                     |
| TAB_IX / X   | Inadimplência, garantias, originadores                   |

We ship the three highest-density facets — ``geral`` (TAB_I), ``pl``
(TAB_IV) and ``direitos_creditorios`` (TAB_VII). Other tabs can be
loaded ad-hoc with the generic helper.

Source: ``https://dados.cvm.gov.br/dados/FIDC/DOC/INF_MENSAL/DADOS/``
(monthly ZIPs, available since 2025-01)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from findata.sources.cvm._directory import CVM_BASE
from findata.sources.cvm.parser import fetch_csv_from_zip

FIDC_URL = f"{CVM_BASE}/FIDC/DOC/INF_MENSAL/DADOS/inf_mensal_fidc_{{ym}}.zip"


def _f(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def _opt(v: str | None) -> str | None:
    if v is None:
        return None
    s = v.strip()
    return s if s else None


def _filter_cnpj(rows: list[dict[str, str]], cnpj: str | None) -> list[dict[str, str]]:
    if not cnpj:
        return rows
    target = cnpj.strip()
    return [r for r in rows if (r.get("CNPJ_FUNDO_CLASSE") or "").strip() == target]


class FIDCGeneral(BaseModel):
    """TAB_I — cadastral facet."""

    cnpj: str
    nome_fundo: str
    dt_referencia: str
    tipo_fundo_classe: str | None = None
    classe_unica: str | None = None
    classe: str | None = None
    cnpj_classe: str | None = None
    condominio: str | None = None
    cnpj_administrador: str | None = None
    nome_administrador: str | None = None


class FIDCPatrimonio(BaseModel):
    """TAB_IV — patrimônio líquido (final + médio)."""

    cnpj: str
    nome_fundo: str
    dt_referencia: str
    pl_final: float | None = None
    pl_medio: float | None = None


class FIDCDireitosCreditorios(BaseModel):
    """TAB_VII — direitos creditórios com / sem risco + vencidos / a vencer."""

    cnpj: str
    nome_fundo: str
    dt_referencia: str
    qtd_com_risco: float | None = None
    valor_com_risco: float | None = None
    qtd_sem_risco: float | None = None
    valor_sem_risco: float | None = None
    qtd_vencidos_a_adquirir: float | None = None
    valor_vencidos_a_adquirir: float | None = None


def _parse_general(r: dict[str, str]) -> FIDCGeneral:
    return FIDCGeneral(
        cnpj=(r.get("CNPJ_FUNDO_CLASSE") or "").strip(),
        nome_fundo=(r.get("DENOM_SOCIAL") or "").strip(),
        dt_referencia=(r.get("DT_COMPTC") or "").strip(),
        tipo_fundo_classe=_opt(r.get("TP_FUNDO_CLASSE")),
        classe_unica=_opt(r.get("CLASSE_UNICA")),
        classe=_opt(r.get("CLASSE")),
        cnpj_classe=_opt(r.get("CNPJ_CLASSE")),
        condominio=_opt(r.get("CONDOM")),
        cnpj_administrador=_opt(r.get("CNPJ_ADMIN")),
        nome_administrador=_opt(r.get("ADMIN")),
    )


def _parse_pl(r: dict[str, str]) -> FIDCPatrimonio:
    return FIDCPatrimonio(
        cnpj=(r.get("CNPJ_FUNDO_CLASSE") or "").strip(),
        nome_fundo=(r.get("DENOM_SOCIAL") or "").strip(),
        dt_referencia=(r.get("DT_COMPTC") or "").strip(),
        pl_final=_f(r.get("TAB_IV_A_VL_PL")),
        pl_medio=_f(r.get("TAB_IV_B_VL_PL_MEDIO")),
    )


def _parse_direitos(r: dict[str, str]) -> FIDCDireitosCreditorios:
    return FIDCDireitosCreditorios(
        cnpj=(r.get("CNPJ_FUNDO_CLASSE") or "").strip(),
        nome_fundo=(r.get("DENOM_SOCIAL") or "").strip(),
        dt_referencia=(r.get("DT_COMPTC") or "").strip(),
        qtd_com_risco=_f(r.get("TAB_VII_A1_1_QT_DIRCRED_RISCO")),
        valor_com_risco=_f(r.get("TAB_VII_A1_2_VL_DIRCRED_RISCO")),
        qtd_sem_risco=_f(r.get("TAB_VII_A2_1_QT_DIRCRED_SEM_RISCO")),
        valor_sem_risco=_f(r.get("TAB_VII_A2_2_VL_DIRCRED_SEM_RISCO")),
        qtd_vencidos_a_adquirir=_f(r.get("TAB_VII_A3_1_QT_DIRCRED_VENC_AD")),
        valor_vencidos_a_adquirir=_f(r.get("TAB_VII_A3_2_VL_DIRCRED_VENC_AD")),
    )


async def get_fidc_geral(
    year: int,
    month: int,
    cnpj: str | None = None,
) -> list[FIDCGeneral]:
    """TAB_I — cadastral facet (admin, classe, condomínio)."""
    ym = f"{year}{month:02d}"
    rows = await fetch_csv_from_zip(
        FIDC_URL.format(ym=ym),
        f"inf_mensal_fidc_tab_I_{ym}",
    )
    rows = _filter_cnpj(rows, cnpj)
    return [_parse_general(r) for r in rows]


async def get_fidc_pl(
    year: int,
    month: int,
    cnpj: str | None = None,
) -> list[FIDCPatrimonio]:
    """TAB_IV — patrimônio líquido (final + médio)."""
    ym = f"{year}{month:02d}"
    rows = await fetch_csv_from_zip(
        FIDC_URL.format(ym=ym),
        f"inf_mensal_fidc_tab_IV_{ym}",
    )
    rows = _filter_cnpj(rows, cnpj)
    return [_parse_pl(r) for r in rows]


async def get_fidc_direitos_creditorios(
    year: int,
    month: int,
    cnpj: str | None = None,
) -> list[FIDCDireitosCreditorios]:
    """TAB_VII — direitos creditórios com/sem risco + vencidos a adquirir."""
    ym = f"{year}{month:02d}"
    rows = await fetch_csv_from_zip(
        FIDC_URL.format(ym=ym),
        f"inf_mensal_fidc_tab_VII_{ym}",
    )
    rows = _filter_cnpj(rows, cnpj)
    return [_parse_direitos(r) for r in rows]
