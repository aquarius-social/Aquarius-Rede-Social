"""Testes do coletor de despesas / CEAP (Área A, §8).

O coração é a identidade §5.2: documento - glosa = líquido, com um caso que
aceita e um que recusa.
"""

import unittest
from typing import Any

from camara.despesas import (
    processar_despesas_para_prata,
    rodada_despesas,
    transformar_despesa,
)
from contrato.canario import EstadoContrato
from pipeline.camadas import RegistroBronze


class _Resp:
    def __init__(self, status, corpo):
        self.status = status
        self.corpo = corpo
    def texto(self):
        return str(self.corpo)


class ClienteFake:
    def __init__(self, por_url):
        self.por_url = {k: list(v) for k, v in por_url.items()}
    def get(self, url, params=None):
        fila = self.por_url.get(url)
        if fila is None:
            raise AssertionError(f"sem resposta para {url}")
        return fila.pop(0)


def _despesa(doc=2000.0, glosa=0.0, liq=2000.0, cod=123, parcela=0):
    return {"ano": 2025, "mes": 12, "tipoDespesa": "DIVULGAÇÃO",
            "tipoDocumento": "Nota Fiscal", "codDocumento": cod, "codLote": 9,
            "numDocumento": "NF-1", "numRessarcimento": "R1", "parcela": parcela,
            "dataDocumento": "2025-12-15", "valorDocumento": doc,
            "valorGlosa": glosa, "valorLiquido": liq,
            "nomeFornecedor": "Fornecedor X", "cnpjCpfFornecedor": "00000000000191",
            "urlDocumento": "http://x"}


def _bronze(payload):
    return RegistroBronze.de("camara.despesas", "https://x", payload)


class TestTransformacaoDespesa(unittest.TestCase):
    def test_shape_e_cod_zero_vira_none(self):
        p = transformar_despesa(_despesa(cod=0), "204379")
        self.assertEqual(p["deputado_id_fonte"], "204379")
        self.assertEqual(p["ano"], 2025)
        self.assertIsNone(p["cod_documento"])   # 0 = sem documento → None
        self.assertEqual(p["valor_liquido"], 2000.0)


class TestIdentidadeValor(unittest.TestCase):
    def test_identidade_coerente_passa(self):
        r = processar_despesas_para_prata(
            [_bronze(_despesa(doc=2000, glosa=50, liq=1950))], "1")
        self.assertEqual(len(r.aprovados), 1)

    def test_identidade_violada_vai_para_quarentena(self):
        r = processar_despesas_para_prata(
            [_bronze(_despesa(doc=2000, glosa=50, liq=1900))], "1")  # 1950 != 1900
        self.assertEqual(r.aprovados, [])
        self.assertEqual(r.quarentena[0][1].dimensao, "precisao")

    def test_estorno_negativo_coerente_passa(self):
        """Achado da fonte viva: estorno (valor negativo) é legítimo e satisfaz
        a identidade — deve PASSAR, não ir à quarentena. Recusar por sinal
        descartaria reembolsos reais (ex.: passagem aérea cancelada)."""
        r = processar_despesas_para_prata(
            [_bronze(_despesa(doc=-3121.6, glosa=0.0, liq=-3121.6))], "1")
        self.assertEqual(len(r.aprovados), 1)
        self.assertEqual(r.quarentena, [])


class TestRodadaDespesas(unittest.TestCase):
    _URL = "https://dadosabertos.camara.leg.br/api/v2/deputados/204379/despesas"

    def test_rodada_feliz(self):
        cli = ClienteFake({self._URL: [_Resp(200, {"dados": [
            _despesa(cod=1), _despesa(cod=2, doc=100, glosa=0, liq=100)],
            "links": []})]})
        r = rodada_despesas(cli, "204379", ano=2025, canario_validado=True,
                            linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 2)

    def test_falha(self):
        cli = ClienteFake({self._URL: [_Resp(404, "x")]})
        r = rodada_despesas(cli, "204379", ano=2025, canario_validado=True,
                            linha_base=None)
        self.assertIs(r.estado, EstadoContrato.FALHA)
        self.assertIsNone(r.prata)


if __name__ == "__main__":
    unittest.main(verbosity=2)
