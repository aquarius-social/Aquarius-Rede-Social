"""Testes do coletor de senadores (Área I).

Campos e formato batem com a fonte viva (senador/lista/atual + senador/{cod},
verificado em 2026-07-31). O caso-fixture é o Alan Rick, que aparece no gold set
bicameral (senado_cod 5672 ↔ camara_id 178836).
"""

import unittest

from contrato.canario import EstadoContrato
from pipeline.camadas import RegistroBronze
from senado.senadores import (
    processar_senadores_para_prata,
    rodada_senadores,
    transformar_senador,
    _ocupacao,
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


def _item(cod="5672", nome="Alan Rick", civil="Alan Rick Miranda",
          partido="REPUBLICANOS", uf="AC", participacao="Titular"):
    return {
        "IdentificacaoParlamentar": {
            "CodigoParlamentar": cod, "NomeParlamentar": nome,
            "NomeCompletoParlamentar": civil, "SexoParlamentar": "Masculino",
            "SiglaPartidoParlamentar": partido, "UfParlamentar": uf,
            "UrlFotoParlamentar": f"http://x/senador{cod}.jpg",
        },
        "Mandato": {
            "PrimeiraLegislaturaDoMandato": {
                "NumeroLegislatura": "57", "DataInicio": "2023-02-01",
                "DataFim": "2027-01-31"},
            "SegundaLegislaturaDoMandato": {
                "NumeroLegislatura": "58", "DataInicio": "2027-02-01",
                "DataFim": "2031-01-31"},
            "DescricaoParticipacao": participacao,
        },
    }


def _det_parlamentar(nasc="1976-10-23", mun="Rio Branco", uf="AC"):
    return {"DadosBasicosParlamentar": {
        "DataNascimento": nasc, "Naturalidade": mun, "UfNaturalidade": uf}}


def _bronze(item):
    return RegistroBronze.de("senado.senadores", "u", item)


class TestOcupacao(unittest.TestCase):
    def test_titular_e_suplente(self):
        self.assertEqual(_ocupacao("Titular"), "titular")
        self.assertEqual(_ocupacao("1º Suplente"), "suplente_em_exercicio")
        self.assertEqual(_ocupacao(None), "titular")


class TestTransformacao(unittest.TestCase):
    def test_shape_completo_com_detalhe(self):
        p = transformar_senador(_item(), _det_parlamentar())
        self.assertEqual(p["id_fonte"], "5672")
        self.assertEqual(p["nome"], "Alan Rick")
        self.assertEqual(p["nome_civil"], "Alan Rick Miranda")   # PII, §5.3
        self.assertTrue(p["slug"].startswith("alan-rick-sen-5672"))
        self.assertEqual(p["data_nascimento"], "1976-10-23")
        self.assertEqual(p["naturalidade_municipio"], "Rio Branco")
        self.assertEqual(p["naturalidade_uf"], "AC")
        self.assertEqual(p["sistema_externo"], "senado")
        self.assertEqual(p["metodo_ligacao"], "fonte_direta")

    def test_mandato_hint_cobre_as_duas_legislaturas(self):
        p = transformar_senador(_item())
        h = p["mandato_hint"]
        self.assertEqual(h["casa"], "senado")
        self.assertEqual(h["uf"], "AC")
        self.assertEqual(h["partido"], "REPUBLICANOS")
        self.assertEqual(h["legislatura"], 57)
        self.assertEqual(h["vigencia_inicio"], "2023-02-01")
        # fim vem da SEGUNDA legislatura (mandato de 8 anos)
        self.assertEqual(h["vigencia_fim"], "2031-01-31")
        self.assertEqual(h["ocupacao"], "titular")

    def test_sem_detalhe_fica_sem_nascimento(self):
        p = transformar_senador(_item())
        self.assertIsNone(p["data_nascimento"])
        self.assertIsNone(p["naturalidade_municipio"])
        self.assertEqual(p["nome_civil"], "Alan Rick Miranda")  # esse vem da lista


class TestPortao(unittest.TestCase):
    def test_valido_passa(self):
        r = processar_senadores_para_prata([_bronze(_item())])
        self.assertEqual(len(r.aprovados), 1)

    def test_sem_codigo_vai_para_quarentena(self):
        item = _item()
        del item["IdentificacaoParlamentar"]["CodigoParlamentar"]
        r = processar_senadores_para_prata([_bronze(item)])
        self.assertEqual(r.aprovados, [])
        self.assertEqual(r.quarentena[0][1].dimensao, "completude")


class TestRodada(unittest.TestCase):
    def _cliente(self, participacao="Titular"):
        return ClienteFake({
            f"{BASE}/senador/lista/atual": _Resp(200, {
                "ListaParlamentarEmExercicio": {"Parlamentares": {
                    "Parlamentar": [_item(participacao=participacao)]}}}),
            f"{BASE}/senador/5672": _Resp(200, {
                "DetalheParlamentar": {"Parlamentar": {
                    "IdentificacaoParlamentar": {"CodigoParlamentar": "5672"},
                    **_det_parlamentar()}}}),
        })

    def test_rodada_feliz_enriquece_com_nascimento(self):
        r = rodada_senadores(self._cliente(), canario_validado=True,
                             linha_base=None, enriquecer=True)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 1)
        self.assertEqual(r.prata.aprovados[0]["data_nascimento"], "1976-10-23")

    def test_canario_nao_validado_vira_falha(self):
        r = rodada_senadores(self._cliente(), canario_validado=False,
                             linha_base=None)
        self.assertIs(r.estado, EstadoContrato.FALHA)
        self.assertIsNone(r.prata)


def _roster_item(cod, nome, civil=None):
    return {"IdentificacaoParlamentar": {
        "CodigoParlamentar": cod, "NomeParlamentar": nome,
        "NomeCompletoParlamentar": civil or (nome + " Completo"),
        "SexoParlamentar": "Masculino"},
        "Mandatos": {"Mandato": [{"UfParlamentar": "PE",
                                  "DescricaoParticipacao": "2º Suplente"}]}}


class TestRosterLegislatura(unittest.TestCase):
    def _cliente(self):
        # roster com 2 senadores; só o 100 está em exercício
        return ClienteFake({
            f"{BASE}/senador/lista/legislatura/57": _Resp(200, {
                "ListaParlamentarLegislatura": {"Parlamentares": {"Parlamentar": [
                    _roster_item("100", "Fulano Ativo"),
                    _roster_item("200", "Beltrano Licenciado")]}}}),
            f"{BASE}/senador/lista/atual": _Resp(200, {
                "ListaParlamentarEmExercicio": {"Parlamentares": {"Parlamentar": [
                    _roster_item("100", "Fulano Ativo")]}}}),
        })

    def test_roster_marca_ativo_pela_lista_em_exercicio(self):
        r = rodada_senadores(self._cliente(), canario_validado=True,
                             linha_base=None, enriquecer=False, legislatura=57)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 2)     # roster completo
        por_cod = {s["id_fonte"]: s for s in r.prata.aprovados}
        self.assertTrue(por_cod["100"]["ativo"])         # em exercício
        self.assertFalse(por_cod["200"]["ativo"])        # licenciado/suplente
        # nome civil vem da própria lista do roster (sem detalhe)
        self.assertEqual(por_cod["200"]["nome_civil"], "Beltrano Licenciado Completo")


if __name__ == "__main__":
    unittest.main(verbosity=2)
