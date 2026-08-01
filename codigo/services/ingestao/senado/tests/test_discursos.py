"""Testes do coletor de discursos do Senado (Área G, bicameral).

Campos conferidos contra a fonte viva (2026-07-31, senador 5672). Produz a mesma
prata que o coletor da Câmara; o pronunciamento TEM id próprio.
"""

import unittest

from contrato.canario import EstadoContrato
from pipeline.camadas import RegistroBronze
from senado.discursos import (
    _aaaammdd,
    processar_discursos_senado_para_prata,
    rodada_discursos_senado,
    transformar_discurso_senado,
)

BASE = "https://legis.senado.leg.br/dadosabertos"


class _Resp:
    def __init__(self, status, corpo):
        self.status = status
        self.corpo = corpo
    def texto(self):
        return str(self.corpo)


class ClienteFake:
    def __init__(self, por_url):
        self.por_url = por_url
        self.ultimo_params = None
    def get(self, url, params=None):
        self.ultimo_params = params
        if url not in self.por_url:
            raise AssertionError(f"sem resposta para {url}")
        return self.por_url[url]


def _pron(cod="510783", data="2024-12-18"):
    return {"CodigoPronunciamento": cod, "DataPronunciamento": data,
            "TipoUsoPalavra": {"Descricao": "Como Relator"},
            "TextoResumo": "resumo", "Indexacao": "RELATOR,PROJETO DE LEI",
            "UrlTexto": "http://x/p/510783",
            "UrlTextoBinario": "http://x/bin/510783"}


def _wrap(pronunciamentos):
    par = {}
    if pronunciamentos is not None:
        par["Pronunciamentos"] = {"Pronunciamento": pronunciamentos}
    return {"DiscursosParlamentar": {"Parlamentar": par}}


def _bronze(item):
    return RegistroBronze.de("senado.discursos", "u", item)


class TestFormatoData(unittest.TestCase):
    def test_iso_vira_aaaammdd(self):
        self.assertEqual(_aaaammdd("2024-01-31"), "20240131")
        self.assertEqual(_aaaammdd("20240131"), "20240131")


class TestTransformacao(unittest.TestCase):
    def test_shape(self):
        p = transformar_discurso_senado(_pron(), "5672")
        self.assertEqual(p["casa"], "senado")
        self.assertEqual(p["sistema"], "senado")
        self.assertEqual(p["parlamentar_id_fonte"], "5672")
        self.assertEqual(p["id_fonte"], "510783")   # id próprio, não composto
        self.assertEqual(p["data"], "2024-12-18")
        self.assertEqual(p["tipo"], "Como Relator")
        self.assertTrue(p["tem_transcricao"])        # tem UrlTextoBinario


class TestPortao(unittest.TestCase):
    def test_valido_passa(self):
        r = processar_discursos_senado_para_prata([_bronze(_pron())], "5672")
        self.assertEqual(len(r.aprovados), 1)

    def test_sem_codigo_vai_para_quarentena(self):
        p = _pron()
        del p["CodigoPronunciamento"]
        r = processar_discursos_senado_para_prata([_bronze(p)], "5672")
        self.assertEqual(r.aprovados, [])


class TestRodada(unittest.TestCase):
    def _cliente(self, wrap):
        return ClienteFake({f"{BASE}/senador/5672/discursos": _Resp(200, wrap)})

    def test_rodada_feliz_converte_data_para_aaaammdd(self):
        cli = self._cliente(_wrap([_pron()]))
        r = rodada_discursos_senado(cli, "5672", canario_validado=True,
                                    linha_base=None, data_inicio="2024-01-01",
                                    data_fim="2024-12-31")
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 1)
        # a janela foi passada no formato que a fonte exige
        self.assertEqual(cli.ultimo_params["dataInicio"], "20240101")

    def test_senador_sem_pronunciamento_e_ok_vazio(self):
        r = rodada_discursos_senado(self._cliente(_wrap(None)), "5672",
                                    canario_validado=True, linha_base=None,
                                    data_inicio="2024-01-01", data_fim="2024-12-31")
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(r.prata.aprovados, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
