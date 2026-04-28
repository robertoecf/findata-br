"""CVM FII — Fundos de Investimento Imobiliário (informe mensal).

The FII annual ZIP holds three CSVs covering the same funds at three
different facets:

| Suffix              | Content                                              |
|---------------------|------------------------------------------------------|
| ``..._geral_``      | Cadastral (segmento, mandato, gestor, administrador) |
| ``..._complemento_``| Cotistas breakdown + PL + taxa administração        |
| ``..._ativo_passivo`` | Balance sheet (imóveis, debêntures, ações)         |

We ship the two most useful surfaces — ``geral`` (who the fund is) and
``complemento`` (how big and how many cotistas) — and leave
``ativo_passivo`` for later when there's a real consumer.

Source: ``https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/``
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from findata.sources.cvm._directory import CVM_BASE
from findata.sources.cvm.parser import fetch_csv_from_zip

FII_URL = f"{CVM_BASE}/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_{{year}}.zip"


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


def _row_cnpj(r: dict[str, str]) -> str:
    """Schema-tolerant CNPJ lookup. CVM renamed ``CNPJ_Fundo`` →
    ``CNPJ_Fundo_Classe`` somewhere around 2021; pre-2021 zips still use
    the old form. Same story for ``Nome_Fundo``.
    """
    return (r.get("CNPJ_Fundo_Classe") or r.get("CNPJ_Fundo") or "").strip()


def _row_nome(r: dict[str, str]) -> str:
    return (r.get("Nome_Fundo_Classe") or r.get("Nome_Fundo") or "").strip()


def _filter_period(
    rows: list[dict[str, str]],
    cnpj: str | None,
    month: int | None,
) -> list[dict[str, str]]:
    out = rows
    if cnpj:
        target = cnpj.strip()
        out = [r for r in out if _row_cnpj(r) == target]
    if month is not None:
        prefix = f"-{month:02d}-"
        out = [r for r in out if prefix in (r.get("Data_Referencia") or "")]
    return out


class FIIGeneral(BaseModel):
    """Cadastral facet — what the fund is."""

    cnpj: str
    nome_fundo: str
    dt_referencia: str
    versao: str
    tipo_fundo_classe: str | None = None
    publico_alvo: str | None = None
    isin: str | None = None
    quantidade_cotas_emitidas: int | None = None
    fundo_exclusivo: str | None = None
    mandato: str | None = None  # Renda / Desenvolvimento / Híbrido / etc.
    segmento_atuacao: str | None = None  # Lajes / Logística / Shoppings / Híbrido…
    tipo_gestao: str | None = None  # Ativa / Passiva
    prazo_duracao: str | None = None  # Determinado / Indeterminado
    dt_funcionamento: str | None = None
    encerramento_exercicio_social: str | None = None
    nome_administrador: str | None = None
    cnpj_administrador: str | None = None


class FIIComplement(BaseModel):
    """Complement facet — investor breakdown + PL + admin fee."""

    cnpj: str
    dt_referencia: str
    versao: str
    valor_ativo: float | None = None
    patrimonio_liquido: float | None = None
    cotas_emitidas: float | None = None
    valor_patrimonial_cotas: float | None = None
    pct_despesas_taxa_administracao: float | None = None
    total_cotistas: int | None = None
    cotistas_pf: int | None = None
    cotistas_pj_nao_financ: int | None = None
    cotistas_banco: int | None = None
    cotistas_corretora_distrib: int | None = None
    cotistas_pj_financ: int | None = None
    cotistas_invest_nao_residentes: int | None = None
    cotistas_eapc: int | None = None  # entidade aberta de previdência complementar
    cotistas_efpc: int | None = None  # entidade fechada de previdência complementar
    cotistas_rpps: int | None = None  # regime próprio dos servidores públicos
    cotistas_seguradora_resseguradora: int | None = None
    cotistas_capitalizacao_arrendamento: int | None = None
    cotistas_fii: int | None = None
    cotistas_outros_fundos: int | None = None
    cotistas_distribuidores_fundo: int | None = None


def _parse_general(r: dict[str, str]) -> FIIGeneral:
    return FIIGeneral(
        cnpj=_row_cnpj(r),
        nome_fundo=_row_nome(r),
        dt_referencia=(r.get("Data_Referencia") or "").strip(),
        versao=(r.get("Versao") or "").strip(),
        tipo_fundo_classe=_opt(r.get("Tipo_Fundo_Classe")),
        publico_alvo=_opt(r.get("Publico_Alvo")),
        isin=_opt(r.get("Codigo_ISIN")),
        quantidade_cotas_emitidas=_i(r.get("Quantidade_Cotas_Emitidas")),
        fundo_exclusivo=_opt(r.get("Fundo_Exclusivo")),
        mandato=_opt(r.get("Mandato")),
        segmento_atuacao=_opt(r.get("Segmento_Atuacao")),
        tipo_gestao=_opt(r.get("Tipo_Gestao")),
        prazo_duracao=_opt(r.get("Prazo_Duracao")),
        dt_funcionamento=_opt(r.get("Data_Funcionamento")),
        encerramento_exercicio_social=_opt(r.get("Encerramento_Exercicio_Social")),
        nome_administrador=_opt(r.get("Nome_Administrador")),
        cnpj_administrador=_opt(r.get("CNPJ_Administrador")),
    )


def _parse_complement(r: dict[str, str]) -> FIIComplement:
    return FIIComplement(
        cnpj=_row_cnpj(r),
        dt_referencia=(r.get("Data_Referencia") or "").strip(),
        versao=(r.get("Versao") or "").strip(),
        valor_ativo=_f(r.get("Valor_Ativo")),
        patrimonio_liquido=_f(r.get("Patrimonio_Liquido")),
        cotas_emitidas=_f(r.get("Cotas_Emitidas")),
        valor_patrimonial_cotas=_f(r.get("Valor_Patrimonial_Cotas")),
        pct_despesas_taxa_administracao=_f(r.get("Percentual_Despesas_Taxa_Administracao")),
        total_cotistas=_i(r.get("Total_Numero_Cotistas")),
        cotistas_pf=_i(r.get("Numero_Cotistas_Pessoa_Fisica")),
        cotistas_pj_nao_financ=_i(r.get("Numero_Cotistas_Pessoa_Juridica_Nao_Financeira")),
        cotistas_banco=_i(r.get("Numero_Cotistas_Banco_Comercial")),
        cotistas_corretora_distrib=_i(r.get("Numero_Cotistas_Corretora_Distribuidora")),
        cotistas_pj_financ=_i(r.get("Numero_Cotistas_Outras_Pessoas_Juridicas_Financeira")),
        cotistas_invest_nao_residentes=_i(r.get("Numero_Cotistas_Investidores_Nao_Residentes")),
        cotistas_eapc=_i(r.get("Numero_Cotistas_Entidade_Aberta_Previdencia_Complementar")),
        cotistas_efpc=_i(r.get("Numero_Cotistas_Entidade_Fechada_Previdência_Complementar")),
        cotistas_rpps=_i(r.get("Numero_Cotistas_Regime_Proprio_Previdencia_Servidores_Publicos")),
        cotistas_seguradora_resseguradora=_i(
            r.get("Numero_Cotistas_Sociedade_Seguradora_Resseguradora")
        ),
        cotistas_capitalizacao_arrendamento=_i(
            r.get("Numero_Cotistas_Sociedade_Capitalizacao_Arrendamento_Mercantil")
        ),
        cotistas_fii=_i(r.get("Numero_Cotistas_FII")),
        cotistas_outros_fundos=_i(r.get("Numero_Cotistas_Outros_Fundos")),
        cotistas_distribuidores_fundo=_i(r.get("Numero_Cotistas_Distribuidores_Fundo")),
    )


async def get_fii_geral(
    year: int,
    cnpj: str | None = None,
    month: int | None = None,
) -> list[FIIGeneral]:
    """FII cadastral facet — segmento, mandato, gestão, administrador."""
    rows = await fetch_csv_from_zip(FII_URL.format(year=year), f"inf_mensal_fii_geral_{year}")
    rows = _filter_period(rows, cnpj, month)
    return [_parse_general(r) for r in rows]


async def get_fii_complemento(
    year: int,
    cnpj: str | None = None,
    month: int | None = None,
) -> list[FIIComplement]:
    """FII complement facet — cotistas breakdown + PL + taxa administração."""
    rows = await fetch_csv_from_zip(
        FII_URL.format(year=year),
        f"inf_mensal_fii_complemento_{year}",
    )
    rows = _filter_period(rows, cnpj, month)
    return [_parse_complement(r) for r in rows]
