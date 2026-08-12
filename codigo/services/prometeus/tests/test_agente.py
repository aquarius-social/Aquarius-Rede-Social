"""Suíte do agente ReAct — o loop, o gating e a acumulação de fontes/ressalvas,
com um modelo FAKE roteirizado. Sem rede, sem chave.
"""
import unittest

from agente import Agente
from modelo import ChamadaFerramenta, RespostaModelo
from tests.fake_gateway import FakeGateway
from tests.test_consultas import DADOS


class ModeloFake:
    """Modelo roteirizado: devolve as respostas na ordem dada."""

    def __init__(self, respostas):
        self._fila = list(respostas)
        self.rodadas = 0

    def conversar(self, *, system, mensagens, ferramentas):
        self.rodadas += 1
        return self._fila.pop(0)


def gw() -> FakeGateway:
    return FakeGateway(DADOS)


class TestAgente(unittest.TestCase):
    def test_loop_chama_ferramenta_e_cita_fonte(self):
        modelo = ModeloFake([
            RespostaModelo(
                chamadas=[ChamadaFerramenta("t1", "despesas_parlamentar",
                                            {"perfil_id": "p1", "ano": 2024, "mes": 3})],
                parou_por="tool_use",
            ),
            RespostaModelo(texto="Em março de 2024, houve 2 lançamentos de cota.", parou_por="end_turn"),
        ])
        r = Agente(modelo, gw()).responder("gastos de p1 em março de 2024?")
        self.assertFalse(r.recusada)
        self.assertIn("março", r.resposta.lower())
        self.assertTrue(r.fontes)  # regra 1: resposta veio com fonte
        self.assertIn("despesas_parlamentar", r.ferramentas_usadas)

    def test_repassa_ressalva_da_ferramenta(self):
        modelo = ModeloFake([
            RespostaModelo(
                chamadas=[ChamadaFerramenta("t1", "emendas_por_autor_nome", {"nome": "Fulano"})],
                parou_por="tool_use",
            ),
            RespostaModelo(texto="Encontrei 1 emenda.", parou_por="end_turn"),
        ])
        r = Agente(modelo, gw()).responder("emendas do Fulano?")
        self.assertTrue(any("nome" in x.lower() and "ressalva" in x.lower() for x in r.ressalvas))

    def test_refusal_do_modelo_recusa(self):
        modelo = ModeloFake([RespostaModelo(texto="Não posso ajudar com isso.", parou_por="refusal")])
        r = Agente(modelo, gw()).responder("algo fora de escopo")
        self.assertTrue(r.recusada)

    def test_teto_de_passos_recusa(self):
        loop = RespostaModelo(
            chamadas=[ChamadaFerramenta("t", "buscar_parlamentar", {"termo": "x"})],
            parou_por="tool_use",
        )
        modelo = ModeloFake([loop] * 20)
        r = Agente(modelo, gw()).responder("pergunta que faz o modelo entrar em loop")
        self.assertTrue(r.recusada)


if __name__ == "__main__":
    unittest.main()
