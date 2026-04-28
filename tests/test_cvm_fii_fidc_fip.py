"""CVM FII / FIDC / FIP tests — fundos imobiliários, direitos creditórios, participações.

Network calls mocked with respx. Each product has a different shape:
- FII: annual ZIP with 3 CSVs (geral, complemento, ativo_passivo)
- FIDC: monthly ZIP with 12 CSVs (TAB I..X)
- FIP: annual single CSV (no zip wrapper)
"""

from __future__ import annotations

import io
import re
import zipfile

import httpx
import pytest
import respx

from findata.http_client import clear_cache
from findata.sources.cvm.fidc import (
    get_fidc_direitos_creditorios,
    get_fidc_geral,
    get_fidc_pl,
)
from findata.sources.cvm.fii import get_fii_complemento, get_fii_geral
from findata.sources.cvm.fip import get_fip


@pytest.fixture(autouse=True)
def _clean_caches() -> None:
    clear_cache()


# ── FII ─────────────────────────────────────────────────────────────


def _make_fii_zip() -> bytes:
    geral_header = (
        "Tipo_Fundo_Classe;CNPJ_Fundo_Classe;Data_Referencia;Versao;"
        "Nome_Fundo_Classe;Codigo_ISIN;Quantidade_Cotas_Emitidas;Mandato;"
        "Segmento_Atuacao;Tipo_Gestao;Prazo_Duracao;Nome_Administrador;"
        "CNPJ_Administrador;Publico_Alvo;Fundo_Exclusivo;"
        "Encerramento_Exercicio_Social;Data_Funcionamento\n"
    )
    geral_rows = (
        "FII;12.345.678/0001-99;2026-01-31;1;FII TESTE LOGISTICA;BRTSTLOGCTF000;"
        "1000000;Renda;Logística;Ativa;Indeterminado;BTG PACTUAL SERVICOS;"
        "59.281.253/0001-23;Investidor geral;N;31/12;2018-05-15\n"
        "FII;12.345.678/0001-99;2026-02-28;1;FII TESTE LOGISTICA;BRTSTLOGCTF000;"
        "1000000;Renda;Logística;Ativa;Indeterminado;BTG PACTUAL SERVICOS;"
        "59.281.253/0001-23;Investidor geral;N;31/12;2018-05-15\n"
    )
    comp_header = (
        "CNPJ_Fundo_Classe;Data_Referencia;Versao;Total_Numero_Cotistas;"
        "Numero_Cotistas_Pessoa_Fisica;Numero_Cotistas_Pessoa_Juridica_Nao_Financeira;"
        "Numero_Cotistas_Banco_Comercial;Valor_Ativo;Patrimonio_Liquido;"
        "Cotas_Emitidas;Valor_Patrimonial_Cotas;Percentual_Despesas_Taxa_Administracao\n"
    )
    comp_rows = (
        "12.345.678/0001-99;2026-01-31;1;15234;14987;230;5;"
        "152340000,00;148230000,00;1000000,00;148,23;0,75\n"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "inf_mensal_fii_geral_2026.csv",
            (geral_header + geral_rows).encode("iso-8859-1"),
        )
        zf.writestr(
            "inf_mensal_fii_complemento_2026.csv",
            (comp_header + comp_rows).encode("iso-8859-1"),
        )
    return buf.getvalue()


@respx.mock
async def test_fii_geral_filter_by_cnpj() -> None:
    respx.get(re.compile(r"https://.*inf_mensal_fii_2026\.zip")).mock(
        return_value=httpx.Response(200, content=_make_fii_zip())
    )
    rows = await get_fii_geral(2026, cnpj="12.345.678/0001-99")
    assert len(rows) == 2
    assert rows[0].nome_fundo == "FII TESTE LOGISTICA"
    assert rows[0].segmento_atuacao == "Logística"
    assert rows[0].mandato == "Renda"
    assert rows[0].tipo_gestao == "Ativa"
    assert rows[0].nome_administrador == "BTG PACTUAL SERVICOS"
    assert rows[0].quantidade_cotas_emitidas == 1_000_000


@respx.mock
async def test_fii_geral_filter_by_month() -> None:
    respx.get(re.compile(r"https://.*inf_mensal_fii_2026\.zip")).mock(
        return_value=httpx.Response(200, content=_make_fii_zip())
    )
    rows = await get_fii_geral(2026, cnpj="12.345.678/0001-99", month=2)
    assert len(rows) == 1
    assert rows[0].dt_referencia == "2026-02-28"


@respx.mock
async def test_fii_complemento_parses_pl_and_cotistas() -> None:
    respx.get(re.compile(r"https://.*inf_mensal_fii_2026\.zip")).mock(
        return_value=httpx.Response(200, content=_make_fii_zip())
    )
    rows = await get_fii_complemento(2026, cnpj="12.345.678/0001-99")
    assert len(rows) == 1
    c = rows[0]
    assert c.patrimonio_liquido == 148_230_000.00
    assert c.valor_patrimonial_cotas == 148.23
    assert c.total_cotistas == 15234
    assert c.cotistas_pf == 14987
    assert c.pct_despesas_taxa_administracao == 0.75


# ── FIDC ────────────────────────────────────────────────────────────


def _make_fidc_zip() -> bytes:
    tab_i_header = (
        "TP_FUNDO_CLASSE;CNPJ_FUNDO_CLASSE;DENOM_SOCIAL;DT_COMPTC;CLASSE_UNICA;"
        "CNPJ_ADMIN;ADMIN;CLASSE;CNPJ_CLASSE;CONDOM\n"
    )
    tab_i_rows = (
        "FIDC;01.234.567/0001-89;FIDC TESTE CRED PRIV;2026-02-28;S;"
        "59.281.253/0001-23;BTG PACTUAL;Sênior;01.234.567/0002-70;Fechado\n"
        "FIDC;99.999.999/0001-00;OUTRO FIDC;2026-02-28;S;59.281.253/0001-23;"
        "BTG PACTUAL;Sênior;99.999.999/0002-91;Fechado\n"
    )
    tab_iv_header = (
        "TP_FUNDO_CLASSE;CNPJ_FUNDO_CLASSE;DENOM_SOCIAL;DT_COMPTC;"
        "TAB_IV_A_VL_PL;TAB_IV_B_VL_PL_MEDIO\n"
    )
    tab_iv_rows = (
        "FIDC;01.234.567/0001-89;FIDC TESTE CRED PRIV;2026-02-28;523000000,00;515250000,00\n"
    )
    tab_vii_header = (
        "TP_FUNDO_CLASSE;CNPJ_FUNDO_CLASSE;DENOM_SOCIAL;DT_COMPTC;"
        "TAB_VII_A1_1_QT_DIRCRED_RISCO;TAB_VII_A1_2_VL_DIRCRED_RISCO;"
        "TAB_VII_A2_1_QT_DIRCRED_SEM_RISCO;TAB_VII_A2_2_VL_DIRCRED_SEM_RISCO;"
        "TAB_VII_A3_1_QT_DIRCRED_VENC_AD;TAB_VII_A3_2_VL_DIRCRED_VENC_AD\n"
    )
    tab_vii_rows = (
        "FIDC;01.234.567/0001-89;FIDC TESTE CRED PRIV;2026-02-28;"
        "12000;380000000,00;500;15000000,00;100;3000000,00\n"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "inf_mensal_fidc_tab_I_202602.csv",
            (tab_i_header + tab_i_rows).encode("iso-8859-1"),
        )
        zf.writestr(
            "inf_mensal_fidc_tab_IV_202602.csv",
            (tab_iv_header + tab_iv_rows).encode("iso-8859-1"),
        )
        zf.writestr(
            "inf_mensal_fidc_tab_VII_202602.csv",
            (tab_vii_header + tab_vii_rows).encode("iso-8859-1"),
        )
    return buf.getvalue()


@respx.mock
async def test_fidc_geral_filter_by_cnpj() -> None:
    respx.get(re.compile(r"https://.*inf_mensal_fidc_202602\.zip")).mock(
        return_value=httpx.Response(200, content=_make_fidc_zip())
    )
    rows = await get_fidc_geral(2026, 2, cnpj="01.234.567/0001-89")
    assert len(rows) == 1
    g = rows[0]
    assert g.nome_fundo == "FIDC TESTE CRED PRIV"
    assert g.classe == "Sênior"
    assert g.condominio == "Fechado"
    assert g.nome_administrador == "BTG PACTUAL"


@respx.mock
async def test_fidc_pl_parses_brazilian_decimals() -> None:
    respx.get(re.compile(r"https://.*inf_mensal_fidc_202602\.zip")).mock(
        return_value=httpx.Response(200, content=_make_fidc_zip())
    )
    rows = await get_fidc_pl(2026, 2, cnpj="01.234.567/0001-89")
    assert len(rows) == 1
    assert rows[0].pl_final == 523_000_000.00
    assert rows[0].pl_medio == 515_250_000.00


@respx.mock
async def test_fidc_direitos_creditorios_parses_quantities() -> None:
    respx.get(re.compile(r"https://.*inf_mensal_fidc_202602\.zip")).mock(
        return_value=httpx.Response(200, content=_make_fidc_zip())
    )
    rows = await get_fidc_direitos_creditorios(2026, 2, cnpj="01.234.567/0001-89")
    assert len(rows) == 1
    d = rows[0]
    assert d.qtd_com_risco == 12000
    assert d.valor_com_risco == 380_000_000.00
    assert d.valor_sem_risco == 15_000_000.00


# ── FIP ─────────────────────────────────────────────────────────────


_FIP_HEADERS = [
    "CNPJ_FUNDO",  # 0
    "DENOM_SOCIAL",  # 1
    "DT_COMPTC",  # 2
    "VL_PATRIM_LIQ",  # 3
    "QT_COTA",  # 4
    "VL_PATRIM_COTA",  # 5
    "NR_COTST",  # 6
    "ENTID_INVEST",  # 7
    "PUBLICO_ALVO",  # 8
    "VL_CAP_COMPROM",  # 9
    "QT_COTA_SUBSCR",  # 10
    "VL_CAP_SUBSCR",  # 11
    "QT_COTA_INTEGR",  # 12
    "VL_CAP_INTEGR",  # 13
    "VL_INVEST_FIP_COTA",  # 14
    "NR_COTST_SUBSCR_PF",  # 15
    "PR_COTA_SUBSCR_PF",  # 16
    "NR_COTST_SUBSCR_PJ_NAO_FINANC",  # 17
    "PR_COTA_SUBSCR_PJ_NAO_FINANC",  # 18 ← long-tail field we assert via raw
    "NR_COTST_SUBSCR_BANCO",  # 19
    "PR_COTA_SUBSCR_BANCO",  # 20
    "NR_COTST_SUBSCR_CORRETORA_DISTRIB",  # 21
    "PR_COTA_SUBSCR_CORRETORA_DISTRIB",  # 22
    "NR_COTST_SUBSCR_PJ_FINANC",  # 23
    "PR_COTA_SUBSCR_PJ_FINANC",  # 24
    "NR_COTST_SUBSCR_INVNR",  # 25
    "PR_COTA_SUBSCR_INVNR",  # 26
    "NR_COTST_SUBSCR_EAPC",  # 27
    "PR_COTA_SUBSCR_EAPC",  # 28
    "NR_COTST_SUBSCR_EFPC",  # 29
    "PR_COTA_SUBSCR_EFPC",  # 30
    "NR_COTST_SUBSCR_RPPS",  # 31
    "PR_COTA_SUBSCR_RPPS",  # 32
    "NR_COTST_SUBSCR_SEGUR",  # 33
    "PR_COTA_SUBSCR_SEGUR",  # 34
    "NR_COTST_SUBSCR_CAPITALIZ",  # 35
    "PR_COTA_SUBSCR_CAPITALIZ",  # 36
    "NR_COTST_SUBSCR_FII",  # 37
    "PR_COTA_SUBSCR_FII",  # 38
    "NR_COTST_SUBSCR_FI",  # 39
    "PR_COTA_SUBSCR_FI",  # 40
    "NR_COTST_SUBSCR_DISTRIB",  # 41
    "PR_COTA_SUBSCR_DISTRIB",  # 42
    "NR_COTST_SUBSCR_OUTRO",  # 43
    "PR_COTA_SUBSCR_OUTRO",  # 44
    "NR_TOTAL_COTST_SUBSCR",  # 45
    "PR_TOTAL_COTA_SUBSCR",  # 46
    "CLASSE_COTA",  # 47
    "NR_COTST_SUBSCR_CLASSE",  # 48
    "QT_COTA_SUBSCR_CLASSE",  # 49
    "QT_COTA_INTEGR_CLASSE",  # 50
    "VL_QUOTA_CLASSE",  # 51
    "DIREITO_POLIT_CLASSE",  # 52
    "DIREITO_ECON_CLASSE",  # 53
]


def _fip_row(dt: str, pl: str, vp: str) -> str:
    """Build a fully-aligned 54-column FIP row. Position 18 carries 30,5
    so the include_raw assertion can verify long-tail fields."""
    values = [""] * len(_FIP_HEADERS)
    values[0] = "11.111.111/0001-11"
    values[1] = "FIP TESTE INFRA"
    values[2] = dt
    values[3] = pl
    values[4] = "1000000,00"
    values[5] = vp
    values[6] = "12"
    values[7] = "Investidor profissional"
    values[8] = "Profissional"
    values[9] = "1000000000,00"
    values[10] = "800000,00"
    values[11] = "700000000,00"
    values[12] = "500000,00"
    values[13] = "500000000,00"
    values[14] = "0"
    values[15] = "0"
    values[16] = "0"
    values[17] = "5"
    values[18] = "30,5"  # PR_COTA_SUBSCR_PJ_NAO_FINANC — asserted via raw
    values[19] = "1"
    values[20] = "5,0"
    values[45] = "12"
    values[46] = "100,0"
    values[47] = "Subordinada"
    values[48] = "12"
    values[49] = "800000"
    values[50] = "500000"
    values[51] = vp
    values[52] = "Total"
    values[53] = "Total"
    return ";".join(values) + "\n"


_FIP_CSV = (
    ";".join(_FIP_HEADERS)
    + "\n"
    + _fip_row("2023-03-31", "500000000,00", "500,00")
    + _fip_row("2023-06-30", "520000000,00", "520,00")
)


@respx.mock
async def test_fip_filter_by_cnpj() -> None:
    respx.get(re.compile(r"https://.*inf_trimestral_fip_2023\.csv")).mock(
        return_value=httpx.Response(200, text=_FIP_CSV)
    )
    rows = await get_fip(2023, cnpj="11.111.111/0001-11")
    assert len(rows) == 2
    assert rows[0].nome_fundo == "FIP TESTE INFRA"
    assert rows[0].patrimonio_liquido == 500_000_000.0
    assert rows[0].capital_comprometido == 1_000_000_000.0
    assert rows[0].num_cotistas == 12
    assert rows[0].classe_cota == "Subordinada"


@respx.mock
async def test_fip_filter_by_quarter() -> None:
    respx.get(re.compile(r"https://.*inf_trimestral_fip_2023\.csv")).mock(
        return_value=httpx.Response(200, text=_FIP_CSV)
    )
    q1 = await get_fip(2023, cnpj="11.111.111/0001-11", quarter=1)
    assert len(q1) == 1
    assert q1[0].dt_referencia == "2023-03-31"

    q2 = await get_fip(2023, cnpj="11.111.111/0001-11", quarter=2)
    assert len(q2) == 1
    assert q2[0].dt_referencia == "2023-06-30"
    assert q2[0].patrimonio_liquido == 520_000_000.0


@respx.mock
async def test_fip_include_raw_carries_full_row() -> None:
    respx.get(re.compile(r"https://.*inf_trimestral_fip_2023\.csv")).mock(
        return_value=httpx.Response(200, text=_FIP_CSV)
    )
    rows = await get_fip(2023, cnpj="11.111.111/0001-11", quarter=1, include_raw=True)
    assert rows[0].raw is not None
    # Long-tail column not modeled explicitly but available via raw.
    assert rows[0].raw.get("PR_COTA_SUBSCR_PJ_NAO_FINANC") == "30,5"
