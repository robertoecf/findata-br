"""ANEEL — Resultado de leilões de geração e transmissão de energia elétrica.

Two long-form CSVs published by ANEEL/SEL covering every regulated
electricity-sector auction since 1999 (transmissão) and 2005 (geração).
Each row is one (leilão × winning empreendimento) tuple with auction
date, price, contract length, investment, and the winning company.

| File                          | Coverage                                    |
|-------------------------------|---------------------------------------------|
| `resultado-leiloes-geracao`   | New-energy auctions (A-3, A-5, A-6, LFA…)   |
| `resultado-leiloes-transmissao` | Transmission-line concessions             |

Source: ``https://dadosabertos.aneel.gov.br/dataset/resultado-de-leiloes``
The CSV resource UUIDs below are stable — ANEEL re-publishes the same
URL monthly.
"""

from __future__ import annotations

import csv
import io
from typing import Any

from pydantic import BaseModel

from findata.http_client import get_bytes

# Stable resource URLs from the ANEEL CKAN package "resultado-de-leiloes".
# (UUIDs are immutable; ANEEL re-uploads the same files at these paths.)
LEILOES_GERACAO_URL = (
    "https://dadosabertos.aneel.gov.br/dataset/"
    "593537c6-9e0e-4ed9-817a-2c5d5de05147/resource/"
    "a1328fc1-f06b-437d-8893-57ac2c8103df/download/resultado-leiloes-geracao.csv"
)
LEILOES_TRANSMISSAO_URL = (
    "https://dadosabertos.aneel.gov.br/dataset/"
    "593537c6-9e0e-4ed9-817a-2c5d5de05147/resource/"
    "453cb742-8089-4c16-aaf2-42088b5553dc/download/resultado-leiloes-transmissao.csv"
)


def _f_br(v: Any) -> float | None:
    """Brazilian-decimal aware float parser. ``"140,00"`` → 140.00,
    ``"158.641.610,00"`` → 158641610.00. Empty → None.
    """
    if v is None or not str(v).strip():
        return None
    s = str(v).strip()
    s = s.replace(".", "").replace(",", ".") if "," in s else s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def _i(v: Any) -> int | None:
    if v is None or not str(v).strip():
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


class LeilaoGeracao(BaseModel):
    """One winning generation-auction record."""

    ano_leilao: int | None = None
    dt_leilao: str | None = None  # YYYY-MM-DD
    num_leilao: str | None = None  # e.g. "2005/2"
    num_leilao_ccee: str | None = None
    tipo_leilao: str | None = None  # "A-5", "A-3", "A-6", "LFA", "LEN"
    nome_empreendimento: str | None = None
    cod_ceg: str | None = None  # Código de Empreendimento de Geração
    tipo_geracao: str | None = None  # UTE / UHE / EOL / UFV / PCH / CGH / etc.
    fonte_energia: str | None = None  # Hídrica / Eólica / Solar / Biomassa / etc.
    detalhamento_fonte: str | None = None  # e.g. "Bagaço de Cana"
    potencia_instalada_mw: float | None = None
    garantia_fisica_mw_med: float | None = None
    energia_vendida_mw_med: float | None = None
    preco_teto_brl_mwh: float | None = None
    preco_leilao_brl_mwh: float | None = None
    desagio_pct: float | None = None
    investimento_previsto_brl: float | None = None
    duracao_contrato_anos: int | None = None
    uf: str | None = None
    empresa_vencedora: str | None = None


class LeilaoTransmissao(BaseModel):
    """One winning transmission-auction record (LT or substation lot)."""

    ano_leilao: int | None = None
    dt_leilao: str | None = None
    num_leilao: str | None = None
    num_lote: int | None = None
    nome_empreendimento: str | None = None
    uf: str | None = None
    prazo_construcao_meses: int | None = None
    extensao_linha_km: float | None = None
    subestacoes_mva: float | None = None
    investimento_previsto_brl: float | None = None
    rap_edital_brl: float | None = None
    rap_vencedor_brl: float | None = None
    desagio_pct: float | None = None
    nome_vencedor: str | None = None


def _parse_geracao(r: dict[str, str]) -> LeilaoGeracao:
    return LeilaoGeracao(
        ano_leilao=_i(r.get("AnoLeilao")),
        dt_leilao=_opt(r.get("DatLeilao")),
        num_leilao=_opt(r.get("NumLeilao")),
        num_leilao_ccee=_opt(r.get("DscNumeroLeilaoCCEE")),
        tipo_leilao=_opt(r.get("DscTipoLeilao")),
        nome_empreendimento=_opt(r.get("NomEmpreendimento")),
        cod_ceg=_opt(r.get("CodCEG")),
        tipo_geracao=_opt(r.get("SigTipoGeracao")),
        fonte_energia=_opt(r.get("DscFonteEnergia")),
        detalhamento_fonte=_opt(r.get("DscDetalhamentoFonteEnergia")),
        potencia_instalada_mw=_f_br(r.get("MdaPotenciaInstaladaMW")),
        garantia_fisica_mw_med=_f_br(r.get("MdaGarantiaFisicaSEL")),
        energia_vendida_mw_med=_f_br(r.get("VlrEnergiaVendida")),
        preco_teto_brl_mwh=_f_br(r.get("VlrPrecoTeto")),
        preco_leilao_brl_mwh=_f_br(r.get("VlrPrecoLeilao")),
        desagio_pct=_f_br(r.get("VlrDesagio")),
        investimento_previsto_brl=_f_br(r.get("VlrInvestimentoPrevisto")),
        duracao_contrato_anos=_i(r.get("MdaDuracaoContrato")),
        uf=_opt(r.get("SigUFPrincipal")),
        empresa_vencedora=_opt(r.get("DscEmpresaVencedora")),
    )


def _parse_transmissao(r: dict[str, str]) -> LeilaoTransmissao:
    return LeilaoTransmissao(
        ano_leilao=_i(r.get("AnoLeilao")),
        dt_leilao=_opt(r.get("DatLeilao")),
        num_leilao=_opt(r.get("NumLeilao")),
        num_lote=_i(r.get("NumLoteLeilao")),
        nome_empreendimento=_opt(r.get("NomEmpreendimento")),
        uf=_opt(r.get("SigUFPrincipal")),
        prazo_construcao_meses=_i(r.get("QtdPrazoConstrucaoMeses")),
        extensao_linha_km=_f_br(r.get("MdaExtensaoLinhaTransmissaoKm")),
        subestacoes_mva=_f_br(r.get("MdaSubEstacoesMVA")),
        investimento_previsto_brl=_f_br(r.get("VlrInvestimentoPrevisto")),
        rap_edital_brl=_f_br(r.get("VlrRAPEditalLeilao")),
        rap_vencedor_brl=_f_br(r.get("VlrRAPVencedorLeilao")),
        desagio_pct=_f_br(r.get("PctDesagio")),
        nome_vencedor=_opt(r.get("NomVencedorLeilao")),
    )


async def _fetch_csv(url: str) -> list[dict[str, str]]:
    raw = await get_bytes(url, cache_ttl=86400)
    # ANEEL's CSVs are Windows-generated and contain CP1252-only bytes
    # (0x96 = en dash, 0x97 = em dash, etc.) that ISO-8859-1 maps to undefined
    # control characters. Decoding as CP1252 keeps them as their printable forms.
    return list(csv.DictReader(io.StringIO(raw.decode("cp1252")), delimiter=";"))


async def get_aneel_leiloes_geracao(
    year: int | None = None,
    fonte: str | None = None,
    uf: str | None = None,
) -> list[LeilaoGeracao]:
    """Generation-auction results (geração de energia elétrica).

    Args:
        year: Filter by ``AnoLeilao`` (auction year, 2005+).
        fonte: Substring match against ``DscFonteEnergia`` (case-sensitive,
            e.g. ``"Eólica"`` / ``"Solar"`` / ``"Biomassa"`` / ``"Hídrica"``).
        uf: Filter by ``SigUFPrincipal`` (state where the project sits).
    """
    rows = await _fetch_csv(LEILOES_GERACAO_URL)
    out = [_parse_geracao(r) for r in rows]
    if year is not None:
        out = [le for le in out if le.ano_leilao == year]
    if fonte:
        out = [le for le in out if le.fonte_energia and fonte in le.fonte_energia]
    if uf:
        target = uf.strip().upper()
        out = [le for le in out if (le.uf or "").upper() == target]
    return out


async def get_aneel_leiloes_transmissao(
    year: int | None = None,
    uf: str | None = None,
) -> list[LeilaoTransmissao]:
    """Transmission-auction results (linhas de transmissão).

    Args:
        year: Filter by ``AnoLeilao`` (1999+).
        uf: Filter by primary UF.
    """
    rows = await _fetch_csv(LEILOES_TRANSMISSAO_URL)
    out = [_parse_transmissao(r) for r in rows]
    if year is not None:
        out = [le for le in out if le.ano_leilao == year]
    if uf:
        target = uf.strip().upper()
        out = [le for le in out if (le.uf or "").upper() == target]
    return out
