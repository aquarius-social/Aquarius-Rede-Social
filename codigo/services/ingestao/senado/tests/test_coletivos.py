"""Testes dos perfis coletivos do Senado — comissões + blocos (bicameral).

Campos conferidos contra a fonte viva (2026-08-01): 222 colegiados, 6 blocos.
"""

import unittest

from contrato.canario import EstadoContrato
from senado.coletivos import (
    rodada_blocos_senado,
    rodada_comissoes_senado,
    transformar_bloco_senado,
    transformar_comissao_senado,
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


def _colegiado(cod="38", sigla="CAE", nome="Comissão de Assuntos Econômicos",
               desc="Comissão Permanente"):
    return {"Codigo": cod, "Sigla": sigla, "Nome": nome, "Publica": "S",
            "DescricaoTipoColegiado": desc, "SiglaCasa": "SF"}


def _bloco(cod="346", nome="Bloco Parlamentar Aliança", apelido="BLALIANÇA"):
    return {"CodigoBloco": cod, "NomeBloco": nome, "NomeApelido": apelido,
            "DataCriacao": "2023-03-20"}


def _colegiados(items):
    return {"ListaColegiados": {"Colegiados": {"Colegiado": items}}}


def _blocos(items):
    return {"ListaBlocoParlamentar": {"Blocos": {"Bloco": items}}}


class TestTransformacao(unittest.TestCase):
    def test_comissao_shape_slug_com_marcador_sf(self):
        p = transformar_comissao_senado(_colegiado())
        self.assertEqual(p["tipo"], "comissao")
        self.assertEqual(p["sigla"], "CAE")
        # o -sf evita colisão com comissão homônima da Câmara (ex.: CCJ)
        self.assertEqual(p["slug"], "comissao-sf-cae-38")

    def test_bloco_shape(self):
        p = transformar_bloco_senado(_bloco())
        self.assertEqual(p["tipo"], "bloco")
        self.assertEqual(p["sigla"], "BLALIANÇA")
        self.assertTrue(p["slug"].startswith("bloco-blalianca-346"))


class TestRodadaComissoes(unittest.TestCase):
    def _cliente(self, colegiados):
        return ClienteFake({
            f"{BASE}/comissao/lista/colegiados": _Resp(200, _colegiados(colegiados))})

    def test_filtra_so_comissoes(self):
        """Colegiados que NÃO são comissão (frente, grupo, mesa) ficam de fora."""
        cli = self._cliente([
            _colegiado("38", "CAE", "Comissão de Assuntos Econômicos", "Comissão Permanente"),
            _colegiado("100", "FPES", "Frente do Esporte", "Frente Parlamentar"),
            _colegiado("200", "MESA", "Mesa", "Mesa Diretora")])
        r = rodada_comissoes_senado(cli, canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 1)      # só a CAE
        self.assertEqual(r.prata.aprovados[0]["sigla"], "CAE")


class TestRodadaBlocos(unittest.TestCase):
    def test_rodada_feliz(self):
        cli = ClienteFake({
            f"{BASE}/composicao/lista/blocos": _Resp(200, _blocos([_bloco(), _bloco("347", "Bloco X", "BLX")]))})
        r = rodada_blocos_senado(cli, canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 2)
        self.assertEqual({b["tipo"] for b in r.prata.aprovados}, {"bloco"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
