"""B3 COTAHIST — official daily-quotes time series (1986+).

The legendary fixed-width format B3 has published since the IBM-mainframe
era. Each annual ZIP holds one ``COTAHIST_A<YYYY>.TXT`` with one record
per stock × per day, 245 bytes per line, ISO-8859-1, integer prices in
cents (divide by 100). Files grow ~85 MB unzipped per recent year, so
we line-stream and let the caller filter by ticker / date.

URL pattern:
- Annual:  ``COTAHIST_A2024.ZIP`` — full year
- Monthly: ``COTAHIST_M042024.ZIP`` — single month (smaller, faster)
- Daily:   ``COTAHIST_D26042024.ZIP`` — single day

Field layout (taken from the official B3 manual ``SeriesHistoricas_Layout.pdf``):

| Pos     | Width | Field   | Notes                                       |
|---------|-------|---------|---------------------------------------------|
| 1-2     | 2     | TIPREG  | 00=header, 01=record, 99=trailer            |
| 3-10    | 8     | DATA    | YYYYMMDD                                    |
| 11-12   | 2     | CODBDI  | market code (02=lote padrão, etc.)          |
| 13-24   | 12    | CODNEG  | ticker, left-aligned, space-padded          |
| 25-27   | 3     | TPMERC  | market type (10=cash, 70/80=options)        |
| 28-39   | 12    | NOMRES  | short name                                  |
| 40-49   | 10    | ESPECI  | class (ON/PN/UNT…)                          |
| 50-52   | 3     | PRAZOT  | option term in days                         |
| 53-56   | 4     | MODREF  | currency reference (R$, US$)                |
| 57-69   | 13    | PREABE  | open  (in cents)                            |
| 70-82   | 13    | PREMAX  | high  (in cents)                            |
| 83-95   | 13    | PREMIN  | low   (in cents)                            |
| 96-108  | 13    | PREMED  | average (in cents)                          |
| 109-121 | 13    | PREULT  | close (in cents)                            |
| 122-134 | 13    | PREOFC  | best bid                                    |
| 135-147 | 13    | PREOFV  | best ask                                    |
| 148-152 | 5     | TOTNEG  | trade count                                 |
| 153-170 | 18    | QUATOT  | total shares traded                         |
| 171-188 | 18    | VOLTOT  | total financial volume (in cents)           |
| 189-201 | 13    | PREEXE  | strike (options only, in cents)             |
| 202     | 1     | INDOPC  | exercise term type                          |
| 203-210 | 8     | DATVEN  | expiration (options) YYYYMMDD               |
| 211-217 | 7     | FATCOT  | quote factor (0000001=R$, 0000010=lote)     |
| 218-230 | 13    | PTOEXE  | exercise points                             |
| 231-242 | 12    | CODISI  | ISIN                                        |
| 243-245 | 3     | DISMES  | distribution number                         |
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Iterator
from typing import Literal

from pydantic import BaseModel

from findata.http_client import get_bytes

COTAHIST_BASE = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist"

_PRICE_DIVISOR = 100  # prices stored in cents
_LINE_WIDTH = 245
_RECORD_TIPREG = "01"


class CotahistTrade(BaseModel):
    """One stock × one trading day from B3's COTAHIST historical series."""

    data: str  # YYYY-MM-DD
    ticker: str  # CODNEG (stripped)
    cod_bdi: str  # market code
    tp_mercado: str  # market type
    nome_resumido: str
    especificacao: str  # class (ON/PN/UNT…)
    moeda: str  # R$ / US$
    preco_abertura: float
    preco_maximo: float
    preco_minimo: float
    preco_medio: float
    preco_ultimo: float
    preco_oferta_compra: float
    preco_oferta_venda: float
    num_negocios: int
    qtd_titulos_negociados: int
    volume_financeiro: float  # R$ (already divided by 100)
    isin: str
    fator_cotacao: int


def _price_raw(slc: str) -> float:
    """Parse a 13-byte cents-encoded price field. Empty / zero → 0.0."""
    s = slc.strip()
    if not s:
        return 0.0
    try:
        return int(s) / _PRICE_DIVISOR
    except ValueError:
        return 0.0


def _price_unit(slc: str, fator: int) -> float:
    """Parse a price and divide by FATCOT for the per-share value.

    B3 quotes prices for a *lot* of FATCOT shares — 1 for almost every
    ticker, but 1000 for some closed-end funds (FNAM11/FNOR11/etc.) and
    occasionally 10 for low-priced legacy issues. Without dividing, the
    value is off by that factor.
    """
    raw = _price_raw(slc)
    return raw / fator if fator > 0 else raw


def _i(slc: str) -> int:
    s = slc.strip()
    if not s:
        return 0
    try:
        return int(s)
    except ValueError:
        return 0


def _format_date(slc: str) -> str:
    """``20240326`` → ``2024-03-26``."""
    s = slc.strip()
    if len(s) != 8:  # noqa: PLR2004 — fixed-width spec
        return s
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}"


def _parse_line(line: str) -> CotahistTrade | None:
    """Slice one fixed-width record. Returns None for header/trailer/non-records."""
    if len(line) < _LINE_WIDTH:
        return None
    if line[0:2] != _RECORD_TIPREG:
        return None
    fator = _i(line[210:217]) or 1
    return CotahistTrade(
        data=_format_date(line[2:10]),
        ticker=line[12:24].strip(),
        cod_bdi=line[10:12].strip(),
        tp_mercado=line[24:27].strip(),
        nome_resumido=line[27:39].strip(),
        especificacao=line[39:49].strip(),
        moeda=line[52:56].strip(),
        # Per-share prices already adjusted by FATCOT — see _price_unit docstring.
        preco_abertura=_price_unit(line[56:69], fator),
        preco_maximo=_price_unit(line[69:82], fator),
        preco_minimo=_price_unit(line[82:95], fator),
        preco_medio=_price_unit(line[95:108], fator),
        preco_ultimo=_price_unit(line[108:121], fator),
        preco_oferta_compra=_price_unit(line[121:134], fator),
        preco_oferta_venda=_price_unit(line[134:147], fator),
        num_negocios=_i(line[147:152]),
        qtd_titulos_negociados=_i(line[152:170]),
        # VOLTOT is total cash volume — not per-lot, so no FATCOT division.
        volume_financeiro=_price_raw(line[170:188]),
        isin=line[230:242].strip(),
        fator_cotacao=fator,
    )


def _iter_lines(zf: zipfile.ZipFile) -> Iterator[str]:
    for name in zf.namelist():
        if not name.upper().endswith(".TXT"):
            continue
        with zf.open(name) as f:
            for raw in io.TextIOWrapper(f, encoding="iso-8859-1", newline=""):
                yield raw.rstrip("\r\n")


_Granularity = Literal["A", "M", "D"]


def _build_url(granularity: _Granularity, stamp: str) -> str:
    """Build the canonical COTAHIST URL for a given granularity + stamp.

    - ``"A"``: stamp = ``"YYYY"``       → ``COTAHIST_A2024.ZIP``
    - ``"M"``: stamp = ``"MMYYYY"``     → ``COTAHIST_M032024.ZIP``
    - ``"D"``: stamp = ``"DDMMYYYY"``   → ``COTAHIST_D26032024.ZIP``
    """
    return f"{COTAHIST_BASE}/COTAHIST_{granularity}{stamp}.ZIP"


async def get_cotahist_year(
    year: int,
    ticker: str | None = None,
    market_codes: list[str] | None = None,
) -> list[CotahistTrade]:
    """Read every trading-day record for a year.

    Args:
        year: 1986+ (B3 publishes back to 1986-01-02).
        ticker: CODNEG filter (case-insensitive exact match). One of
            ``ticker`` or ``market_codes`` is **required** for annual
            calls — the unfiltered annual file expands to ~2.6M records
            (75 MB raw zip, well over a gigabyte once parsed into Pydantic
            models). For a full unfiltered scan, iterate per month using
            :func:`get_cotahist_month`.
        market_codes: Whitelist of CODBDI values (e.g. ``["02"]`` lote
            padrão, ``["96"]`` fracionário, ``["12"]`` BTC,
            ``["78","82"]`` options).

    Raises:
        ValueError: If both ``ticker`` and ``market_codes`` are ``None``.
    """
    if not ticker and not market_codes:
        raise ValueError(
            "get_cotahist_year requires ticker or market_codes "
            "(unfiltered scan would materialise ~2.6M records). "
            "Iterate per month with get_cotahist_month for a full scan."
        )
    return await _fetch(_build_url("A", str(year)), ticker, market_codes)


async def get_cotahist_month(
    year: int,
    month: int,
    ticker: str | None = None,
    market_codes: list[str] | None = None,
) -> list[CotahistTrade]:
    """Read one month of COTAHIST records (smaller, faster than annual)."""
    return await _fetch(_build_url("M", f"{month:02d}{year}"), ticker, market_codes)


async def get_cotahist_day(
    year: int,
    month: int,
    day: int,
    ticker: str | None = None,
    market_codes: list[str] | None = None,
) -> list[CotahistTrade]:
    """Read a single trading day of COTAHIST records."""
    return await _fetch(
        _build_url("D", f"{day:02d}{month:02d}{year}"),
        ticker,
        market_codes,
    )


async def _fetch(
    url: str,
    ticker: str | None,
    market_codes: list[str] | None,
) -> list[CotahistTrade]:
    raw = await get_bytes(url, cache_ttl=86400)
    target = ticker.strip().upper() if ticker else None
    code_set = {c.strip() for c in market_codes} if market_codes else None
    out: list[CotahistTrade] = []
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        for line in _iter_lines(zf):
            # Cheap pre-filter: skip non-records and non-matching tickers
            # before paying the BaseModel construction cost.
            if line[:2] != _RECORD_TIPREG:
                continue
            if target and line[12:24].strip().upper() != target:
                continue
            if code_set and line[10:12].strip() not in code_set:
                continue
            row = _parse_line(line)
            if row is not None:
                out.append(row)
    return out
