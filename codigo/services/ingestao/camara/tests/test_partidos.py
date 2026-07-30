"""Testes do coletor de partidos canônicos (§4)."""

import unittest
from typing import Any

from camara.partidos import (
    processar_partidos_para_prata,
    rodada_partidos,
    transformar_partido,
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


def _part(pid=36898, sigla="AVANTE", nome="Avante"):
    return {"id": pid, "sigla": sigla, "nome": nome, "uri": f"x/{pid}"}


def _part_det(pid=36898, numero=70, situacao="Ativo"):
    return {"id": pid, "numeroEleitoral": numero, "status": {"situacao": situacao}}


def _bronze(payload):
    return RegistroBronze.de("camara.partidos", "https://x", payload)


class TestTransformacaoPartido(unittest.TestCase):
    def test_shape_e_slug(self):
        p = transformar_partido(_part())
        self.assertEqual(p["tipo"], "partido")
        self.assertEqual(p["sigla"], "AVANTE")
        self.assertEqual(p["slug"], "partido-avante-36898")
        self.assertTrue(p["ativo"])  # sem detalhe, assume ativo

    def test_detalhe_preenche_numero_e_situacao(self):
        p = transformar_partido(_part(), _part_det(numero=70, situacao="Ativo"))
        self.assertEqual(p["numero_urna"], 70)
        self.assertTrue(p["ativo"])

    def test_situacao_inativo_marca_ativo_false(self):
        p = transformar_partido(_part(), _part_det(situacao="Inativo"))
        self.assertFalse(p["ativo"])


class TestPortaoPartido(unittest.TestCase):
    def test_valido_passa(self):
        r = processar_partidos_para_prata([_bronze(_part())])
        self.assertEqual(len(r.aprovados), 1)

    def test_sem_sigla_vai_para_quarentena(self):
        p = _part()
        del p["sigla"]
        r = processar_partidos_para_prata([_bronze(p)])
        self.assertEqual(r.aprovados, [])
        _, v = r.quarentena[0]
        self.assertEqual(v.dimensao, "completude")


class TestRodadaPartidos(unittest.TestCase):
    def test_rodada_feliz_enriquece(self):
        cliente = ClienteFake({
            "https://dadosabertos.camara.leg.br/api/v2/partidos":
                [_Resp(200, {"dados": [_part(36898, "AVANTE", "Avante")],
                             "links": []})],
            "https://dadosabertos.camara.leg.br/api/v2/partidos/36898":
                [_Resp(200, {"dados": _part_det(36898, numero=70)})],
        })
        r = rodada_partidos(cliente, canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 1)
        self.assertEqual(r.prata.aprovados[0]["numero_urna"], 70)
        self.assertEqual(len(r.detalhes_bronze), 1)

    def test_falha_na_fonte(self):
        cliente = ClienteFake({
            "https://dadosabertos.camara.leg.br/api/v2/partidos":
                [_Resp(404, "not found")],
        })
        r = rodada_partidos(cliente, canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.FALHA)
        self.assertIsNone(r.prata)


if __name__ == "__main__":
    unittest.main(verbosity=2)
