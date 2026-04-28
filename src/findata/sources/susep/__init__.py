"""SUSEP — Superintendência de Seguros Privados (open data, partial).

SUSEP supervises insurance, open-end pension, and capitalization
companies. Most of its statistical data lives behind the SES (Sistema
de Estatísticas) ``.aspx`` portal and requires session-bound form
posts to download — out of scope for an HTTP-stateless library.

What we ship: the public ``LISTAEMPRESAS.csv`` lookup table — a
canonical roster of every SUSEP-supervised entity with FIP code, name,
and CNPJ. Useful as a CNPJ resolver or to filter joint-product feeds.

Source: ``https://www2.susep.gov.br/menuestatistica/ses/``
"""

from findata.sources.susep.empresas import (
    EmpresaSusep,
    get_susep_empresas,
    search_susep_empresa,
)

__all__ = [
    "EmpresaSusep",
    "get_susep_empresas",
    "search_susep_empresa",
]
