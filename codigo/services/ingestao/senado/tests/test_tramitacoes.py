"""Testes do coletor de tramitações do Senado (Área D, bicameral).

Fonte é o endpoint SUBSTITUTO /processo/{id} (o /movimentacoes foi
descontinuado, §19). Verificado ao vivo em 2026-08-01 (processo 8614284).
A sequência é derivada da ordem de `id` (criação) e a checagem §5.2 confere que
a data não retrocede nessa ordem — teste real, não tautológico.
"""

import unittest

from contrato.canario import EstadoContrato
from pipeline.camadas import RegistroBronze
from senado.tramitacoes import (
    _iso,
    processar_tramitacoes_senado_para_prata,
    rodada_tramitacoes_senado,
    transformar_tramitacao_senado,
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
    def get(self, url, params=None):
        if url not in self.por_url:
            raise AssertionError(f"sem resposta para {url}")
        return self.por_url[url]


def _informe(iid=2176723, data="2024-01-02 09:45:27", sigla="PLEN",
             desc="Matéria recebida"):
    return {"id": iid, "data": data,
            "colegiado": {"sigla": sigla, "nome": "Plenário"},
            "enteAdministrativo": {"sigla": "SLSF"}, "descricao": desc}


def _processo(informes):
    return {"id": 8614284, "codigoMateria": "161856",
            "autuacoes": [{"numero": 1, "movimentacoes": [],
                           "informesLegislativos": informes}]}


def _bronze(informe):
    return RegistroBronze.de("senado.tramitacoes", "u", informe)


class TestIso(unittest.TestCase):
    def test_espaco_vira_t(self):
        self.assertEqual(_iso("2024-01-02 09:45:27"), "2024-01-02T09:45:27")
        self.assertIsNone(_iso(None))


class TestTransformacao(unittest.TestCase):
    def test_shape(self):
        p = transformar_tramitacao_senado(_informe(), "161856", 1)
        self.assertEqual(p["casa"], "senado")
        self.assertEqual(p["proposicao_id_fonte"], "161856")
        self.assertEqual(p["sequencia"], 1)
        self.assertEqual(p["data_hora"], "2024-01-02T09:45:27")
        self.assertEqual(p["orgao_sigla"], "PLEN")
        self.assertEqual(p["descricao"], "Matéria recebida")


class TestProcessar(unittest.TestCase):
    def test_sequencia_segue_ordem_de_id(self):
        # id maior = criado depois; a sequência deve refletir a ordem de id
        b = [_bronze(_informe(2177302, data="2024-02-05 20:16:13")),
             _bronze(_informe(2176723, data="2024-01-02 09:45:27"))]
        r = processar_tramitacoes_senado_para_prata(b, "161856")
        seq_por_data = {t["data_hora"][:10]: t["sequencia"] for t in r.aprovados}
        self.assertEqual(seq_por_data["2024-01-02"], 1)   # id menor → seq 1
        self.assertEqual(seq_por_data["2024-02-05"], 2)

    def test_sem_data_vai_para_quarentena(self):
        inf = _informe()
        del inf["data"]
        r = processar_tramitacoes_senado_para_prata([_bronze(inf)], "161856")
        self.assertEqual(r.aprovados, [])


class TestRodada(unittest.TestCase):
    def _cliente(self, informes):
        return ClienteFake({
            f"{BASE}/processo/8614284": _Resp(200, _processo(informes))})

    def test_rodada_feliz_sem_violacao(self):
        cli = self._cliente([
            _informe(2176723, data="2024-01-02 09:45:27"),
            _informe(2177302, data="2024-02-05 20:16:13", desc="Distribuída")])
        r = rodada_tramitacoes_senado(cli, "8614284", "161856",
                                      canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 2)
        self.assertEqual(r.sequencia_violacoes, [])

    def test_data_que_retrocede_na_ordem_de_id_e_violacao(self):
        """id maior (criado depois) com data ANTERIOR = cadeia não monotônica §5.2."""
        cli = self._cliente([
            _informe(100, data="2024-05-01 10:00:00"),
            _informe(200, data="2024-01-01 10:00:00")])  # id maior, data menor
        r = rodada_tramitacoes_senado(cli, "8614284", "161856",
                                      canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertTrue(len(r.sequencia_violacoes) >= 1)

    def test_materia_sem_informe_e_ok_vazio(self):
        r = rodada_tramitacoes_senado(self._cliente([]), "8614284", "161856",
                                      canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(r.prata.aprovados, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
