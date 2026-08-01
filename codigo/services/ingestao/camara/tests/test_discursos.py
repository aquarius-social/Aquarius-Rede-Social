"""Testes do coletor de discursos da Câmara (Área G).

Campos conferidos contra a fonte viva (2026-07-31, deputado 74784). O discurso
não tem id próprio: identidade composta (deputado, dataHoraInicio), como o voto.
"""

import unittest

from camara.discursos import (
    processar_discursos_para_prata,
    rodada_discursos,
    transformar_discurso,
)
from contrato.canario import EstadoContrato
from pipeline.camadas import RegistroBronze

BASE = "https://dadosabertos.camara.leg.br/api/v2"


class _Resp:
    def __init__(self, status, corpo):
        self.status = status
        self.corpo = corpo
    def texto(self):
        return str(self.corpo)


class ClienteFake:
    def __init__(self, por_url):
        self.por_url = por_url
    def get(self, url, params=None):
        if url not in self.por_url:
            raise AssertionError(f"sem resposta para {url}")
        return self.por_url[url]


def _disc(inicio="2024-12-18T14:00", tipo="COMO LÍDER", trans="texto longo"):
    return {"dataHoraInicio": inicio, "dataHoraFim": "2024-12-18T14:10",
            "tipoDiscurso": tipo, "keywords": "Ditadura,CNV", "sumario": "resumo",
            "urlTexto": "http://x/texto", "urlVideo": "http://x/video",
            "urlAudio": None, "transcricao": trans}


def _bronze(item):
    return RegistroBronze.de("camara.discursos", "u", item)


class TestTransformacao(unittest.TestCase):
    def test_id_composto_e_shape(self):
        p = transformar_discurso(_disc(), "74784")
        self.assertEqual(p["casa"], "camara")
        self.assertEqual(p["sistema"], "camara")
        self.assertEqual(p["parlamentar_id_fonte"], "74784")
        self.assertEqual(p["id_fonte"], "74784:2024-12-18T14:00")
        self.assertEqual(p["data"], "2024-12-18")
        self.assertEqual(p["tipo"], "COMO LÍDER")
        self.assertTrue(p["tem_transcricao"])
        self.assertEqual(p["url_texto"], "http://x/texto")

    def test_sem_transcricao_flag_falsa(self):
        p = transformar_discurso(_disc(trans=""), "74784")
        self.assertFalse(p["tem_transcricao"])


class TestPortao(unittest.TestCase):
    def test_valido_passa(self):
        r = processar_discursos_para_prata([_bronze(_disc())], "74784")
        self.assertEqual(len(r.aprovados), 1)

    def test_sem_data_vai_para_quarentena(self):
        r = processar_discursos_para_prata([_bronze(_disc(inicio=None))], "74784")
        self.assertEqual(r.aprovados, [])
        self.assertEqual(r.quarentena[0][1].dimensao, "completude")


class TestRodada(unittest.TestCase):
    def _cliente(self, dados):
        return ClienteFake({
            f"{BASE}/deputados/74784/discursos": _Resp(200, {"dados": dados, "links": []})})

    def test_rodada_feliz(self):
        r = rodada_discursos(self._cliente([_disc()]), "74784",
                             canario_validado=True, linha_base=None,
                             data_inicio="2024-01-01", data_fim="2024-12-31")
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 1)

    def test_deputado_sem_discurso_na_janela_e_ok_vazio(self):
        """Lista vazia legítima não é FALHA de contrato — é ausência honesta."""
        r = rodada_discursos(self._cliente([]), "74784",
                             canario_validado=True, linha_base=None,
                             data_inicio="2024-01-01", data_fim="2024-12-31")
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(r.prata.aprovados, [])

    def test_canario_nao_validado_com_dado_vira_falha(self):
        r = rodada_discursos(self._cliente([_disc()]), "74784",
                             canario_validado=False, linha_base=None,
                             data_inicio="2024-01-01", data_fim="2024-12-31")
        self.assertIs(r.estado, EstadoContrato.FALHA)


if __name__ == "__main__":
    unittest.main(verbosity=2)
