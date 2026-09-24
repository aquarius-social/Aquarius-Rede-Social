"""Testes do coletor de matérias do Senado (proposições, Área B bicameral).

Campos conferidos contra a fonte viva (2026-07-31, PL 2024). Produz a mesma
prata que a Câmara (casa_origem='senado') — reusa `salvar_proposicoes`.
"""

import unittest

from contrato.canario import EstadoContrato
from pipeline.camadas import RegistroBronze
from senado.materias import (
    _aaaammdd,
    extrair_enriquecimento_materia,
    processar_materias_para_prata,
    rodada_materias,
    transformar_materia,
)

BASE = "https://legis.senado.leg.br/dadosabertos"
URL = f"{BASE}/materia/pesquisa/lista"


class TestEnriquecimentoMateria(unittest.TestCase):
    def test_extrai_situacao_e_tema(self):
        det = {"DetalheMateria": {"Materia": {"DadosBasicosMateria": {
            "IndexacaoMateria": " CRIAÇÃO ,  LEI FEDERAL ;\n MILITAR "}}}}
        # Situacao aninhada (pode vir lista) — o extrator acha em qualquer nível
        sit = {"SituacaoAtualMateria": {"Materia": {"Situacao": [
            {"DescricaoSituacao": "AGUARDANDO DESIGNAÇÃO DO RELATOR"}]}}}
        e = extrair_enriquecimento_materia(det, sit)
        self.assertEqual(e["situacao"], "AGUARDANDO DESIGNAÇÃO DO RELATOR")
        self.assertEqual(e["tema"], "CRIAÇÃO , LEI FEDERAL , MILITAR")  # ; -> , e espaços colapsados

    def test_ausente_vira_none(self):  # §1
        e = extrair_enriquecimento_materia({}, {})
        self.assertEqual(e, {"situacao": None, "tema": None})


class _Resp:
    def __init__(self, status, corpo):
        self.status = status
        self.corpo = corpo
    def texto(self):
        return str(self.corpo)


class ClienteFake:
    """Fila por sigla (o coletor consulta uma vez por sigla)."""
    def __init__(self, por_sigla):
        self.por_sigla = por_sigla
        self.siglas_consultadas = []
    def get(self, url, params=None):
        sigla = (params or {}).get("sigla")
        self.siglas_consultadas.append(sigla)
        return _Resp(200, self.por_sigla.get(sigla, {}))


def _materia(cod="161856", sigla="PL", numero="00001", ano="2024",
             ementa="Altera a Lei; dispõe sobre\nalgo.", data="2024-01-02"):
    return {"Codigo": cod, "DescricaoIdentificacao": f"{sigla} {int(numero)}/{ano}",
            "Sigla": sigla, "Numero": numero, "Ano": ano, "Ementa": ementa,
            "Autor": "Senador X (PP/SE)", "Data": data,
            "UrlDetalheMateria": f"http://x/materia/{cod}"}


def _wrap(materias):
    return {"PesquisaBasicaMateria": {"Materias": {"Materia": materias}}}


def _bronze(item):
    return RegistroBronze.de("senado.materias", "u", item)


class TestFormatoData(unittest.TestCase):
    def test_iso_vira_aaaammdd(self):
        self.assertEqual(_aaaammdd("2024-06-01"), "20240601")


class TestTransformacao(unittest.TestCase):
    def test_shape_e_limpeza_de_ementa(self):
        p = transformar_materia(_materia())
        self.assertEqual(p["casa_origem"], "senado")
        self.assertEqual(p["id_fonte"], "161856")
        self.assertEqual(p["tipo"], "PL")
        self.assertEqual(p["numero"], 1)      # "00001" → 1
        self.assertEqual(p["ano"], 2024)
        self.assertEqual(p["identificador"], "PL 1/2024")
        # ; vira , e a quebra de linha some (§3.2)
        self.assertNotIn(";", p["ementa"])
        self.assertNotIn("\n", p["ementa"])
        self.assertEqual(p["data_apresentacao"], "2024-01-02")


class TestPortao(unittest.TestCase):
    def test_valido_passa(self):
        r = processar_materias_para_prata([_bronze(_materia())])
        self.assertEqual(len(r.aprovados), 1)

    def test_tipo_nao_suportado_vai_para_quarentena(self):
        """RQS (requerimento, procedural) não está no enum → quarentena honesta,
        não erro. (aceita/recusa: PL passa, RQS não.)"""
        r = processar_materias_para_prata([_bronze(_materia(sigla="RQS"))])
        self.assertEqual(r.aprovados, [])
        self.assertTrue(len(r.quarentena) == 1)


class TestRodada(unittest.TestCase):
    def test_rodada_consulta_por_sigla_e_agrega(self):
        cli = ClienteFake({
            "PL": _wrap([_materia(cod="1", sigla="PL")]),
            "PEC": _wrap([_materia(cod="2", sigla="PEC", numero="7")]),
            "PLP": _wrap([]),
            "PDL": _wrap([]),
        })
        r = rodada_materias(cli, data_inicio="2024-06-01", data_fim="2024-06-30",
                            canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 2)
        self.assertEqual(cli.siglas_consultadas, ["PL", "PEC", "PLP", "PDL"])

    def test_janela_vazia_e_ok(self):
        cli = ClienteFake({s: _wrap([]) for s in ("PL", "PEC", "PLP", "PDL")})
        r = rodada_materias(cli, data_inicio="2024-01-01", data_fim="2024-01-02",
                            canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(r.prata.aprovados, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
