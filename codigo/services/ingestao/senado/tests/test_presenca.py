"""Testes da presença do Senado (derivada do comparecimento em votações)."""
import unittest
from typing import Any

from senado.presenca import rodada_presenca_senado, _esta_presente


class _Resp:
    def __init__(self, status: int, corpo: Any):
        self.status = status
        self.corpo = corpo
    def texto(self) -> str:
        return str(self.corpo)


class _Cliente:
    def __init__(self, votacoes):
        self._v = votacoes
    def get(self, url: str, params: dict | None = None) -> _Resp:
        return _Resp(200, self._v)


def _votacao(cod_sessao, data, votos, casa="SF", tipo="DOR"):
    return {"codigoSessao": cod_sessao, "dataSessao": data, "casaSessao": casa,
            "siglaTipoSessao": tipo,
            "votos": {"VotoParlamentar": [
                {"codigoParlamentar": c, "siglaVotoParlamentar": s} for c, s in votos]}}


class TestClassificacao(unittest.TestCase):
    def test_presente_vs_ausente(self):
        for s in ("Sim", "Não", "Abstenção", "VO", "PSF", "P-NRV", "OB",
                  "Presidente (art. 51 RISF)"):
            self.assertTrue(_esta_presente(s), s)
        for s in ("AP", "MIS", "LS", "AUS", "NCom", "AFO", "", None, "NR"):
            self.assertFalse(_esta_presente(s), s)


class TestRodada(unittest.TestCase):
    def test_agrega_por_sessao_presente_em_uma_votacao_conta(self):
        # sessão 100, 2 votações: senador 1 presente numa, ausente na outra -> presente.
        # senador 2 ausente nas duas -> não presente. senador 3 sempre presente.
        v1 = _votacao("100", "2024-03-05", [("1", "Sim"), ("2", "MIS"), ("3", "Não")])
        v2 = _votacao("100", "2024-03-05", [("1", "AP"), ("2", "LS"), ("3", "Sim")])
        r = rodada_presenca_senado(_Cliente([v1, v2]), data_inicio="2024-03-01",
                                   data_fim="2024-03-31", canario_validado=True,
                                   linha_base=None)
        self.assertEqual(len(r.sessoes), 1)
        pres = {p["id_parlamentar"] for p in r.presencas["100"]}
        self.assertEqual(pres, {"1", "3"})            # 2 ficou de fora (ausente)

    def test_exclui_sessao_do_congresso(self):
        v = _votacao("200", "2024-03-05", [("1", "Sim")], casa="CN")
        r = rodada_presenca_senado(_Cliente([v]), data_inicio="2024-03-01",
                                   data_fim="2024-03-31", canario_validado=True,
                                   linha_base=None)
        self.assertEqual(len(r.sessoes), 0)           # CN (Congresso) fica de fora

    def test_janela_vazia_ok(self):
        r = rodada_presenca_senado(_Cliente([]), data_inicio="2024-01-01",
                                   data_fim="2024-01-02", canario_validado=True,
                                   linha_base=None)
        self.assertEqual(r.estado.value, "ok")
        self.assertEqual(len(r.sessoes), 0)


if __name__ == "__main__":
    unittest.main()
