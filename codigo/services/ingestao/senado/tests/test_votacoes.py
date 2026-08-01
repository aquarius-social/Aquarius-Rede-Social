"""Testes do coletor de votações do Senado (Área C, §10/§5.2, bicameral).

Fonte é o endpoint SUBSTITUTO /votacao (o /materia/votacoes foi descontinuado,
§19). Verificado ao vivo em 2026-08-01. Placar e nominais vêm inline.
"""

import unittest

from contrato.canario import EstadoContrato
from senado.votacoes import (
    _mapear_voto,
    _reconciliar_placar,
    rodada_votacoes_senado,
    transformar_votacao_senado,
)

BASE = "https://legis.senado.leg.br/dadosabertos"
URL = f"{BASE}/votacao"


class _Resp:
    def __init__(self, status, corpo):
        self.status = status
        self.corpo = corpo
    def texto(self):
        return str(self.corpo)


class ClienteFake:
    def __init__(self, corpo):
        self._corpo = corpo
    def get(self, url, params=None):
        return _Resp(200, self._corpo)


def _voto(cod, sigla, partido="PT"):
    return {"codigoParlamentar": cod, "siglaVotoParlamentar": sigla,
            "nomeParlamentar": f"Sen {cod}", "siglaPartidoParlamentar": partido,
            "siglaUFParlamentar": "SP"}


def _votacao(idf=6883, secreta="N", sim=2, nao=1, ab=0, votos=None, mat="161856"):
    return {"codigoSessaoVotacao": idf, "codigoMateria": mat, "idProcesso": 999,
            "sigla": "PL", "numero": "1", "ano": 2024, "dataSessao": "2024-12-10",
            "descricaoVotacao": "Votação nominal do PL 1/2024",
            "identificacao": "PL 1/2024", "resultadoVotacao": "A",
            "votacaoSecreta": secreta, "totalVotosSim": sim, "totalVotosNao": nao,
            "totalVotosAbstencao": ab, "votos": votos or []}


class TestMapearVoto(unittest.TestCase):
    def test_posicoes_e_ausencias(self):
        self.assertEqual(_mapear_voto("Sim"), "sim")
        self.assertEqual(_mapear_voto("Não"), "nao")
        self.assertEqual(_mapear_voto("Abstenção"), "abstencao")
        self.assertEqual(_mapear_voto("AP"), "ausente")     # atividade parlamentar
        self.assertEqual(_mapear_voto("P-NRV"), "ausente")

    def test_nao_posicao_vira_none(self):
        self.assertIsNone(_mapear_voto("Votou"))            # secreto, oculto
        self.assertIsNone(_mapear_voto("Presidente (art. 51 RISF)"))


class TestTransformacao(unittest.TestCase):
    def test_shape_aberta(self):
        v = transformar_votacao_senado(_votacao(votos=[_voto(1, "Sim")]))
        self.assertEqual(v["casa"], "senado")
        self.assertEqual(v["id_fonte"], "6883")
        self.assertEqual(v["proposicao_id_fonte"], "161856")
        self.assertEqual(v["resultado"], "Aprovada")
        self.assertEqual(v["sim"], 2)
        self.assertFalse(v["secreta"])
        self.assertTrue(v["nominal"])

    def test_secreta_marca_flag_e_sem_nominal(self):
        v = transformar_votacao_senado(_votacao(secreta="S", votos=[_voto(1, "Votou")]))
        self.assertTrue(v["secreta"])
        self.assertFalse(v["nominal"])


class TestReconciliacao(unittest.TestCase):
    def test_placar_bate_sem_violacao(self):
        p = _votacao(sim=2, nao=1, votos=[_voto(1, "Sim"), _voto(2, "Sim"), _voto(3, "Não")])
        self.assertIsNone(_reconciliar_placar(p))

    def test_placar_divergente_e_reportado(self):
        p = _votacao(sim=5, nao=1, votos=[_voto(1, "Sim"), _voto(2, "Não")])
        viol = _reconciliar_placar(p)
        self.assertIsNotNone(viol)
        self.assertIn("sim", viol)


class TestRodada(unittest.TestCase):
    def test_aberta_resolve_nominais_por_lookup(self):
        cli = ClienteFake([_votacao(votos=[
            _voto(10, "Sim"), _voto(20, "Não"), _voto(30, "AP")])])
        # lookup resolve só os senadores 10 e 20 (30 não ingerido)
        lookup = lambda s, i: f"P-{i}" if (s == "senado" and i in ("10", "20", "30")) else None
        r = rodada_votacoes_senado(cli, data_inicio="2024-12-01", data_fim="2024-12-31",
                                   canario_validado=True, linha_base=None, lookup=lookup)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.votacoes_prata.aprovados), 1)
        nominais = r.nominais["6883"]
        # 3 votos, todos resolvem (10 sim, 20 nao, 30 ausente)
        self.assertEqual(len(nominais), 3)
        self.assertEqual({n.voto for n in nominais}, {"sim", "nao", "ausente"})

    def test_secreta_nao_gera_nominal(self):
        cli = ClienteFake([_votacao(secreta="S", sim=0, nao=0,
                                    votos=[_voto(10, "Votou"), _voto(20, "Votou")])])
        r = rodada_votacoes_senado(cli, data_inicio="2024-12-01", data_fim="2024-12-31",
                                   canario_validado=True, linha_base=None,
                                   lookup=lambda s, i: f"P-{i}")
        self.assertEqual(r.nominais["6883"], [])           # §10: sem nominal
        self.assertTrue(r.votacoes_prata.aprovados[0]["secreta"])

    def test_janela_vazia_e_ok(self):
        r = rodada_votacoes_senado(ClienteFake([]), data_inicio="2024-01-01",
                                   data_fim="2024-01-02", canario_validado=True,
                                   linha_base=None, lookup=lambda s, i: None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(r.votacoes_prata.aprovados, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
