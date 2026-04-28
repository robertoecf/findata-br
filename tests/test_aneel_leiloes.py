"""ANEEL leilões tests — energy-auction CSV parser.

Network calls mocked with respx. ANEEL CSVs are ;-delimited, ISO-8859-1,
with a mix of Brazilian-thousand decimals (158.641.610,00) and plain
decimals (140,00) — same parser handles both.
"""

from __future__ import annotations

import re

import httpx
import pytest
import respx

from findata.http_client import clear_cache
from findata.sources.aneel.leiloes import (
    LEILOES_GERACAO_URL,
    LEILOES_TRANSMISSAO_URL,
    get_aneel_leiloes_geracao,
    get_aneel_leiloes_transmissao,
)


@pytest.fixture(autouse=True)
def _clean_caches() -> None:
    clear_cache()


_GERACAO_CSV = (
    "DatGeracaoConjuntoDados;AnoLeilao;DatLeilao;NumLeilao;DscNumeroLeilaoCCEE;"
    "DscTipoLeilao;NomEmpreendimento;CodCEG;IdeNucleoCEG;SigTipoGeracao;"
    "DscFonteEnergia;DscDetalhamentoFonteEnergia;MdaPotenciaInstaladaMW;"
    "MdaGarantiaFisicaSEL;VlrEnergiaVendida;VlrPrecoTeto;VlrPrecoLeilao;"
    "VlrDesagio;VlrInvestimentoPrevisto;MdaDuracaoContrato;SigUFPrincipal;"
    "VlrCotacaoDolar;VlrPrecoTetoDolar;VlrPrecoDolar;VlrInvestimentoDolar;"
    "DscEmpresaVencedora\n"
    "2026-04-01;2005;2005-12-16;2005/2;1° LEN;A-5;Costa Pinto (AMPLIAÇÃO);"
    "UTE.AI.SP.028221-9;28221;UTE;Biomassa;Bagaço de Cana;56,14;22,00;19,00;"
    "140,00;138,99;,72;158.641.610,00;15;SP;2,33;57,91;59,47;67882588,79;"
    "Cosan S.A. Bioenergia\n"
    "2026-04-01;2024;2024-08-30;2024/3;LEN-2024;A-5;Eólica Lagoa Solta I;"
    "EOL.RN.012345-6;12345;EOL;Eólica;Eólica Onshore;100,00;45,00;40,00;"
    "180,00;165,50;8,06;500.000.000,00;20;RN;5,12;35,16;32,32;97656250,00;"
    "Vento Limpo Energia S.A.\n"
)

_TRANSMISSAO_CSV = (
    "AnoLeilao;DatLeilao;NumLeilao;NumLoteLeilao;NomEmpreendimento;"
    "SigUFPrincipal;QtdPrazoConstrucaoMeses;MdaExtensaoLinhaTransmissaoKm;"
    "MdaSubEstacoesMVA;VlrInvestimentoPrevisto;VlrRAPEditalLeilao;"
    "NomVencedorLeilao;VlrRAPVencedorLeilao;PctDesagio;DatGeracaoConjuntoDados\n"
    "1999;1999-12-03;007/1999;1;LT Taquaruçu - Assis 440 kV;SP;18;505,35;0,00;"
    "208000000,00;45290000,00;CONSÓRCIO MULTISERCE/AMP;41657760,00;0,08;2026-04-01\n"
    "2024;2024-06-28;01/2024;3;LT Lago Azul - Brasília 500 kV;DF;36;680,00;"
    "1500,00;1.500.000.000,00;320.000.000,00;Consórcio Lago Azul;280.000.000,00;"
    "12,5;2026-04-01\n"
)


@respx.mock
async def test_geracao_parses_brazilian_decimals() -> None:
    respx.get(re.compile(re.escape(LEILOES_GERACAO_URL))).mock(
        return_value=httpx.Response(200, content=_GERACAO_CSV.encode("iso-8859-1"))
    )
    rows = await get_aneel_leiloes_geracao()
    assert len(rows) == 2
    cosan = rows[0]
    assert cosan.ano_leilao == 2005
    assert cosan.tipo_leilao == "A-5"
    assert cosan.fonte_energia == "Biomassa"
    assert cosan.detalhamento_fonte == "Bagaço de Cana"
    assert cosan.potencia_instalada_mw == 56.14
    assert cosan.preco_teto_brl_mwh == 140.00
    assert cosan.preco_leilao_brl_mwh == 138.99
    # Brazilian-thousand decimal — used to break the parser before Sprint 3.
    assert cosan.investimento_previsto_brl == 158_641_610.00
    assert cosan.duracao_contrato_anos == 15
    assert cosan.uf == "SP"
    assert cosan.empresa_vencedora == "Cosan S.A. Bioenergia"


@respx.mock
async def test_geracao_filter_by_year() -> None:
    respx.get(re.compile(re.escape(LEILOES_GERACAO_URL))).mock(
        return_value=httpx.Response(200, content=_GERACAO_CSV.encode("iso-8859-1"))
    )
    rows = await get_aneel_leiloes_geracao(year=2024)
    assert len(rows) == 1
    assert rows[0].fonte_energia == "Eólica"


@respx.mock
async def test_geracao_filter_by_fonte_substring() -> None:
    respx.get(re.compile(re.escape(LEILOES_GERACAO_URL))).mock(
        return_value=httpx.Response(200, content=_GERACAO_CSV.encode("iso-8859-1"))
    )
    rows = await get_aneel_leiloes_geracao(fonte="Eólica")
    assert len(rows) == 1
    assert rows[0].nome_empreendimento == "Eólica Lagoa Solta I"


@respx.mock
async def test_geracao_filter_by_uf_case_insensitive() -> None:
    respx.get(re.compile(re.escape(LEILOES_GERACAO_URL))).mock(
        return_value=httpx.Response(200, content=_GERACAO_CSV.encode("iso-8859-1"))
    )
    rows = await get_aneel_leiloes_geracao(uf="rn")
    assert len(rows) == 1
    assert rows[0].uf == "RN"


@respx.mock
async def test_transmissao_parses_rap_and_extensao() -> None:
    respx.get(re.compile(re.escape(LEILOES_TRANSMISSAO_URL))).mock(
        return_value=httpx.Response(200, content=_TRANSMISSAO_CSV.encode("iso-8859-1"))
    )
    rows = await get_aneel_leiloes_transmissao()
    assert len(rows) == 2
    assp = rows[0]
    assert assp.ano_leilao == 1999
    assert assp.uf == "SP"
    assert assp.extensao_linha_km == 505.35
    assert assp.rap_edital_brl == 45_290_000.00
    assert assp.rap_vencedor_brl == 41_657_760.00
    # Lago Azul row — Brazilian-thousand decimals on RAP and investimento
    df = rows[1]
    assert df.uf == "DF"
    assert df.investimento_previsto_brl == 1_500_000_000.00
    assert df.rap_edital_brl == 320_000_000.00
    assert df.rap_vencedor_brl == 280_000_000.00


@respx.mock
async def test_transmissao_filter_by_year_uf() -> None:
    respx.get(re.compile(re.escape(LEILOES_TRANSMISSAO_URL))).mock(
        return_value=httpx.Response(200, content=_TRANSMISSAO_CSV.encode("iso-8859-1"))
    )
    rows = await get_aneel_leiloes_transmissao(year=2024, uf="DF")
    assert len(rows) == 1
    assert rows[0].nome_empreendimento == "LT Lago Azul - Brasília 500 kV"
