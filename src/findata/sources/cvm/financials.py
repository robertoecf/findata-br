"""CVM financial statements — DFP (annual) and ITR (quarterly)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from findata.sources.cvm.parser import fetch_csv_from_zip

_DFP_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{year}.zip"
_ITR_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/itr_cia_aberta_{year}.zip"


class StatementType(StrEnum):
    BPA_CON = "BPA_con"
    BPA_IND = "BPA_ind"
    BPP_CON = "BPP_con"
    BPP_IND = "BPP_ind"
    DRE_CON = "DRE_con"
    DRE_IND = "DRE_ind"
    DFC_MI_CON = "DFC_MI_con"
    DFC_MI_IND = "DFC_MI_ind"
    DMPL_CON = "DMPL_con"
    DMPL_IND = "DMPL_ind"
    DVA_CON = "DVA_con"
    DVA_IND = "DVA_ind"


class FinancialEntry(BaseModel):
    cnpj: str
    nome_empresa: str
    cod_cvm: str
    dt_referencia: str
    versao: str
    cod_conta: str
    desc_conta: str
    valor: float
    moeda: str
    escala: str


def _parse(rows: list[dict[str, str]], cnpj: str | None) -> list[FinancialEntry]:
    results = []
    for r in rows:
        if cnpj and r.get("CNPJ_CIA", "") != cnpj:
            continue
        try:
            valor = float(r.get("VL_CONTA", "0"))
        except ValueError:
            valor = 0.0
        results.append(FinancialEntry(
            cnpj=r.get("CNPJ_CIA", ""),
            nome_empresa=r.get("DENOM_CIA", ""),
            cod_cvm=r.get("CD_CVM", ""),
            dt_referencia=r.get("DT_REFER", ""),
            versao=r.get("VERSAO", ""),
            cod_conta=r.get("CD_CONTA", ""),
            desc_conta=r.get("DS_CONTA", ""),
            valor=valor,
            moeda=r.get("MOEDA", "REAL"),
            escala=r.get("ESCALA_MOEDA", "MIL"),
        ))
    return results


async def _fetch(
    url_template: str, prefix: str,
    year: int, statement: StatementType, cnpj: str | None,
) -> list[FinancialEntry]:
    url = url_template.format(year=year)
    rows = await fetch_csv_from_zip(url, f"{prefix}_{statement.value}_{year}")
    return _parse(rows, cnpj)


async def get_dfp(
    year: int, statement: StatementType = StatementType.DRE_CON, cnpj: str | None = None,
) -> list[FinancialEntry]:
    return await _fetch(_DFP_URL, "dfp_cia_aberta", year, statement, cnpj)


async def get_itr(
    year: int, statement: StatementType = StatementType.DRE_CON, cnpj: str | None = None,
) -> list[FinancialEntry]:
    return await _fetch(_ITR_URL, "itr_cia_aberta", year, statement, cnpj)
