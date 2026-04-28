"""ANEEL — Agência Nacional de Energia Elétrica (open data).

Currently covers energy-auction results (geração + transmissão), the
flagship financial dataset in ANEEL's CKAN catalog. Other ANEEL
datasets (tarifas, bandeiras, geração distribuída, etc.) live behind
the same CKAN at ``dadosabertos.aneel.gov.br`` and can be added later
following the same pattern.

Source: ``https://dadosabertos.aneel.gov.br/`` (CKAN 2.9, public).
"""

from findata.sources.aneel.leiloes import (
    LeilaoGeracao,
    LeilaoTransmissao,
    get_aneel_leiloes_geracao,
    get_aneel_leiloes_transmissao,
)

__all__ = [
    "LeilaoGeracao",
    "LeilaoTransmissao",
    "get_aneel_leiloes_geracao",
    "get_aneel_leiloes_transmissao",
]
