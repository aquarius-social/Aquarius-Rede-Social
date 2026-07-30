"""Testes do coletor de histórico de mandatos → vinculo_temporal (§12 D4, §4).

O coração é `construir_vinculos`: converter snapshots pontuais do histórico em
intervalos de vigência não sobrepostos, resolvendo partido/UF/ocupação na data
do fato.
"""

import unittest
from typing import Any

from camara.mandatos import (
    conferir_sem_sobreposicao,
    construir_vinculos,
    rodada_historico,
    _ocupacao,
)
from contrato.canario import EstadoContrato


class _Resp:
    def __init__(self, status: int, corpo: Any):
        self.status = status
        self.corpo = corpo
    def texto(self) -> str:
        return str(self.corpo)


class ClienteFake:
    def __init__(self, por_url: dict[str, list[Any]]):
        self.por_url = {k: list(v) for k, v in por_url.items()}
    def get(self, url: str, params: dict | None = None) -> _Resp:
        fila = self.por_url.get(url)
        if fila is None:
            raise AssertionError(f"sem resposta programada para {url}")
        return fila.pop(0)


def _snap(dh, partido, uf, cond, sit, leg=55):
    return {"id": 62881, "dataHora": dh, "idLegislatura": leg,
            "siglaPartido": partido, "siglaUf": uf,
            "condicaoEleitoral": cond, "situacao": sit,
            "descricaoStatus": "x"}


# =============================================================================
# Mapeamento de ocupação
# =============================================================================

class TestOcupacao(unittest.TestCase):
    def test_titular_em_exercicio(self):
        self.assertEqual(_ocupacao("Titular", "Exercício"), "titular")

    def test_efetivado_conta_como_titular(self):
        self.assertEqual(_ocupacao("Efetivado", "Exercício"), "titular")

    def test_suplente_convocado_e_suplente_em_exercicio(self):
        self.assertEqual(_ocupacao("Suplente", "Convocado"), "suplente_em_exercicio")

    def test_licenciado(self):
        self.assertEqual(_ocupacao("Titular", "Licenciado"), "licenciado")

    def test_fim_de_mandato_nao_e_ocupacao(self):
        self.assertIsNone(_ocupacao("Titular", "Fim de Mandato"))

    def test_borda_sem_situacao_nao_e_ocupacao(self):
        self.assertIsNone(_ocupacao(None, None))


# =============================================================================
# Construção de vínculos — snapshots → intervalos
# =============================================================================

class TestConstruirVinculos(unittest.TestCase):
    def test_troca_de_partido_gera_periodos_encadeados(self):
        hist = [
            _snap("2015-02-01T10:00", "PMDB", "CE", "Titular", "Exercício"),
            _snap("2015-09-24T16:26", "PSB", "CE", "Titular", "Exercício"),
            _snap("2017-11-07T16:49", "S.PART.", "CE", "Titular", "Exercício"),
        ]
        r = construir_vinculos(hist, "62881")
        self.assertEqual(len(r.aprovados), 3)
        self.assertEqual(
            [(v["partido_sigla_fonte"], v["vigencia_inicio"], v["vigencia_fim"])
             for v in r.aprovados],
            [("PMDB", "2015-02-01", "2015-09-24"),
             ("PSB", "2015-09-24", "2017-11-07"),
             ("S.PART.", "2017-11-07", None)],  # último em aberto
        )
        self.assertEqual(conferir_sem_sobreposicao(r.aprovados), [])

    def test_marcador_de_borda_de_duracao_nula_e_descartado(self):
        """'Nome no início' e a posse no mesmo dia → período de duração nula."""
        hist = [
            _snap("2015-02-01T00:00", "PMDB", "CE", None, None),      # borda
            _snap("2015-02-01T10:00", "PMDB", "CE", "Titular", "Exercício"),
        ]
        r = construir_vinculos(hist, "62881")
        # a borda não é ocupação; a posse fica em aberto (é o último)
        self.assertEqual(len(r.aprovados), 1)
        self.assertEqual(r.aprovados[0]["vigencia_inicio"], "2015-02-01")

    def test_snapshot_sem_data_vai_para_quarentena(self):
        hist = [
            _snap("2015-02-01T10:00", "PMDB", "CE", "Titular", "Exercício"),
            {"id": 62881, "siglaPartido": "PSB", "siglaUf": "CE",
             "condicaoEleitoral": "Titular", "situacao": "Exercício"},  # sem dataHora
        ]
        r = construir_vinculos(hist, "62881")
        self.assertEqual(len(r.quarentena), 1)
        _, v = r.quarentena[0]
        self.assertEqual(v.dimensao, "completude")

    def test_suplente_em_exercicio_vai_para_quarentena(self):
        """Sem resolver o titular da cadeira (§6.4), a constraint recusaria —
        quarentena honesta em vez de dado errado."""
        hist = [
            _snap("2019-05-01T10:00", "PT", "SP", "Suplente", "Convocado"),
            _snap("2019-08-01T10:00", "PT", "SP", "Titular", "Fim de Mandato"),
        ]
        r = construir_vinculos(hist, "999")
        self.assertEqual(r.aprovados, [])
        self.assertEqual(len(r.quarentena), 1)
        _, v = r.quarentena[0]
        self.assertEqual(v.dimensao, "integridade_referencial")

    def test_funde_periodos_consecutivos_identicos(self):
        """Dois snapshots seguidos com mesmo (uf, partido, ocupação) viram um
        período só — não dois adjacentes."""
        hist = [
            _snap("2015-02-01T10:00", "PMDB", "CE", "Titular", "Exercício"),
            _snap("2015-03-01T10:00", "PMDB", "CE", "Efetivado", "Exercício"),  # mesma ocup
            _snap("2016-01-01T10:00", "PSB", "CE", "Titular", "Exercício"),
        ]
        r = construir_vinculos(hist, "62881")
        self.assertEqual(len(r.aprovados), 2)  # PMDB fundido, depois PSB
        self.assertEqual(r.aprovados[0]["partido_sigla_fonte"], "PMDB")
        self.assertEqual(r.aprovados[0]["vigencia_inicio"], "2015-02-01")
        self.assertEqual(r.aprovados[0]["vigencia_fim"], "2016-01-01")


class TestSemSobreposicao(unittest.TestCase):
    def test_sobreposicao_injetada_e_detectada(self):
        vinc = [
            {"vigencia_inicio": "2015-01-01", "vigencia_fim": "2015-12-31"},
            {"vigencia_inicio": "2015-06-01", "vigencia_fim": "2016-01-01"},  # invade
        ]
        self.assertEqual(len(conferir_sem_sobreposicao(vinc)), 1)


# =============================================================================
# Rodada
# =============================================================================

class TestRodadaHistorico(unittest.TestCase):
    _URL = "https://dadosabertos.camara.leg.br/api/v2/deputados/62881/historico"

    def test_rodada_feliz(self):
        cliente = ClienteFake({self._URL: [_Resp(200, {"dados": [
            _snap("2015-02-01T10:00", "PMDB", "CE", "Titular", "Exercício"),
            _snap("2015-09-24T16:26", "PSB", "CE", "Titular", "Exercício"),
        ]})]})
        r = rodada_historico(cliente, "62881", canario_validado=True,
                             linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.vinculos.aprovados), 2)
        self.assertEqual(r.sobreposicao_violacoes, [])

    def test_falha_na_fonte_nao_constroi_vinculos(self):
        cliente = ClienteFake({self._URL: [_Resp(404, "not found")]})
        r = rodada_historico(cliente, "62881", canario_validado=True,
                             linha_base=None)
        self.assertIs(r.estado, EstadoContrato.FALHA)
        self.assertIsNone(r.vinculos)


if __name__ == "__main__":
    unittest.main(verbosity=2)
