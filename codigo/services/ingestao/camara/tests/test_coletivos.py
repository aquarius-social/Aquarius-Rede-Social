"""Testes dos coletores de perfis coletivos — comissões e frentes."""

import unittest
from typing import Any

from camara.coletivos import (
    processar_comissoes_para_prata,
    processar_frentes_para_prata,
    rodada_comissoes,
    rodada_frentes,
    transformar_comissao,
    transformar_frente,
)
from contrato.canario import EstadoContrato
from pipeline.camadas import RegistroBronze


class _Resp:
    def __init__(self, status, corpo):
        self.status = status
        self.corpo = corpo
    def texto(self):
        return str(self.corpo)


class ClienteFake:
    def __init__(self, por_url):
        self.por_url = {k: list(v) for k, v in por_url.items()}
    def get(self, url, params=None):
        fila = self.por_url.get(url)
        if fila is None:
            raise AssertionError(f"sem resposta para {url}")
        return fila.pop(0)


def _orgao(oid=2003, sigla="CCJC",
           nome="Comissão de Constituição e Justiça e de Cidadania"):
    return {"id": oid, "sigla": sigla, "nome": nome, "codTipoOrgao": 2, "uri": "u"}


def _frente(fid=55703, titulo="Frente Parlamentar Mista do Serviço Exterior"):
    return {"id": fid, "titulo": titulo, "idLegislatura": 57, "uri": "u"}


def _bronze(fonte, payload):
    return RegistroBronze.de(fonte, "https://x", payload)


class TestComissao(unittest.TestCase):
    def test_transform(self):
        p = transformar_comissao(_orgao())
        self.assertEqual(p["tipo"], "comissao")
        self.assertEqual(p["sigla"], "CCJC")
        self.assertEqual(p["slug"], "comissao-ccjc-2003")

    def test_portao_valido_passa(self):
        r = processar_comissoes_para_prata([_bronze("camara.orgaos", _orgao())])
        self.assertEqual(len(r.aprovados), 1)

    def test_sem_sigla_vai_para_quarentena(self):
        o = _orgao()
        del o["sigla"]
        r = processar_comissoes_para_prata([_bronze("camara.orgaos", o)])
        self.assertEqual(r.aprovados, [])
        self.assertEqual(r.quarentena[0][1].dimensao, "completude")

    def test_rodada_feliz(self):
        cli = ClienteFake({
            "https://dadosabertos.camara.leg.br/api/v2/orgaos":
                [_Resp(200, {"dados": [_orgao(2003, "CCJC"), _orgao(2004, "CFT",
                                              "Comissão de Finanças e Tributação")],
                             "links": []})]})
        r = rodada_comissoes(cli, canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 2)

    def test_falha(self):
        cli = ClienteFake({
            "https://dadosabertos.camara.leg.br/api/v2/orgaos":
                [_Resp(404, "x")]})
        r = rodada_comissoes(cli, canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.FALHA)
        self.assertIsNone(r.prata)


class TestFrente(unittest.TestCase):
    def test_transform(self):
        p = transformar_frente(_frente())
        self.assertEqual(p["tipo"], "frente")
        self.assertEqual(p["nome"], "Frente Parlamentar Mista do Serviço Exterior")
        self.assertIsNone(p["sigla"])
        self.assertTrue(p["slug"].startswith("frente-"))
        self.assertTrue(p["slug"].endswith("-55703"))

    def test_portao_sem_titulo_vai_para_quarentena(self):
        f = _frente()
        del f["titulo"]
        r = processar_frentes_para_prata([_bronze("camara.frentes", f)])
        self.assertEqual(r.aprovados, [])
        self.assertEqual(r.quarentena[0][1].dimensao, "completude")

    def test_rodada_feliz(self):
        cli = ClienteFake({
            "https://dadosabertos.camara.leg.br/api/v2/frentes":
                [_Resp(200, {"dados": [_frente(55703), _frente(55685, "Frente da Saúde")],
                             "links": []})]})
        r = rodada_frentes(cli, canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
