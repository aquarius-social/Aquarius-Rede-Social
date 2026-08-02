"""Testes do coletor de CEAPS do Senado (Área A, bicameral).

Formato conferido contra a fonte viva (2026-08-01): CSV ISO-8859-1, `;`,
colunas ANO;MES;SENADOR;TIPO_DESPESA;CNPJ_CPF;FORNECEDOR;DOCUMENTO;DATA;
DETALHAMENTO;VALOR_REEMBOLSADO;COD_DOCUMENTO. Inclui um campo com quebra de linha
DENTRO das aspas, para provar que o parse não quebra por linha física.
"""

import unittest

from contrato.canario import EstadoContrato
from pipeline.camadas import RegistroBronze
from senado.despesas import (
    _data_br,
    _linhas_csv,
    _valor,
    processar_ceaps_para_prata,
    rodada_ceaps,
    transformar_despesa_senado,
)

# CSV de exemplo — a 2ª linha de dados tem DETALHAMENTO multi-linha (aspas).
CSV = (
    '"ULTIMA ATUALIZACAO";"01/08/2026 02:02"\n'
    '"ANO";"MES";"SENADOR";"TIPO_DESPESA";"CNPJ_CPF";"FORNECEDOR";"DOCUMENTO";'
    '"DATA";"DETALHAMENTO";"VALOR_REEMBOLSADO";"COD_DOCUMENTO"\n'
    '"2024";"1";"ALAN RICK";"Aluguel";"66.970.229/0132-26";"CLARO";"470160";'
    '"17/01/2024";"";"583,58";"2221244"\n'
    '"2024";"2";"ALAN RICK";"Passagens";"";"TAM";"01";"05/02/2024";'
    '"detalhe linha 1\nlinha 2";"1.234,56";"2221260"\n'
)


class TestParsers(unittest.TestCase):
    def test_valor_br(self):
        self.assertEqual(_valor("583,58"), 583.58)
        self.assertEqual(_valor("1.234,56"), 1234.56)
        self.assertIsNone(_valor(""))

    def test_data_br(self):
        self.assertEqual(_data_br("17/01/2024"), "2024-01-17")
        self.assertEqual(_data_br("5/2/2024"), "2024-02-05")
        self.assertIsNone(_data_br(""))

    def test_csv_com_quebra_dentro_de_aspas(self):
        linhas = _linhas_csv(CSV)
        self.assertEqual(len(linhas), 2)   # 2 registros, não 3 (a quebra é interna)
        self.assertEqual(linhas[0]["SENADOR"], "ALAN RICK")
        self.assertEqual(linhas[1]["COD_DOCUMENTO"], "2221260")


class TestTransformacao(unittest.TestCase):
    def test_shape(self):
        linhas = _linhas_csv(CSV)
        d = transformar_despesa_senado(linhas[0])
        self.assertEqual(d["senador_nome"], "ALAN RICK")
        self.assertEqual(d["ano"], 2024)
        self.assertEqual(d["mes"], 1)
        self.assertEqual(d["valor_documento"], 583.58)
        self.assertEqual(d["valor_liquido"], 583.58)
        self.assertIsNone(d["valor_glosa"])           # Senado não tem glosa
        self.assertEqual(d["parcela"], 0)             # chave de dedup efetiva
        self.assertEqual(d["cod_documento"], 2221244)
        self.assertEqual(d["data_documento"], "2024-01-17")


class TestPortao(unittest.TestCase):
    def _bronze(self, row):
        return RegistroBronze.de("senado.ceaps", "u", row)

    def test_valido_passa(self):
        r = processar_ceaps_para_prata([self._bronze(_linhas_csv(CSV)[0])])
        self.assertEqual(len(r.aprovados), 1)

    def test_sem_cod_documento_vai_para_quarentena(self):
        row = dict(_linhas_csv(CSV)[0]); row["COD_DOCUMENTO"] = ""
        r = processar_ceaps_para_prata([self._bronze(row)])
        self.assertEqual(r.aprovados, [])


class TestRodada(unittest.TestCase):
    def test_rodada_feliz(self):
        r = rodada_ceaps(lambda url: CSV, 2024,
                         canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 2)

    def test_falha_de_rede_vira_instabilidade(self):
        def _erro(url):
            raise OSError("timeout")
        r = rodada_ceaps(_erro, 2024, canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.INSTABILIDADE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
