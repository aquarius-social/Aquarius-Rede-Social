"""Testes do coletor de tramitações da Câmara (Área D, §11).

Cobre a novidade desta etapa: a identidade de sequência monotônica (§5.2),
verificável só sobre a lista inteira de uma proposição, e a ressalva bicameral
(`casa` explícito em cada registro).
"""

import unittest
from typing import Any

from camara.tramitacoes import (
    CAMPOS_CRITICOS_TRAMITACAO,
    conferir_sequencia_monotonica,
    processar_tramitacoes_para_prata,
    rodada_tramitacoes,
    transformar_tramitacao,
)
from contrato.canario import EstadoContrato
from pipeline.camadas import RegistroBronze


class _Resp:
    def __init__(self, status: int, corpo: Any):
        self.status = status
        self.corpo = corpo
    def texto(self) -> str:
        return str(self.corpo)


class ClienteFake:
    def __init__(self, por_url: dict[str, list[Any]]):
        self.por_url = {k: list(v) for k, v in por_url.items()}
        self.chamadas: list[tuple[str, dict | None]] = []
    def get(self, url: str, params: dict | None = None) -> _Resp:
        self.chamadas.append((url, params))
        fila = self.por_url.get(url)
        if fila is None:
            raise AssertionError(f"sem resposta programada para {url}")
        return fila.pop(0)


def _tram(seq, dh, orgao="PLEN", desc="Às Comissões", despacho=None):
    return {
        "sequencia": seq, "dataHora": dh, "siglaOrgao": orgao,
        "descricaoTramitacao": desc, "despacho": despacho,
        "descricaoSituacao": None, "codTipoTramitacao": 100,
    }


def _bronze(payload):
    return RegistroBronze.de("camara.tramitacoes", "https://x", payload)


# =============================================================================
# Transformação
# =============================================================================

class TestTransformacaoTramitacao(unittest.TestCase):
    def test_shape_e_proposicao_injetada(self):
        p = transformar_tramitacao(_tram(1, "2015-03-12T18:32"), "996958")
        self.assertEqual(p["proposicao_id_fonte"], "996958")
        self.assertEqual(p["casa"], "camara")  # ressalva bicameral (§11)
        self.assertEqual(p["sequencia"], 1)
        self.assertEqual(p["data_hora"], "2015-03-12T18:32")
        self.assertEqual(p["orgao_sigla"], "PLEN")

    def test_limpa_texto_livre_do_despacho(self):
        p = transformar_tramitacao(
            _tram(2, "2015-04-01T10:00", despacho="Linha 1\r\n\r\nLinha 2"),
            "996958",
        )
        self.assertEqual(p["despacho"], "Linha 1 Linha 2")


# =============================================================================
# Portão
# =============================================================================

class TestPortaoTramitacao(unittest.TestCase):
    def test_valida_passa(self):
        r = processar_tramitacoes_para_prata(
            [_bronze(_tram(1, "2015-03-12T18:32"))], "996958")
        self.assertEqual(len(r.aprovados), 1)

    def test_sem_descricao_vai_para_quarentena(self):
        r = processar_tramitacoes_para_prata(
            [_bronze(_tram(1, "2015-03-12T18:32", desc=None))], "996958")
        self.assertEqual(r.aprovados, [])
        _, v = r.quarentena[0]
        self.assertEqual(v.dimensao, "completude")

    def test_sequencia_invalida_vai_para_quarentena(self):
        r = processar_tramitacoes_para_prata(
            [_bronze(_tram(0, "2015-03-12T18:32"))], "996958")
        _, v = r.quarentena[0]
        self.assertEqual(v.dimensao, "precisao")


# =============================================================================
# Identidade §5.2 — sequência temporal monotônica
# =============================================================================

class TestSequenciaMonotonica(unittest.TestCase):
    def test_cadeia_em_ordem_nao_gera_violacao(self):
        tram = [
            transformar_tramitacao(_tram(1, "2015-03-12T18:32"), "1"),
            transformar_tramitacao(_tram(2, "2015-03-15T09:00"), "1"),
            transformar_tramitacao(_tram(3, "2015-04-01T10:00"), "1"),
        ]
        self.assertEqual(conferir_sequencia_monotonica(tram), [])

    def test_data_que_retrocede_gera_violacao(self):
        """Sequência 2 com data ANTERIOR à sequência 1 — cadeia incoerente."""
        tram = [
            transformar_tramitacao(_tram(1, "2015-03-15T09:00"), "1"),
            transformar_tramitacao(_tram(2, "2015-03-12T18:32"), "1"),  # retrocede
        ]
        viol = conferir_sequencia_monotonica(tram)
        self.assertEqual(len(viol), 1)
        self.assertEqual(viol[0].dimensao, "consistencia")

    def test_ordena_por_sequencia_antes_de_comparar(self):
        """A checagem ordena por sequência, mesmo se a lista chega embaralhada."""
        tram = [
            transformar_tramitacao(_tram(2, "2015-03-15T09:00"), "1"),
            transformar_tramitacao(_tram(1, "2015-03-12T18:32"), "1"),
        ]
        self.assertEqual(conferir_sequencia_monotonica(tram), [])

    def test_mesmo_dia_com_hora_zero_nao_e_violacao(self):
        """Achado da fonte viva (PL 736/2015): a sequência seguinte, do MESMO
        dia, vem carimbada às 00:00 (hora ausente). Não é anterioridade — a
        checagem compara por data, não por instante, para não gritar à toa."""
        tram = [
            transformar_tramitacao(_tram(91, "2026-05-04T13:16"), "1"),
            transformar_tramitacao(_tram(92, "2026-05-04T00:00"), "1"),
        ]
        self.assertEqual(conferir_sequencia_monotonica(tram), [])


# =============================================================================
# Rodada completa
# =============================================================================

class TestRodadaTramitacoes(unittest.TestCase):
    _URL = "https://dadosabertos.camara.leg.br/api/v2/proposicoes/996958/tramitacoes"

    def test_rodada_feliz(self):
        cliente = ClienteFake({self._URL: [_Resp(200, {"dados": [
            _tram(1, "2015-03-12T18:32"), _tram(2, "2015-03-15T09:00")],
            "links": []})]})
        r = rodada_tramitacoes(cliente, "996958", canario_validado=True,
                               linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 2)
        self.assertEqual(r.sequencia_violacoes, [])

    def test_rodada_reporta_cadeia_nao_monotonica(self):
        cliente = ClienteFake({self._URL: [_Resp(200, {"dados": [
            _tram(1, "2015-03-15T09:00"), _tram(2, "2015-03-12T18:32")],
            "links": []})]})
        r = rodada_tramitacoes(cliente, "996958", canario_validado=True,
                               linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.sequencia_violacoes), 1)

    def test_falha_na_fonte_nao_processa_prata(self):
        cliente = ClienteFake({self._URL: [_Resp(404, "not found")]})
        r = rodada_tramitacoes(cliente, "996958", canario_validado=True,
                               linha_base=None)
        self.assertIs(r.estado, EstadoContrato.FALHA)
        self.assertIsNone(r.prata)


if __name__ == "__main__":
    unittest.main(verbosity=2)
