"""Testes do coletor de eventos da Câmara (agenda, área nova bicameral).

Campos conferidos contra a fonte viva (2026-08-02).
"""

import unittest

from camara.eventos import (
    processar_eventos_para_prata,
    rodada_eventos,
    transformar_evento,
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


def _ev(eid=82678, tipo="Sessão Solene", desc="Homenagem ao Ano X",
        ini="2026-08-03T15:00", orgao_id=180, sigla="PLEN"):
    return {"id": eid, "dataHoraInicio": ini, "dataHoraFim": None,
            "situacao": "Agendada", "descricaoTipo": tipo, "descricao": desc,
            "localExterno": None,
            "orgaos": [{"id": orgao_id, "sigla": sigla, "nome": "Plenário"}],
            "localCamara": {"nome": "Plenário da Câmara"},
            "urlRegistro": "http://x/reg", "uri": "http://x/uri"}


class TestTransformacao(unittest.TestCase):
    def test_shape_e_slug_do_orgao(self):
        p = transformar_evento(_ev(orgao_id=2003, sigla="CCJC"))
        self.assertEqual(p["casa"], "camara")
        self.assertEqual(p["id_fonte"], "82678")
        self.assertEqual(p["tipo"], "Sessão Solene")
        self.assertEqual(p["titulo"], "Homenagem ao Ano X")
        self.assertEqual(p["situacao"], "Agendada")
        self.assertEqual(p["orgao_sigla"], "CCJC")
        # slug reconstruído bate com o de camara/coletivos.py
        self.assertEqual(p["orgao_slug"], "comissao-ccjc-2003")
        self.assertEqual(p["local"], "Plenário da Câmara")


class TestPortao(unittest.TestCase):
    def test_valido_passa(self):
        r = processar_eventos_para_prata([RegistroBronze.de("camara.eventos", "u", _ev())])
        self.assertEqual(len(r.aprovados), 1)

    def test_sem_data_vai_para_quarentena(self):
        ev = _ev()
        ev["dataHoraInicio"] = None
        r = processar_eventos_para_prata([RegistroBronze.de("camara.eventos", "u", ev)])
        self.assertEqual(r.aprovados, [])


class TestRodada(unittest.TestCase):
    def test_rodada_feliz(self):
        cli = ClienteFake({f"{BASE}/eventos": _Resp(200, {"dados": [_ev()], "links": []})})
        r = rodada_eventos(cli, data_inicio="2026-08-01", data_fim="2026-08-07",
                           canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 1)

    def test_janela_vazia_e_ok(self):
        cli = ClienteFake({f"{BASE}/eventos": _Resp(200, {"dados": [], "links": []})})
        r = rodada_eventos(cli, data_inicio="2026-01-01", data_fim="2026-01-02",
                           canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(r.prata.aprovados, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
