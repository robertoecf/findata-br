"""CVM company registration. Updated daily (Tue-Sat 08:00 BRT)."""

from __future__ import annotations

from pydantic import BaseModel

from findata._cache import TTLCache
from findata.sources.cvm.parser import fetch_csv

COMPANIES_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"


class Company(BaseModel):
    cnpj: str
    nome_social: str
    nome_comercial: str
    cod_cvm: str
    situacao: str
    setor: str
    categoria: str
    controle_acionario: str


_companies_cache: TTLCache[list[Company]] = TTLCache(ttl=900)


async def _load() -> list[Company]:
    rows = await fetch_csv(COMPANIES_URL)
    return [
        Company(
            cnpj=r.get("CNPJ_CIA", ""),
            nome_social=r.get("DENOM_SOCIAL", ""),
            nome_comercial=r.get("DENOM_COMERC", ""),
            cod_cvm=r.get("CD_CVM", ""),
            situacao=r.get("SIT", ""),
            setor=r.get("SETOR_ATIV", ""),
            categoria=r.get("CATEG_REG", ""),
            controle_acionario=r.get("CONTROLE_ACIONARIO", ""),
        )
        for r in rows
    ]


async def get_companies(only_active: bool = True) -> list[Company]:
    results = await _companies_cache.get_or_load(_load)
    if only_active:
        return [c for c in results if c.situacao == "ATIVO"]
    return results


async def search_company(query: str, only_active: bool = True) -> list[Company]:
    """Case-insensitive substring search on social and commercial names."""
    q = query.upper()
    return [
        c
        for c in await get_companies(only_active)
        if q in c.nome_social.upper() or q in c.nome_comercial.upper()
    ]
