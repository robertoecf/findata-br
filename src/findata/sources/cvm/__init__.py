"""CVM — Comissão de Valores Mobiliários (dados abertos).

Listed-company data + investment funds.

Funds (FI / FIF) coverage:

| Module             | Product (CVM)                                | Cadence           |
|--------------------|----------------------------------------------|-------------------|
| `funds.py`         | CAD (cadastro) + INF_DIARIO (cota / NAV)     | static / daily    |
| `holdings.py`      | CDA (Composição da Carteira) — every asset   | monthly           |
| `lamina.py`        | LAMINA (factsheet + rentabilidade mês/ano)   | monthly           |
| `profile.py`       | PERFIL_MENSAL (cotistas por tipo)            | monthly           |
| `_directory.py`    | HTML scrape helper for dynamic period lookup | (utility)         |
"""

from findata.sources.cvm._directory import (
    latest_period,
    list_files,
    list_periods,
)
from findata.sources.cvm.companies import Company, get_companies, search_company
from findata.sources.cvm.financials import (
    FinancialEntry,
    StatementType,
    get_dfp,
    get_itr,
)
from findata.sources.cvm.funds import Fund, FundDaily, get_fund_catalog, get_fund_daily
from findata.sources.cvm.holdings import FundHolding, get_fund_holdings
from findata.sources.cvm.lamina import (
    FundLamina,
    FundLaminaReturnMonth,
    FundLaminaReturnYear,
    get_fund_lamina,
    get_fund_monthly_returns,
    get_fund_yearly_returns,
)
from findata.sources.cvm.profile import FundProfile, get_fund_profile

__all__ = [
    "Company",
    "FinancialEntry",
    "Fund",
    "FundDaily",
    "FundHolding",
    "FundLamina",
    "FundLaminaReturnMonth",
    "FundLaminaReturnYear",
    "FundProfile",
    "StatementType",
    "get_companies",
    "get_dfp",
    "get_fund_catalog",
    "get_fund_daily",
    "get_fund_holdings",
    "get_fund_lamina",
    "get_fund_monthly_returns",
    "get_fund_profile",
    "get_fund_yearly_returns",
    "get_itr",
    "latest_period",
    "list_files",
    "list_periods",
    "search_company",
]
