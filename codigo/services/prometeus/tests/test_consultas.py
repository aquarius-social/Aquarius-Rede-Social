"""Suíte das ferramentas do Prometeus — disciplina da Metodologia: cada regra tem
um caso que ACEITA e um que RECUSA. Roda sem rede (FakeGateway).

Os testes espelham os modos de falha catalogados (§21): janela temporal ausente,
ausência lida como negação, contar linhas em vez de entidades, somar estágios
incompatíveis, atribuição por nome, atributo resolvido no presente.
"""
import unittest

import consultas
from tests.fake_gateway import FakeGateway

DADOS = {
    "parlamentar_publico": [
        {
            "id": "p1", "nome": "Fulano de Tal", "slug": "fulano-de-tal",
            "partido_sigla_atual": "XYZ", "uf_atual": "SP", "casa_atual": "camara",
            "situacao": "em_exercicio", "source": "camara.deputados",
            "source_url": "https://dadosabertos.camara.leg.br/api/v2",
            "synced_at": "2026-08-10T00:00:00Z",
        },
        {
            "id": "p2", "nome": "Fulano de Tal Filho", "slug": "fulano-de-tal-filho",
            "partido_sigla_atual": "ABC", "uf_atual": "SP", "casa_atual": "camara",
            "situacao": "em_exercicio", "source": "camara.deputados",
            "source_url": "https://dadosabertos.camara.leg.br/api/v2",
            "synced_at": "2026-08-10T00:00:00Z",
        },
    ],
    "despesa_publica": [
        {"id": "d1", "perfil_id": "p1", "ano": 2024, "mes": 3, "data_documento": "2024-03-10",
         "tipo_despesa": "COMBUSTIVEIS", "valor_liquido": 500.0, "fornecedor_nome": "Posto X",
         "fornecedor_cnpj_cpf": "1", "source": "camara.despesas",
         "source_url": "https://dadosabertos.camara.leg.br/api/v2", "synced_at": "2026-08-11T00:00:00Z"},
        {"id": "d2", "perfil_id": "p1", "ano": 2024, "mes": 3, "data_documento": "2024-03-20",
         "tipo_despesa": "COMBUSTIVEIS", "valor_liquido": 300.0, "fornecedor_nome": "Posto X",
         "fornecedor_cnpj_cpf": "1", "source": "camara.despesas",
         "source_url": "https://dadosabertos.camara.leg.br/api/v2", "synced_at": "2026-08-11T00:00:00Z"},
        {"id": "d3", "perfil_id": "p1", "ano": 2024, "mes": 4, "data_documento": "2024-04-05",
         "tipo_despesa": "PASSAGENS", "valor_liquido": 1200.0, "fornecedor_nome": "Cia Aerea",
         "fornecedor_cnpj_cpf": "2", "source": "camara.despesas",
         "source_url": "https://dadosabertos.camara.leg.br/api/v2", "synced_at": "2026-08-11T00:00:00Z"},
    ],
    "emenda_publica": [
        {"id": "e1", "autor_nome": "Fulano de Tal", "ano": 2024, "localidade_gasto": "Campinas - SP",
         "funcao": "Saude", "valor_empenhado": 1000000.0, "valor_liquidado": 600000.0,
         "valor_pago": 500000.0, "valor_resto_inscrito": 0.0, "valor_resto_cancelado": 0.0,
         "valor_resto_pago": 0.0, "autor_profile_id": None, "source": "transparencia.emendas",
         "source_url": "https://api.portaldatransparencia.gov.br/api-de-dados",
         "synced_at": "2026-08-11T00:00:00Z"},
    ],
    "evento_publico": [
        {"id": "ev1", "casa": "camara", "tipo": "Audiencia", "titulo": "Debate X",
         "data_hora_inicio": "2024-05-10T14:00:00", "situacao": "Realizada", "orgao_sigla": "CFT",
         "source": "camara.eventos", "source_url": "https://dadosabertos.camara.leg.br/api/v2",
         "synced_at": "2026-08-11T00:00:00Z"},
        {"id": "ev2", "casa": "senado", "tipo": "Reuniao", "titulo": "Reuniao Y",
         "data_hora_inicio": "2024-05-20T10:00:00", "situacao": "Agendada", "orgao_sigla": "CAE",
         "source": "senado.eventos", "source_url": "https://legis.senado.leg.br/dadosabertos",
         "synced_at": "2026-08-11T00:00:00Z"},
    ],
}


def gw() -> FakeGateway:
    return FakeGateway(DADOS)


class TestBuscarParlamentar(unittest.TestCase):
    def test_aceita_por_nome(self):
        r = consultas.buscar_parlamentar(gw(), termo="Fulano")
        self.assertIsNone(r.recusa)
        self.assertEqual(len(r.dados), 2)
        self.assertTrue(r.proveniencia)  # regra 1: nada sem fonte
        self.assertTrue(any("hoje" in x.lower() for x in r.ressalvas))  # partido é o de hoje

    def test_recusa_termo_vazio(self):
        self.assertIsNotNone(consultas.buscar_parlamentar(gw(), termo="   ").recusa)


class TestDespesas(unittest.TestCase):
    def test_aceita_com_ano(self):
        r = consultas.despesas_parlamentar(gw(), perfil_id="p1", ano=2024, mes=3)
        self.assertIsNone(r.recusa)
        self.assertEqual(len(r.dados), 2)
        self.assertEqual(r.completude.ultimo_registro_em, "2024-03-20")
        self.assertTrue(r.proveniencia)

    def test_recusa_sem_ano(self):  # modo de falha: janela temporal ausente
        self.assertIsNotNone(consultas.despesas_parlamentar(gw(), perfil_id="p1", ano=None).recusa)

    def test_recusa_sem_perfil(self):
        self.assertIsNotNone(consultas.despesas_parlamentar(gw(), perfil_id="", ano=2024).recusa)

    def test_ausencia_nao_e_inexistencia(self):  # regra 3 / modo de falha 8
        r = consultas.despesas_parlamentar(gw(), perfil_id="p1", ano=2020)
        self.assertIsNone(r.recusa)
        self.assertEqual(r.dados, [])
        self.assertTrue(any("ausência" in x.lower() or "defasagem" in x.lower() for x in r.ressalvas))

    def test_total_conta_entidades(self):  # modo de falha 3: contar linhas != entidades
        r = consultas.total_despesas(gw(), perfil_id="p1", ano=2024)
        self.assertEqual(r.dados["total_liquido"], 2000.0)
        self.assertEqual(r.dados["n_lancamentos"], 3)
        self.assertEqual(r.dados["n_fornecedores_distintos"], 2)

    def test_total_por_categoria(self):
        r = consultas.total_despesas(gw(), perfil_id="p1", ano=2024, por="categoria")
        self.assertEqual(r.dados["por_categoria"]["COMBUSTIVEIS"], 800.0)
        self.assertEqual(r.dados["por_categoria"]["PASSAGENS"], 1200.0)


class TestEmendas(unittest.TestCase):
    def test_por_municipio_nao_soma_estagios(self):  # regra 5 / modo de falha 7
        r = consultas.emendas_por_municipio(gw(), municipio="Campinas")
        tot = r.dados["totais_por_estagio"]
        self.assertEqual(tot["valor_empenhado"], 1000000.0)
        self.assertEqual(tot["valor_pago"], 500000.0)
        self.assertNotIn("total", tot)  # não existe soma única entre estágios
        self.assertTrue(any("estágio" in x.lower() or "estagio" in x.lower() for x in r.ressalvas))

    def test_por_autor_nome_declara_ressalva(self):  # regra 2 / modo de falha 9
        r = consultas.emendas_por_autor_nome(gw(), nome="Fulano")
        self.assertIsNone(r.recusa)
        self.assertEqual(len(r.dados["emendas"]), 1)
        self.assertTrue(any("nome" in x.lower() and "ressalva" in x.lower() for x in r.ressalvas))

    def test_recusa_sem_municipio(self):
        self.assertIsNotNone(consultas.emendas_por_municipio(gw(), municipio="").recusa)


class TestEventos(unittest.TestCase):
    def test_agenda_intervalo(self):
        r = consultas.agenda_eventos(gw(), data_inicio="2024-05-01", data_fim="2024-05-15")
        self.assertEqual(len(r.dados), 1)
        self.assertEqual(r.dados[0]["id"], "ev1")

    def test_recusa_sem_intervalo(self):
        self.assertIsNotNone(consultas.agenda_eventos(gw(), data_inicio="2024-05-01", data_fim="").recusa)

    def test_filtra_por_casa(self):
        r = consultas.agenda_eventos(gw(), data_inicio="2024-05-01", data_fim="2024-05-31", casa="senado")
        self.assertEqual(len(r.dados), 1)
        self.assertEqual(r.dados[0]["casa"], "senado")


if __name__ == "__main__":
    unittest.main()
