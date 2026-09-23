"""Fatiamento da janela de data.

A API `/proposicoes` e `/votacoes` da Câmara REJEITA intervalos de data largos
(HTTP 400 — verificado ao vivo 2026-09: 1 ano dá 400, 2 meses passam). O backfill
(~1 ano) precisa fatiar a janela em pedaços curtos; o incremental (30 dias) cabe
num pedaço só. Sem isto, a coleta volta 0 em silêncio (o backfill de atividade de
2024 trouxe proposicoes=0/votos=0 antes deste conserto).
"""
import unittest
from datetime import date, timedelta
from typing import Any

from camara.proposicoes import coletar_bronze
from camara.votacoes import coletar_bronze_votacoes
from pipeline.coletor import MAX_JANELA_CAMARA_DIAS, JanelaMovel, fatiar_periodo


class _Resp:
    def __init__(self, status: int, corpo: Any):
        self.status = status
        self.corpo = corpo
    def texto(self) -> str:
        return str(self.corpo)


class _ClienteVazio:
    """Sempre responde 200 com lista vazia; grava as chamadas (url, params)."""
    def __init__(self) -> None:
        self.chamadas: list[tuple[str, Any]] = []
    def get(self, url: str, params: dict | None = None) -> _Resp:
        self.chamadas.append((url, params))
        return _Resp(200, {"dados": [], "links": []})


class TestFatiarPeriodo(unittest.TestCase):
    def test_larga_vira_varios_pedacos_sem_buraco_nem_sobreposicao(self):
        ini, fim = date(2024, 1, 1), date(2024, 12, 31)
        pedacos = fatiar_periodo(ini, fim, 60)
        self.assertGreater(len(pedacos), 1)
        for a, b in pedacos:
            self.assertLessEqual((b - a).days, 59)             # nenhum pedaço > 60 dias
        self.assertEqual(pedacos[0][0], ini)                   # começa no início
        self.assertEqual(pedacos[-1][1], fim)                  # cobre a ponta
        for (_, a1), (b0, _) in zip(pedacos, pedacos[1:]):
            self.assertEqual(b0, a1 + timedelta(days=1))       # sem buraco/sobreposição

    def test_curta_um_pedaco_so(self):
        j = (date(2024, 6, 1), date(2024, 6, 30))
        self.assertEqual(fatiar_periodo(*j, 60), [j])

    def test_fim_antes_do_inicio_vazio(self):
        self.assertEqual(fatiar_periodo(date(2024, 6, 30), date(2024, 6, 1), 60), [])


class TestColetoresFatiam(unittest.TestCase):
    def test_proposicoes_janela_larga_fatia_em_chamadas_curtas(self):
        cli = _ClienteVazio()
        coletar_bronze(cli, ate=date(2024, 12, 31), janela=JanelaMovel(dias=366))
        self.assertGreater(len(cli.chamadas), 1)               # não manda 1 janela larga (=> 400)
        for _, p in cli.chamadas:
            a = date.fromisoformat(p["dataApresentacaoInicio"])
            b = date.fromisoformat(p["dataApresentacaoFim"])
            self.assertLessEqual((b - a).days, MAX_JANELA_CAMARA_DIAS - 1)

    def test_proposicoes_incremental_uma_chamada(self):
        cli = _ClienteVazio()
        coletar_bronze(cli, ate=date(2024, 12, 31), janela=JanelaMovel(dias=30))
        self.assertEqual(len(cli.chamadas), 1)                 # 30 dias cabe num pedaço (compat)

    def test_votacoes_janela_larga_fatia_em_chamadas_curtas(self):
        cli = _ClienteVazio()
        coletar_bronze_votacoes(cli, data_inicio="2023-12-31", data_fim="2024-12-31")
        self.assertGreater(len(cli.chamadas), 1)
        for _, p in cli.chamadas:
            a = date.fromisoformat(p["dataInicio"])
            b = date.fromisoformat(p["dataFim"])
            self.assertLessEqual((b - a).days, MAX_JANELA_CAMARA_DIAS - 1)


if __name__ == "__main__":
    unittest.main()
