"""CVM IPE — Informações Periódicas e Eventuais (event stream).

The IPE annual file is the official feed of corporate communications filed
with CVM by listed companies: fatos relevantes, comunicados ao mercado,
calendários de eventos corporativos, atas de AGO/AGE, atos societários,
boletins de voto a distância, etc.

Each row is one document, with a stable protocolo, the responsible
companhia (CNPJ + código CVM), an event taxonomy (Categoria → Tipo →
Espécie → Assunto), filing date, and a download link to the original PDF
on CVM's RAD system.

The annual ZIPs grow ~2 MB so a CNPJ filter is optional but strongly
recommended for noisy issuers (Petrobras alone files hundreds of times
a year). The current-year file gets refreshed nightly.

Source: ``https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/IPE/DADOS/``
"""

from __future__ import annotations

from pydantic import BaseModel

from findata.sources.cvm._directory import CVM_BASE
from findata.sources.cvm.parser import fetch_csv_from_zip

IPE_URL = f"{CVM_BASE}/CIA_ABERTA/DOC/IPE/DADOS/ipe_cia_aberta_{{year}}.zip"


class IPEDocument(BaseModel):
    """One corporate communication filed at CVM via the IPE channel."""

    cnpj: str
    nome_empresa: str
    cod_cvm: str
    dt_referencia: str  # Data_Referencia — the event date
    dt_entrega: str  # Data_Entrega — when CVM received the filing
    categoria: str  # high-level bucket (e.g. "Fato Relevante", "Assembleia")
    tipo: str | None = None  # e.g. "AGE", "AGO" (when categoria=Assembleia)
    especie: str | None = None  # finer classification (e.g. "Boletim de voto")
    assunto: str | None = None  # free-text subject line
    tipo_apresentacao: str | None = None  # "AP - Apresentação" / "RE - Reapresentação"
    protocolo: str  # unique CVM protocol id
    versao: str
    link: str  # direct PDF download URL on CVM's RAD


def _opt(v: str | None) -> str | None:
    """Strip + drop empty. Handles NBSP (\\xa0) — Python's str.strip() treats it
    as whitespace, which matters for CVM feeds where free-text fields (Assunto,
    Especie, …) carry trailing NBSPs that would otherwise leak into exact-match
    deduplication downstream.
    """
    if v is None:
        return None
    s = v.strip()
    return s if s else None


def _parse(rows: list[dict[str, str]], cnpj: str | None) -> list[IPEDocument]:
    out: list[IPEDocument] = []
    for r in rows:
        row_cnpj = (r.get("CNPJ_Companhia") or r.get("CNPJ_CIA") or "").strip()
        if cnpj and row_cnpj != cnpj.strip():
            continue
        out.append(
            IPEDocument(
                cnpj=row_cnpj,
                nome_empresa=(r.get("Nome_Companhia") or r.get("DENOM_CIA") or "").strip(),
                cod_cvm=(r.get("Codigo_CVM") or r.get("CD_CVM") or "").strip(),
                dt_referencia=(r.get("Data_Referencia") or r.get("DT_REFER") or "").strip(),
                dt_entrega=(r.get("Data_Entrega") or r.get("DT_ENTREGA") or "").strip(),
                categoria=(r.get("Categoria") or "").strip(),
                tipo=_opt(r.get("Tipo")),
                especie=_opt(r.get("Especie")),
                assunto=_opt(r.get("Assunto")),
                tipo_apresentacao=_opt(r.get("Tipo_Apresentacao")),
                protocolo=(r.get("Protocolo_Entrega") or r.get("ID_DOC") or "").strip(),
                versao=(r.get("Versao") or r.get("VERSAO") or "").strip(),
                link=(r.get("Link_Download") or r.get("LINK_DOC") or "").strip(),
            )
        )
    return out


async def get_ipe(
    year: int,
    cnpj: str | None = None,
    categoria: str | None = None,
) -> list[IPEDocument]:
    """Every CVM filing for ``year`` (one row per document).

    Args:
        year: Filing year (>= 2003 — earlier years aren't published).
        cnpj: Optional issuer filter (strongly recommended for noisy
            issuers — Petrobras / Vale file hundreds of docs per year).
        categoria: Optional category filter (e.g. ``"Fato Relevante"``,
            ``"Assembleia"``, ``"Comunicado ao Mercado"``,
            ``"Calendário de Eventos Corporativos"``,
            ``"Aviso aos Acionistas"``). Case-sensitive — use the exact
            label as published by CVM.
    """
    url = IPE_URL.format(year=year)
    rows = await fetch_csv_from_zip(url, f"ipe_cia_aberta_{year}")
    out = _parse(rows, cnpj)
    if categoria:
        out = [d for d in out if d.categoria == categoria]
    return out
