"""ANBIMA indices and curve endpoints — IMA family, IHFA, IDA, ETTJ."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from findata.sources.anbima.client import get_default_client


class IMAFamily(StrEnum):
    IMA_GERAL = "IMA-Geral"
    IMA_B = "IMA-B"
    IMA_B_5 = "IMA-B 5"
    IMA_B_5_PLUS = "IMA-B 5+"
    IMA_S = "IMA-S"
    IRF_M = "IRF-M"
    IRF_M_1 = "IRF-M 1"
    IRF_M_1_PLUS = "IRF-M 1+"


class IMADataPoint(BaseModel):
    indice: str
    data_referencia: str
    valor_indice: float | None = None
    variacao_pct: float | None = None
    duration: float | None = None


class IHFADataPoint(BaseModel):
    data_referencia: str
    valor_indice: float | None = None
    variacao_dia_pct: float | None = None
    variacao_mes_pct: float | None = None
    variacao_ano_pct: float | None = None


class IDADataPoint(BaseModel):
    indice: str
    data_referencia: str
    valor_indice: float | None = None
    variacao_dia_pct: float | None = None


class ETTJDataPoint(BaseModel):
    data_referencia: str
    vertice: int  # business days to maturity
    taxa_pre: float | None = None
    taxa_ipca: float | None = None
    taxa_real: float | None = None


# ── Public functions ──────────────────────────────────────────────


def _fmt_date(d: date | None) -> str:
    return (d or date.today()).strftime("%Y-%m-%d")


async def get_ima(
    family: IMAFamily | str = IMAFamily.IMA_B,
    data_referencia: date | None = None,
) -> list[IMADataPoint]:
    """Fetch IMA family index for a reference date."""
    client = get_default_client()
    raw = await client.get_json(
        "/feed/precos-indices/v1/indices/ima",
        params={"data": _fmt_date(data_referencia)},
    )
    rows = _value_array(raw)
    return [_parse_ima(r) for r in rows if not family or r.get("indice") == str(family)]


async def get_ihfa(data_referencia: date | None = None) -> list[IHFADataPoint]:
    """Fetch IHFA (hedge fund index) for a reference date."""
    client = get_default_client()
    raw = await client.get_json(
        "/feed/precos-indices/v1/indices-mais/ihfa",
        params={"data": _fmt_date(data_referencia)},
    )
    return [_parse_ihfa(r) for r in _value_array(raw)]


async def get_ida(data_referencia: date | None = None) -> list[IDADataPoint]:
    """Fetch IDA (debenture index) for a reference date."""
    client = get_default_client()
    raw = await client.get_json(
        "/feed/precos-indices/v1/indices-mais/ida",
        params={"data": _fmt_date(data_referencia)},
    )
    return [_parse_ida(r) for r in _value_array(raw)]


async def get_ettj(data_referencia: date | None = None) -> list[ETTJDataPoint]:
    """Fetch the zero-coupon yield curve (estrutura a termo) for a date."""
    client = get_default_client()
    raw = await client.get_json(
        "/feed/precos-indices/v1/titulos-publicos/curva-zero",
        params={"data": _fmt_date(data_referencia)},
    )
    return [_parse_ettj(r) for r in _value_array(raw)]


# ── Parsers ───────────────────────────────────────────────────────


def _value_array(raw: Any) -> list[dict[str, Any]]:
    """ANBIMA wraps lists in either a top-level array or `{"data": [...]}`."""
    if isinstance(raw, list):
        return list(raw)
    if isinstance(raw, dict):
        for k in ("data", "value", "results", "indices"):
            if k in raw and isinstance(raw[k], list):
                return list(raw[k])
    return []


def _parse_ima(r: dict[str, Any]) -> IMADataPoint:
    return IMADataPoint(
        indice=str(r.get("indice", "")),
        data_referencia=str(r.get("dataReferencia") or r.get("data") or ""),
        valor_indice=_f(r.get("valorIndice") or r.get("valor")),
        variacao_pct=_f(r.get("variacaoPercentual") or r.get("variacao_pct")),
        duration=_f(r.get("duration")),
    )


def _parse_ihfa(r: dict[str, Any]) -> IHFADataPoint:
    return IHFADataPoint(
        data_referencia=str(r.get("dataReferencia") or r.get("data") or ""),
        valor_indice=_f(r.get("valorIndice") or r.get("valor")),
        variacao_dia_pct=_f(r.get("variacaoDia") or r.get("variacao_dia_pct")),
        variacao_mes_pct=_f(r.get("variacaoMes") or r.get("variacao_mes_pct")),
        variacao_ano_pct=_f(r.get("variacaoAno") or r.get("variacao_ano_pct")),
    )


def _parse_ida(r: dict[str, Any]) -> IDADataPoint:
    return IDADataPoint(
        indice=str(r.get("indice", "")),
        data_referencia=str(r.get("dataReferencia") or r.get("data") or ""),
        valor_indice=_f(r.get("valorIndice") or r.get("valor")),
        variacao_dia_pct=_f(r.get("variacaoDia") or r.get("variacao_dia_pct")),
    )


def _parse_ettj(r: dict[str, Any]) -> ETTJDataPoint:
    vertice = r.get("vertice") or r.get("dias") or 0
    return ETTJDataPoint(
        data_referencia=str(r.get("dataReferencia") or r.get("data") or ""),
        vertice=int(vertice) if vertice is not None else 0,
        taxa_pre=_f(r.get("taxaPre") or r.get("taxa_pre")),
        taxa_ipca=_f(r.get("taxaIPCA") or r.get("taxa_ipca")),
        taxa_real=_f(r.get("taxaReal") or r.get("taxa_real")),
    )


def _f(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
