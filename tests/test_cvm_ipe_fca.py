"""CVM IPE + FCA tests — corporate filings + cadastral form.

Network calls mocked with respx. Both products ship as ZIP-wrapped CSVs
on dados.cvm.gov.br with semicolon delimiter and ISO-8859-1 encoding,
so we synthesise tiny zips that mirror the real schema.
"""

from __future__ import annotations

import io
import re
import zipfile

import httpx
import pytest
import respx

from findata.http_client import clear_cache
from findata.sources.cvm.fca import (
    get_fca_dri,
    get_fca_geral,
    get_fca_valores_mobiliarios,
)
from findata.sources.cvm.ipe import get_ipe


@pytest.fixture(autouse=True)
def _clean_caches() -> None:
    clear_cache()


# ── IPE ─────────────────────────────────────────────────────────────


_IPE_CSV = (
    "CNPJ_Companhia;Nome_Companhia;Codigo_CVM;Data_Referencia;Categoria;Tipo;"
    "Especie;Assunto;Data_Entrega;Tipo_Apresentacao;Protocolo_Entrega;Versao;"
    "Link_Download\n"
    "33.592.510/0001-54;PETROBRAS;9512;2026-04-15;Fato Relevante;;Fato Relevante;"
    "Aprovação de dividendos;2026-04-15;AP - Apresentação;P001;1;"
    "https://www.rad.cvm.gov.br/ENET/p001\n"
    "33.592.510/0001-54;PETROBRAS;9512;2026-04-20;Assembleia;AGO;Boletim de voto;"
    ";2026-03-30;AP - Apresentação;P002;1;https://www.rad.cvm.gov.br/ENET/p002\n"
    "00.000.000/0001-91;BANCO DO BRASIL;1023;2026-04-21;Comunicado ao Mercado;;"
    "Comunicado;Calendário corporativo;2026-04-21;AP - Apresentação;P003;1;"
    "https://www.rad.cvm.gov.br/ENET/p003\n"
)


def _make_ipe_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("ipe_cia_aberta_2026.csv", _IPE_CSV.encode("iso-8859-1"))
    return buf.getvalue()


@respx.mock
async def test_ipe_no_filter_returns_all() -> None:
    respx.get(re.compile(r"https://.*ipe_cia_aberta_2026\.zip")).mock(
        return_value=httpx.Response(200, content=_make_ipe_zip())
    )
    rows = await get_ipe(2026)
    assert len(rows) == 3
    assert {r.protocolo for r in rows} == {"P001", "P002", "P003"}


@respx.mock
async def test_ipe_filter_by_cnpj() -> None:
    respx.get(re.compile(r"https://.*ipe_cia_aberta_2026\.zip")).mock(
        return_value=httpx.Response(200, content=_make_ipe_zip())
    )
    rows = await get_ipe(2026, cnpj="33.592.510/0001-54")
    assert len(rows) == 2
    assert all(r.cnpj == "33.592.510/0001-54" for r in rows)
    assert {r.categoria for r in rows} == {"Fato Relevante", "Assembleia"}


@respx.mock
async def test_ipe_filter_by_categoria() -> None:
    respx.get(re.compile(r"https://.*ipe_cia_aberta_2026\.zip")).mock(
        return_value=httpx.Response(200, content=_make_ipe_zip())
    )
    rows = await get_ipe(2026, categoria="Fato Relevante")
    assert len(rows) == 1
    fr = rows[0]
    assert fr.assunto == "Aprovação de dividendos"
    assert fr.link == "https://www.rad.cvm.gov.br/ENET/p001"
    assert fr.dt_entrega == "2026-04-15"


@respx.mock
async def test_ipe_strips_nbsp_in_optional_fields() -> None:
    """Regression — Codex found a real 2024 row with trailing NBSP in
    Assunto. Without stripping, exact-match deduplication breaks downstream.
    """
    csv_with_nbsp = (
        "CNPJ_Companhia;Nome_Companhia;Codigo_CVM;Data_Referencia;Categoria;Tipo;"
        "Especie;Assunto;Data_Entrega;Tipo_Apresentacao;Protocolo_Entrega;Versao;"
        "Link_Download\n"
        "34.274.233/0001-02;VIBRA;24295;2024-05-07;Documentos de Oferta;"
        "Anúncio de Encerramento;;Anúncio de Encerramento - 6ª Emissão\xa0;"
        "2024-05-07; AP - Apresentação \xa0;P999;1;https://example.org\n"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("ipe_cia_aberta_2024.csv", csv_with_nbsp.encode("iso-8859-1"))

    respx.get(re.compile(r"https://.*ipe_cia_aberta_2024\.zip")).mock(
        return_value=httpx.Response(200, content=buf.getvalue())
    )
    rows = await get_ipe(2024)
    assert len(rows) == 1
    r = rows[0]
    # NBSP and surrounding spaces gone.
    assert r.assunto == "Anúncio de Encerramento - 6ª Emissão"
    assert r.tipo_apresentacao == "AP - Apresentação"
    # Empty fields stay None, not "".
    assert r.especie is None


# ── FCA ─────────────────────────────────────────────────────────────


_FCA_GERAL_CSV = (
    "CNPJ_Companhia;Data_Referencia;Versao;ID_Documento;Nome_Empresarial;"
    "Data_Nome_Empresarial;Nome_Empresarial_Anterior;Data_Constituicao;Codigo_CVM;"
    "Data_Registro_CVM;Categoria_Registro_CVM;Data_Categoria_Registro_CVM;"
    "Situacao_Registro_CVM;Data_Situacao_Registro_CVM;Pais_Origem;"
    "Pais_Custodia_Valores_Mobiliarios;Setor_Atividade;Descricao_Atividade;"
    "Situacao_Emissor;Data_Situacao_Emissor;Especie_Controle_Acionario;"
    "Data_Especie_Controle_Acionario;Dia_Encerramento_Exercicio_Social;"
    "Mes_Encerramento_Exercicio_Social;Data_Alteracao_Exercicio_Social;Pagina_Web\n"
    "33.592.510/0001-54;2026-01-01;1;100;PETROBRAS;;;1953-10-03;9512;"
    "1977-12-12;Categoria A;2010-01-01;Ativo;1977-12-12;Brasil;Brasil;"
    "Petróleo e Gás;Petróleo, Gás e Biocombustíveis;Fase Operacional;"
    "1977-12-12;Estatal;1953-10-03;31;12;;www.petrobras.com.br\n"
    "00.000.000/0001-91;2026-01-01;1;101;BCO BRASIL S.A.;;;1808-10-12;1023;"
    "1977-07-20;Categoria A;2010-01-01;Ativo;1977-07-20;Brasil;Brasil;"
    "Bancos;Banco Múltiplo;Fase Operacional;1977-07-20;Estatal;1998-04-07;"
    "31;12;;www.bb.com.br\n"
)

_FCA_VM_CSV = (
    "CNPJ_Companhia;Data_Referencia;Versao;ID_Documento;Nome_Empresarial;"
    "Valor_Mobiliario;Sigla_Classe_Acao_Preferencial;Classe_Acao_Preferencial;"
    "Codigo_Negociacao;Composicao_BDR_Unit;Mercado;Sigla_Entidade_Administradora;"
    "Entidade_Administradora;Data_Inicio_Negociacao;Data_Fim_Negociacao;Segmento;"
    "Data_Inicio_Listagem;Data_Fim_Listagem\n"
    "33.592.510/0001-54;2026-01-01;1;100;PETROBRAS;Ações Ordinárias;;;"
    "PETR3;;Bolsa;B3;B3 S.A. - Brasil, Bolsa, Balcão.;2002-01-02;;"
    "Nível 2;1977-12-12;\n"
    "33.592.510/0001-54;2026-01-01;1;100;PETROBRAS;Ações Preferenciais;PN;PN;"
    "PETR4;;Bolsa;B3;B3 S.A. - Brasil, Bolsa, Balcão.;2002-01-02;;"
    "Nível 2;1977-12-12;\n"
    "00.000.000/0001-91;2026-01-01;1;101;BCO BRASIL S.A.;Ações Ordinárias;;;"
    "BBAS3;;Bolsa;B3;B3 S.A. - Brasil, Bolsa, Balcão.;2006-05-31;;"
    "Novo Mercado;1977-07-20;\n"
)

_FCA_DRI_CSV = (
    "CNPJ_Companhia;Data_Referencia;Versao;ID_Documento;Nome_Empresarial;"
    "Tipo_Responsavel;Responsavel;CPF_Responsavel;Tipo_Endereco;Logradouro;"
    "Complemento;Bairro;Cidade;Sigla_UF;UF;Pais;CEP;DDI_Telefone;DDD_Telefone;"
    "Telefone;DDI_Fax;DDD_Fax;Fax;Email;Data_Inicio_Atuacao;Data_Fim_Atuacao\n"
    "33.592.510/0001-54;2026-01-01;1;100;PETROBRAS;Diretor de Relações com "
    "Investidores;Pierangelo Esposito;111.222.333-44;;Av. Henrique Valadares, 28;"
    ";Centro;Rio de Janeiro;RJ;Rio de Janeiro;Brasil;20231030;;21;32249000;;;;"
    "ri@petrobras.com.br;2024-01-01;\n"
)


def _make_fca_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("fca_cia_aberta_geral_2026.csv", _FCA_GERAL_CSV.encode("iso-8859-1"))
        zf.writestr(
            "fca_cia_aberta_valor_mobiliario_2026.csv",
            _FCA_VM_CSV.encode("iso-8859-1"),
        )
        zf.writestr("fca_cia_aberta_dri_2026.csv", _FCA_DRI_CSV.encode("iso-8859-1"))
    return buf.getvalue()


@respx.mock
async def test_fca_geral_no_filter() -> None:
    respx.get(re.compile(r"https://.*fca_cia_aberta_2026\.zip")).mock(
        return_value=httpx.Response(200, content=_make_fca_zip())
    )
    rows = await get_fca_geral(2026)
    assert len(rows) == 2
    petr = next(r for r in rows if r.cnpj == "33.592.510/0001-54")
    assert petr.nome_empresarial == "PETROBRAS"
    assert petr.setor_atividade == "Petróleo e Gás"
    assert petr.especie_controle_acionario == "Estatal"
    assert petr.dia_encerramento_exercicio == 31
    assert petr.mes_encerramento_exercicio == 12
    assert petr.pagina_web == "www.petrobras.com.br"


@respx.mock
async def test_fca_geral_filter_by_cnpj() -> None:
    respx.get(re.compile(r"https://.*fca_cia_aberta_2026\.zip")).mock(
        return_value=httpx.Response(200, content=_make_fca_zip())
    )
    rows = await get_fca_geral(2026, cnpj="00.000.000/0001-91")
    assert len(rows) == 1
    assert rows[0].nome_empresarial == "BCO BRASIL S.A."


@respx.mock
async def test_fca_securities_ticker_resolver() -> None:
    respx.get(re.compile(r"https://.*fca_cia_aberta_2026\.zip")).mock(
        return_value=httpx.Response(200, content=_make_fca_zip())
    )
    rows = await get_fca_valores_mobiliarios(2026, ticker="petr4")
    assert len(rows) == 1
    s = rows[0]
    assert s.cnpj == "33.592.510/0001-54"
    assert s.codigo_negociacao == "PETR4"
    assert s.segmento == "Nível 2"
    assert s.valor_mobiliario == "Ações Preferenciais"


@respx.mock
async def test_fca_dri() -> None:
    respx.get(re.compile(r"https://.*fca_cia_aberta_2026\.zip")).mock(
        return_value=httpx.Response(200, content=_make_fca_zip())
    )
    rows = await get_fca_dri(2026, cnpj="33.592.510/0001-54")
    assert len(rows) == 1
    dri = rows[0]
    assert dri.responsavel == "Pierangelo Esposito"
    assert dri.email == "ri@petrobras.com.br"
    assert dri.uf == "RJ"
