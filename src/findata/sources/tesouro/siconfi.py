"""Tesouro Nacional SICONFI — public-finance accounting datalake.

SICONFI (Sistema de Informações Contábeis e Fiscais do Setor Público
Brasileiro) is the Tesouro's API for the bimonthly RREO (Relatório
Resumido de Execução Orçamentária) and quadrimestral RGF (Relatório
de Gestão Fiscal) reports filed by every federal, state, and municipal
entity in Brazil — required by the Lei de Responsabilidade Fiscal.

The API is REST + JSON, public, no auth. Each row is one (entity ×
period × annex × column × account) tuple — a "long-form" representation
of accounting tables. Filters narrow scope before parsing.

Endpoint base: ``https://apidatalake.tesouro.gov.br/ords/siconfi/tt/``

| Path                | Content                                              |
|---------------------|------------------------------------------------------|
| ``/rreo``           | RREO bimestral (executive budget execution)          |
| ``/rgf``            | RGF quadrimestral (LRF fiscal-management report)     |
| ``/entes``          | Full entity list (5570+ municipalities + 27 UFs + União) |
| ``/extrato_entregas`` | Filing-status extract per entity / period          |

Pagination: 5000 rows per page, ``hasMore`` flag, ``offset`` param.
We auto-paginate up to a safety cap (1M rows = 200 pages).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from findata.http_client import get_json

SICONFI_BASE = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"

_PAGE_LIMIT = 5000
_MAX_PAGES = 200  # 1M-row cap — well above any single (ente, period, annex)


class SiconfiEntity(BaseModel):
    """One federation entity (União, state, municipality, DF)."""

    cod_ibge: int  # IBGE code (1=União, 11..53=UFs, 6-digit=municipalities)
    uf: str  # state UF (e.g. "SP", "BR" for União)
    instituicao: str  # display name
    esfera: str  # U=União, E=Estado, M=Município, D=DF
    populacao: int | None = None  # only municipalities + states


class SiconfiAccount(BaseModel):
    """One row from a RREO / RGF / DCA report.

    The data model is intentionally long-form (one value per row) so
    callers can pivot however they need. ``coluna`` carries the column
    label inside the original table (e.g. ``"PREVISÃO INICIAL"``,
    ``"% (b/a)"``); ``cod_conta`` + ``conta`` carry the row key.
    """

    exercicio: int  # year
    demonstrativo: str  # "RREO" / "RREO Simplificado" / "RGF" / etc.
    periodo: int  # bimestre (1-6 for RREO) or quadrimestre (1-3 for RGF)
    periodicidade: str  # "B" (bimestral) / "Q" (quadrimestral) / "A" (anual)
    instituicao: str
    cod_ibge: int
    uf: str
    populacao: int | None = None
    anexo: str  # e.g. "RREO-Anexo 01"
    esfera: str
    rotulo: str | None = None  # e.g. "Padrão"
    coluna: str  # column label inside the table
    cod_conta: str | None = None  # account code
    conta: str  # account name
    valor: float | None = None


def _row_to_account(r: dict[str, Any]) -> SiconfiAccount:
    return SiconfiAccount(
        exercicio=int(r.get("exercicio") or 0),
        demonstrativo=str(r.get("demonstrativo") or ""),
        periodo=int(r.get("periodo") or 0),
        periodicidade=str(r.get("periodicidade") or ""),
        instituicao=str(r.get("instituicao") or ""),
        cod_ibge=int(r.get("cod_ibge") or 0),
        uf=str(r.get("uf") or ""),
        populacao=int(r["populacao"]) if r.get("populacao") is not None else None,
        anexo=str(r.get("anexo") or ""),
        esfera=str(r.get("esfera") or ""),
        rotulo=r.get("rotulo"),
        coluna=str(r.get("coluna") or ""),
        cod_conta=r.get("cod_conta"),
        conta=str(r.get("conta") or ""),
        valor=float(r["valor"]) if r.get("valor") is not None else None,
    )


async def _paginate(url: str, params: dict[str, str | int]) -> list[dict[str, Any]]:
    """Fetch all pages of a SICONFI list endpoint.

    SICONFI returns ``hasMore`` true while more pages exist; we walk
    ``offset`` until ``hasMore`` is false or the safety cap kicks in.
    """
    out: list[dict[str, Any]] = []
    for page in range(_MAX_PAGES):
        offset = page * _PAGE_LIMIT
        page_params = dict(params)
        page_params["offset"] = offset
        data = await get_json(url, params=page_params, cache_ttl=86400)
        items = data.get("items") or []
        out.extend(items)
        if not data.get("hasMore"):
            break
    return out


_DemonstrativoRREO = Literal["RREO", "RREO Simplificado"]
_DemonstrativoRGF = Literal["RGF", "RGF Simplificado"]
_PoderRGF = Literal["E", "L", "J", "M", "D"]
# E=Executivo, L=Legislativo, J=Judiciário, M=Ministério Público, D=Defensoria

_VALID_RREO_DEMOS = {"RREO", "RREO Simplificado"}
_VALID_RGF_DEMOS = {"RGF", "RGF Simplificado"}
_VALID_PODERES = {"E", "L", "J", "M", "D"}

# IBGE → UF map (states only). Derives UF for municipalities by taking the
# first two digits of their 7-digit cod_ibge. The API returns ``"BR"`` for
# states and ``None`` for União, so we always derive locally.
_IBGE_STATE_UF: dict[int, str] = {
    11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
    21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL",
    28: "SE", 29: "BA",
    31: "MG", 32: "ES", 33: "RJ", 35: "SP",
    41: "PR", 42: "SC", 43: "RS",
    50: "MS", 51: "MT", 52: "GO", 53: "DF",
}  # fmt: skip


def _derive_uf(cod_ibge: int, esfera: str) -> str:
    """Resolve the entity's UF from cod_ibge.

    SICONFI's raw ``uf`` field is unreliable: it returns ``"BR"`` for the
    27 states and ``None`` for União. We derive locally instead:

    - ``cod_ibge == 1``: União → ``"BR"``
    - 2-digit code (11-53): state → look up in :data:`_IBGE_STATE_UF`
    - 7-digit code: municipality → take first two digits, look up
    """
    if cod_ibge == 1 or esfera == "U":
        return "BR"
    state_code = cod_ibge if cod_ibge < 100 else cod_ibge // 100_000  # noqa: PLR2004
    return _IBGE_STATE_UF.get(state_code, "")


async def get_rreo(
    year: int,
    bimestre: int,
    cod_ibge: int,
    demonstrativo: _DemonstrativoRREO = "RREO",
    anexo: str | None = None,
) -> list[SiconfiAccount]:
    """RREO — Relatório Resumido de Execução Orçamentária.

    Args:
        year: ``an_exercicio``. RREO data starts at 2013 for most entities.
        bimestre: 1-6 (RREO is published every two months).
        cod_ibge: IBGE code of the reporting entity. Use
            :func:`get_entes` to discover. ``1`` = União.
        demonstrativo: ``"RREO"`` (full, default) or ``"RREO Simplificado"``
            (subset published by small municipalities).
        anexo: Optional annex filter (e.g. ``"RREO-Anexo 01"`` =
            balanço orçamentário, ``"RREO-Anexo 06"`` = resultado primário).

    Raises:
        ValueError: ``demonstrativo`` outside the documented values.
    """
    if demonstrativo not in _VALID_RREO_DEMOS:
        raise ValueError(
            f"demonstrativo must be one of {sorted(_VALID_RREO_DEMOS)}, got {demonstrativo!r}"
        )
    params: dict[str, str | int] = {
        "an_exercicio": year,
        "nr_periodo": bimestre,
        "co_tipo_demonstrativo": demonstrativo,
        "id_ente": cod_ibge,
    }
    if anexo:
        params["no_anexo"] = anexo  # SICONFI param is no_anexo, not co_anexo
    rows = await _paginate(f"{SICONFI_BASE}/rreo", params)
    return [_row_to_account(r) for r in rows]


async def get_rgf(
    year: int,
    quadrimestre: int,
    cod_ibge: int,
    poder: _PoderRGF = "E",
    demonstrativo: _DemonstrativoRGF = "RGF",
    anexo: str | None = None,
) -> list[SiconfiAccount]:
    """RGF — Relatório de Gestão Fiscal.

    Args:
        year: ``an_exercicio``.
        quadrimestre: 1-3 (every four months) — RGF for very small
            entities is published semestralmente, then ``2`` and ``3``
            converge.
        cod_ibge: IBGE code (use :func:`get_entes`).
        poder: ``"E"`` Executivo (default), ``"L"`` Legislativo,
            ``"J"`` Judiciário, ``"M"`` Ministério Público,
            ``"D"`` Defensoria Pública.
        demonstrativo: ``"RGF"`` (full) or ``"RGF Simplificado"``.
        anexo: Optional annex filter (e.g. ``"RGF-Anexo 01"`` =
            despesa com pessoal, ``"RGF-Anexo 02"`` = dívida consolidada).

    Raises:
        ValueError: ``demonstrativo`` or ``poder`` outside documented values.
    """
    if demonstrativo not in _VALID_RGF_DEMOS:
        raise ValueError(
            f"demonstrativo must be one of {sorted(_VALID_RGF_DEMOS)}, got {demonstrativo!r}"
        )
    if poder not in _VALID_PODERES:
        raise ValueError(f"poder must be one of {sorted(_VALID_PODERES)}, got {poder!r}")
    params: dict[str, str | int] = {
        "an_exercicio": year,
        "nr_periodo": quadrimestre,
        "co_tipo_demonstrativo": demonstrativo,
        "co_poder": poder,
        "id_ente": cod_ibge,
    }
    if anexo:
        params["no_anexo"] = anexo  # SICONFI param is no_anexo, not co_anexo
    rows = await _paginate(f"{SICONFI_BASE}/rgf", params)
    return [_row_to_account(r) for r in rows]


async def get_entes() -> list[SiconfiEntity]:
    """List every federation entity registered at SICONFI.

    Returns União (cod_ibge=1) + 27 UFs + DF + ~5570 municipalities,
    each with their IBGE code, name, esfera, and population.
    Cached for 24h.
    """
    rows = await _paginate(f"{SICONFI_BASE}/entes", {})
    out: list[SiconfiEntity] = []
    for r in rows:
        cod = r.get("cod_ibge")
        if cod is None:
            continue
        cod_int = int(cod)
        esfera = str(r.get("esfera") or "")
        # Trust the API's uf only when it's a real 2-char state code that
        # isn't its sentinel "BR" for states. For União and states, derive.
        raw_uf = (r.get("uf") or "").strip()
        uf = raw_uf if raw_uf and raw_uf != "BR" and esfera != "E" else _derive_uf(cod_int, esfera)
        out.append(
            SiconfiEntity(
                cod_ibge=cod_int,
                uf=uf,
                instituicao=str(r.get("instituicao") or r.get("ente") or ""),
                esfera=esfera,
                populacao=int(r["populacao"]) if r.get("populacao") is not None else None,
            )
        )
    return out
