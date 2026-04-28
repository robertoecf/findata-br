"""CVM FIP — Fundos de Investimento em Participações (informe trimestral).

Unlike FII / FIDC / regular FIs, the FIP feed is a single annual CSV
(no zip wrapper) with one row per fund per quarter and 53 columns
covering capital subscription, capital integralization, cotistas
breakdown by investor type, share-class details, and political/economic
rights.

We model it conservatively — a stable subset of the columns most
investors actually consume — and expose the raw row through ``raw=`` for
callers that need the long tail.

Source: ``https://dados.cvm.gov.br/dados/FIP/DOC/INF_TRIMESTRAL/DADOS/``
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from findata.sources.cvm._directory import CVM_BASE
from findata.sources.cvm.parser import fetch_csv

FIP_URL = f"{CVM_BASE}/FIP/DOC/INF_TRIMESTRAL/DADOS/inf_trimestral_fip_{{year}}.csv"


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


def _opt(v: str | None) -> str | None:
    if v is None:
        return None
    s = v.strip()
    return s if s else None


class FIPInforme(BaseModel):
    """One quarterly informe row for one FIP / classe de cotas."""

    cnpj: str
    nome_fundo: str
    dt_referencia: str  # DT_COMPTC — last day of the quarter
    patrimonio_liquido: float | None = None
    quantidade_cotas: float | None = None
    valor_patrimonial_cota: float | None = None
    num_cotistas: int | None = None
    publico_alvo: str | None = None
    capital_comprometido: float | None = None
    capital_subscrito: float | None = None
    capital_integralizado: float | None = None
    qtd_cota_subscrita: float | None = None
    qtd_cota_integralizada: float | None = None
    investido_via_fip_cota: float | None = None
    classe_cota: str | None = None
    direito_politico_classe: str | None = None
    direito_economico_classe: str | None = None
    cotistas_pf_pb: int | None = None  # private banking PF
    cotistas_pj_nao_financ_pb: int | None = None
    cotistas_banco: int | None = None
    cotistas_corretora_distrib: int | None = None
    cotistas_pj_financ: int | None = None
    cotistas_invnr: int | None = None  # investidor não residente
    cotistas_eapc: int | None = None
    cotistas_efpc: int | None = None
    cotistas_rpps: int | None = None
    cotistas_segur: int | None = None
    cotistas_capitaliz: int | None = None
    cotistas_fii: int | None = None
    cotistas_fi: int | None = None
    cotistas_distrib: int | None = None
    cotistas_outro: int | None = None
    raw: dict[str, str] | None = None  # full row when caller wants the long tail


def _safe_raw(r: dict[str, str]) -> dict[str, str]:
    """Drop the ``None`` keys ``csv.DictReader`` returns when a row has more
    fields than the header (real CVM data sometimes has trailing empty
    delimiters). Pydantic rejects them otherwise.
    """
    return {k: v for k, v in r.items() if isinstance(k, str) and isinstance(v, str)}


def _parse(r: dict[str, str], *, include_raw: bool) -> FIPInforme:
    return FIPInforme(
        cnpj=(r.get("CNPJ_FUNDO") or "").strip(),
        nome_fundo=(r.get("DENOM_SOCIAL") or "").strip(),
        dt_referencia=(r.get("DT_COMPTC") or "").strip(),
        patrimonio_liquido=_f(r.get("VL_PATRIM_LIQ")),
        quantidade_cotas=_f(r.get("QT_COTA")),
        valor_patrimonial_cota=_f(r.get("VL_PATRIM_COTA")),
        num_cotistas=_i(r.get("NR_COTST")),
        publico_alvo=_opt(r.get("PUBLICO_ALVO")),
        capital_comprometido=_f(r.get("VL_CAP_COMPROM")),
        capital_subscrito=_f(r.get("VL_CAP_SUBSCR")),
        capital_integralizado=_f(r.get("VL_CAP_INTEGR")),
        qtd_cota_subscrita=_f(r.get("QT_COTA_SUBSCR")),
        qtd_cota_integralizada=_f(r.get("QT_COTA_INTEGR")),
        investido_via_fip_cota=_f(r.get("VL_INVEST_FIP_COTA")),
        classe_cota=_opt(r.get("CLASSE_COTA")),
        direito_politico_classe=_opt(r.get("DIREITO_POLIT_CLASSE")),
        direito_economico_classe=_opt(r.get("DIREITO_ECON_CLASSE")),
        cotistas_pf_pb=_i(r.get("NR_COTST_SUBSCR_PF")),
        cotistas_pj_nao_financ_pb=_i(r.get("NR_COTST_SUBSCR_PJ_NAO_FINANC")),
        cotistas_banco=_i(r.get("NR_COTST_SUBSCR_BANCO")),
        cotistas_corretora_distrib=_i(r.get("NR_COTST_SUBSCR_CORRETORA_DISTRIB")),
        cotistas_pj_financ=_i(r.get("NR_COTST_SUBSCR_PJ_FINANC")),
        cotistas_invnr=_i(r.get("NR_COTST_SUBSCR_INVNR")),
        cotistas_eapc=_i(r.get("NR_COTST_SUBSCR_EAPC")),
        cotistas_efpc=_i(r.get("NR_COTST_SUBSCR_EFPC")),
        cotistas_rpps=_i(r.get("NR_COTST_SUBSCR_RPPS")),
        cotistas_segur=_i(r.get("NR_COTST_SUBSCR_SEGUR")),
        cotistas_capitaliz=_i(r.get("NR_COTST_SUBSCR_CAPITALIZ")),
        cotistas_fii=_i(r.get("NR_COTST_SUBSCR_FII")),
        cotistas_fi=_i(r.get("NR_COTST_SUBSCR_FI")),
        cotistas_distrib=_i(r.get("NR_COTST_SUBSCR_DISTRIB")),
        cotistas_outro=_i(r.get("NR_COTST_SUBSCR_OUTRO")),
        raw=_safe_raw(r) if include_raw else None,
    )


async def get_fip(
    year: int,
    cnpj: str | None = None,
    quarter: int | None = None,
    include_raw: bool = False,
) -> list[FIPInforme]:
    """Quarterly FIP filings for a given year.

    Args:
        year: 2010+ (CVM publishes since 2010).
        cnpj: Optional fund CNPJ filter.
        quarter: Optional quarter filter (1-4). When set, keeps only rows
            whose ``DT_COMPTC`` falls in the matching calendar quarter.
        include_raw: When ``True``, the parsed model carries the original
            CSV row in ``raw`` so callers can access the 20+ extra columns
            we don't model explicitly.
    """
    if quarter is not None and quarter not in {1, 2, 3, 4}:
        raise ValueError(f"quarter must be 1-4, got {quarter}")
    rows = await fetch_csv(FIP_URL.format(year=year))
    if cnpj:
        target = cnpj.strip()
        rows = [r for r in rows if (r.get("CNPJ_FUNDO") or "").strip() == target]
    if quarter is not None:
        # Quarters end on -03-31, -06-30, -09-30, -12-31 (DT_COMPTC).
        end_months = {1: "-03-", 2: "-06-", 3: "-09-", 4: "-12-"}
        prefix = end_months[quarter]
        rows = [r for r in rows if prefix in (r.get("DT_COMPTC") or "")]
    return [_parse(r, include_raw=include_raw) for r in rows]
