"""CVM FCA — Formulário Cadastral de Companhia Aberta.

The FCA annual ZIP carries the company's structured registration record:
who they are, where they're located, how they trade, who audits them,
and which securities they've issued. Eleven CSVs in one ZIP, each a
different facet:

| Suffix                          | Content                              |
|---------------------------------|--------------------------------------|
| `fca_cia_aberta_<year>`         | Index — one row per (cnpj, versão)   |
| `..._geral_<year>`              | Setor, controle acionário, website,  |
|                                 | fiscal year end, situação registro   |
| `..._valor_mobiliario_<year>`   | Ticker → CNPJ map (class + segmento) |
| `..._dri_<year>`                | Diretor de Relações com Investidores |
| `..._auditor_<year>`            | Independent auditor                  |
| `..._endereco_<year>`           | Mailing addresses                    |
| `..._escriturador_<year>`       | Share-book agent                     |
| `..._canal_divulgacao_<year>`   | Disclosure channels                  |
| `..._departamento_acionistas_*` | Shareholder-services dept            |
| `..._pais_estrangeiro_<year>`   | Foreign listings                     |

We ship the three highest-density facets up-front: ``geral``,
``valor_mobiliario`` (the ticker map), and ``dri``. Other facets can be
added as needed — the parser is generic and the URL is the same.

Source: ``https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FCA/DADOS/``
"""

from __future__ import annotations

from pydantic import BaseModel

from findata.sources.cvm._directory import CVM_BASE
from findata.sources.cvm.parser import fetch_csv_from_zip

FCA_URL = f"{CVM_BASE}/CIA_ABERTA/DOC/FCA/DADOS/fca_cia_aberta_{{year}}.zip"


class FCAGeneral(BaseModel):
    """Top-level company facts (one row per (cnpj, versão))."""

    cnpj: str
    nome_empresarial: str
    cod_cvm: str
    dt_referencia: str
    versao: str
    setor_atividade: str | None = None
    descricao_atividade: str | None = None
    pais_origem: str | None = None
    situacao_emissor: str | None = None
    situacao_registro_cvm: str | None = None
    categoria_registro_cvm: str | None = None
    especie_controle_acionario: str | None = None
    dia_encerramento_exercicio: int | None = None
    mes_encerramento_exercicio: int | None = None
    pagina_web: str | None = None


class FCASecurity(BaseModel):
    """Issued security — ticker, class, market, segment, listing dates."""

    cnpj: str
    nome_empresarial: str
    dt_referencia: str
    versao: str
    valor_mobiliario: str  # "Ações Ordinárias" / "BDR" / "Debênture" etc.
    classe_preferencial: str | None = None
    sigla_classe_preferencial: str | None = None
    codigo_negociacao: str | None = None  # the actual ticker (PETR4, VALE3…)
    mercado: str | None = None  # "Bolsa" / "Balcão Organizado"
    entidade_administradora: str | None = None  # usually "B3"
    segmento: str | None = None  # "Novo Mercado" / "N1" / "N2" / etc.
    dt_inicio_negociacao: str | None = None
    dt_fim_negociacao: str | None = None
    dt_inicio_listagem: str | None = None
    dt_fim_listagem: str | None = None


class FCAInvestorRelations(BaseModel):
    """Diretor de Relações com Investidores (DRI) contact card."""

    cnpj: str
    nome_empresarial: str
    dt_referencia: str
    versao: str
    responsavel: str
    cpf: str | None = None
    email: str | None = None
    telefone: str | None = None
    cidade: str | None = None
    uf: str | None = None
    dt_inicio_atuacao: str | None = None
    dt_fim_atuacao: str | None = None


def _i(v: str | None) -> int | None:
    if v is None or not v.strip():
        return None
    try:
        return int(v.strip())
    except ValueError:
        return None


def _opt(v: str | None) -> str | None:
    """Strip + drop empty. Treats NBSP (\\xa0) as whitespace, matching the
    feed's actual usage in free-text fields."""
    if v is None:
        return None
    s = v.strip()
    return s if s else None


def _filter_cnpj(rows: list[dict[str, str]], cnpj: str | None) -> list[dict[str, str]]:
    if not cnpj:
        return rows
    target = cnpj.strip()
    return [
        r for r in rows if (r.get("CNPJ_Companhia") or r.get("CNPJ_CIA") or "").strip() == target
    ]


async def get_fca_geral(year: int, cnpj: str | None = None) -> list[FCAGeneral]:
    """Top-level company facts: setor, situação, exercício social, website."""
    url = FCA_URL.format(year=year)
    rows = await fetch_csv_from_zip(url, f"fca_cia_aberta_geral_{year}")
    rows = _filter_cnpj(rows, cnpj)
    return [
        FCAGeneral(
            cnpj=(r.get("CNPJ_Companhia") or "").strip(),
            nome_empresarial=(r.get("Nome_Empresarial") or "").strip(),
            cod_cvm=(r.get("Codigo_CVM") or "").strip(),
            dt_referencia=(r.get("Data_Referencia") or "").strip(),
            versao=(r.get("Versao") or "").strip(),
            setor_atividade=_opt(r.get("Setor_Atividade")),
            descricao_atividade=_opt(r.get("Descricao_Atividade")),
            pais_origem=_opt(r.get("Pais_Origem")),
            situacao_emissor=_opt(r.get("Situacao_Emissor")),
            situacao_registro_cvm=_opt(r.get("Situacao_Registro_CVM")),
            categoria_registro_cvm=_opt(r.get("Categoria_Registro_CVM")),
            especie_controle_acionario=_opt(r.get("Especie_Controle_Acionario")),
            dia_encerramento_exercicio=_i(r.get("Dia_Encerramento_Exercicio_Social")),
            mes_encerramento_exercicio=_i(r.get("Mes_Encerramento_Exercicio_Social")),
            pagina_web=_opt(r.get("Pagina_Web")),
        )
        for r in rows
    ]


async def get_fca_valores_mobiliarios(
    year: int,
    cnpj: str | None = None,
    ticker: str | None = None,
) -> list[FCASecurity]:
    """Issued securities — useful as a ticker→CNPJ resolver.

    Args:
        year: FCA reference year.
        cnpj: Optional issuer filter.
        ticker: Optional B3 ticker filter (case-insensitive exact match
            against ``Codigo_Negociacao``).
    """
    url = FCA_URL.format(year=year)
    rows = await fetch_csv_from_zip(url, f"fca_cia_aberta_valor_mobiliario_{year}")
    rows = _filter_cnpj(rows, cnpj)
    out = [
        FCASecurity(
            cnpj=(r.get("CNPJ_Companhia") or "").strip(),
            nome_empresarial=(r.get("Nome_Empresarial") or "").strip(),
            dt_referencia=(r.get("Data_Referencia") or "").strip(),
            versao=(r.get("Versao") or "").strip(),
            valor_mobiliario=(r.get("Valor_Mobiliario") or "").strip(),
            classe_preferencial=_opt(r.get("Classe_Acao_Preferencial")),
            sigla_classe_preferencial=_opt(r.get("Sigla_Classe_Acao_Preferencial")),
            codigo_negociacao=_opt(r.get("Codigo_Negociacao")),
            mercado=_opt(r.get("Mercado")),
            entidade_administradora=_opt(r.get("Entidade_Administradora")),
            segmento=_opt(r.get("Segmento")),
            dt_inicio_negociacao=_opt(r.get("Data_Inicio_Negociacao")),
            dt_fim_negociacao=_opt(r.get("Data_Fim_Negociacao")),
            dt_inicio_listagem=_opt(r.get("Data_Inicio_Listagem")),
            dt_fim_listagem=_opt(r.get("Data_Fim_Listagem")),
        )
        for r in rows
    ]
    if ticker:
        target = ticker.strip().upper()
        out = [s for s in out if (s.codigo_negociacao or "").upper() == target]
    return out


async def get_fca_dri(year: int, cnpj: str | None = None) -> list[FCAInvestorRelations]:
    """Diretor de Relações com Investidores (DRI) contact info."""
    url = FCA_URL.format(year=year)
    rows = await fetch_csv_from_zip(url, f"fca_cia_aberta_dri_{year}")
    rows = _filter_cnpj(rows, cnpj)
    return [
        FCAInvestorRelations(
            cnpj=(r.get("CNPJ_Companhia") or "").strip(),
            nome_empresarial=(r.get("Nome_Empresarial") or "").strip(),
            dt_referencia=(r.get("Data_Referencia") or "").strip(),
            versao=(r.get("Versao") or "").strip(),
            responsavel=(r.get("Responsavel") or "").strip(),
            cpf=_opt(r.get("CPF_Responsavel")),
            email=_opt(r.get("Email")),
            telefone=_opt(r.get("Telefone")),
            cidade=_opt(r.get("Cidade")),
            uf=_opt(r.get("Sigla_UF")),
            dt_inicio_atuacao=_opt(r.get("Data_Inicio_Atuacao")),
            dt_fim_atuacao=_opt(r.get("Data_Fim_Atuacao")),
        )
        for r in rows
    ]
