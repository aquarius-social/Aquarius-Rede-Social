"""Testes do coletor de eventos do Senado (agenda de comissões, bicameral).

Campos conferidos contra a fonte viva (2026-08-02). Mesma prata que a Câmara.
"""

import unittest

from contrato.canario import EstadoContrato
from pipeline.camadas import RegistroBronze
from senado.eventos import (
    _aaaammm,
    processar_eventos_senado_para_prata,
    rodada_eventos_senado,
    transformar_evento_senado,
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


def _reuniao(codigo="14883", titulo="56ª Reunião Extraordinária",
             ini="2026-08-06T10:00:00.000", sigla="CDH", cod_col="834"):
    return {"codigo": codigo, "titulo": titulo, "descricao": "56ª, Extraordinária",
            "dataInicio": ini, "situacao": "Agendada", "local": "Anexo II, Plenário 6",
            "colegiadoCriador": {"codigo": cod_col, "sigla": sigla,
                                 "nome": "Comissão de Direitos Humanos",
                                 "descricaoTipo": "Comissão Permanente"}}


def _wrap(reunioes):
    return {"AgendaReuniao": {"reunioes": {"reuniao": reunioes}}}


class TestFormatoMes(unittest.TestCase):
    def test_iso_vira_aaaamm(self):
        self.assertEqual(_aaaammm("2026-08"), "202608")
        self.assertEqual(_aaaammm("202608"), "202608")


class TestTransformacao(unittest.TestCase):
    def test_shape_e_slug_sf(self):
        p = transformar_evento_senado(_reuniao())
        self.assertEqual(p["casa"], "senado")
        self.assertEqual(p["id_fonte"], "14883")
        self.assertEqual(p["tipo"], "Comissão Permanente")
        self.assertEqual(p["orgao_sigla"], "CDH")
        # slug reconstruído bate com o de senado/coletivos.py (prefixo -sf)
        self.assertEqual(p["orgao_slug"], "comissao-sf-cdh-834")
        self.assertEqual(p["situacao"], "Agendada")


class TestPortao(unittest.TestCase):
    def test_valido_passa(self):
        r = processar_eventos_senado_para_prata(
            [RegistroBronze.de("senado.eventos", "u", _reuniao())])
        self.assertEqual(len(r.aprovados), 1)


class TestRodada(unittest.TestCase):
    def test_rodada_feliz(self):
        cli = ClienteFake({
            f"{BASE}/comissao/agenda/mes/202608": _Resp(200, _wrap([_reuniao(),
                _reuniao(codigo="14871", sigla="CRE", cod_col="54")]))})
        r = rodada_eventos_senado(cli, "202608", canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 2)

    def test_mes_vazio_e_ok(self):
        cli = ClienteFake({
            f"{BASE}/comissao/agenda/mes/202601": _Resp(200, _wrap([]))})
        r = rodada_eventos_senado(cli, "202601", canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(r.prata.aprovados, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
