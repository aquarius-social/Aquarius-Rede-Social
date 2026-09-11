"""Suíte do registro de ferramentas — despacho e esquemas, sem rede."""
import unittest

import ferramentas
from tests.fake_gateway import FakeGateway
from tests.test_consultas import DADOS


def gw() -> FakeGateway:
    return FakeGateway(DADOS)


class TestFerramentas(unittest.TestCase):
    def test_esquemas_tem_as_oito(self):
        esquemas = ferramentas.esquemas_anthropic()
        nomes = {e["name"] for e in esquemas}
        self.assertEqual(len(nomes), 8)
        self.assertIn("despesas_parlamentar", nomes)
        self.assertIn("emendas_por_autor_perfil", nomes)  # nova: atribuição por chave
        # todo esquema tem input_schema com 'required'
        for e in esquemas:
            self.assertIn("input_schema", e)
            self.assertIn("required", e["input_schema"])

    def test_executar_despesas(self):
        res = ferramentas.executar(gw(), "despesas_parlamentar", {"perfil_id": "p1", "ano": 2024, "mes": 3})
        self.assertIsNone(res["recusa"])
        self.assertEqual(len(res["dados"]), 2)
        self.assertTrue(res["proveniencia"])  # regra 1

    def test_executar_ferramenta_desconhecida(self):
        res = ferramentas.executar(gw(), "nao_existe", {})
        self.assertIsNotNone(res["recusa"])


if __name__ == "__main__":
    unittest.main()
