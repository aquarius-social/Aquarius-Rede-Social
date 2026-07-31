"""Testes do coletor de emendas parlamentares (Área F, §13).

Campos e formato batem com o dado real baixado (emendas_2024.json). Cobre o
parse do formato BR, a extração do autor do código (§6.3) e a identidade de
ordem dos estágios (§5.2).
"""

import unittest
from typing import Any

from contrato.canario import EstadoContrato
from pipeline.camadas import RegistroBronze
from transparencia.emendas import (
    processar_emendas_para_prata,
    rodada_emendas,
    transformar_emenda,
    _valor,
)


class _Resp:
    def __init__(self, status, corpo):
        self.status = status
        self.corpo = corpo
    def texto(self):
        return str(self.corpo)


class ClienteFake:
    """Fila por URL — cada get() consome a próxima resposta (para paginação)."""
    def __init__(self, por_url):
        self.por_url = {k: list(v) for k, v in por_url.items()}
    def get(self, url, params=None):
        fila = self.por_url.get(url)
        if fila is None:
            raise AssertionError(f"sem resposta para {url}")
        return fila.pop(0) if fila else _Resp(200, [])


_URL = "https://api.portaldatransparencia.gov.br/api-de-dados/emendas"


def _emenda(codigo="202440340007", emp="10.000,00", liq="10.000,00",
            pago="10.000,00", numero="0007"):
    return {
        "codigoEmenda": codigo, "ano": 2024,
        "tipoEmenda": "Emenda Individual - Transferências com Finalidade Definida",
        "autor": "LUISA CANZIANI", "nomeAutor": "LUISA CANZIANI",
        "numeroEmenda": numero, "localidadeDoGasto": "LONDRINA - PR",
        "funcao": "Saúde", "subfuncao": "Assistência hospitalar e ambulatorial",
        "valorEmpenhado": emp, "valorLiquidado": liq, "valorPago": pago,
        "valorRestoInscrito": "0,00", "valorRestoCancelado": "0,00",
        "valorRestoPago": "0,00",
    }


def _bronze(payload):
    return RegistroBronze.de("transparencia.emendas", "u", payload)


class TestParseValor(unittest.TestCase):
    def test_formato_br(self):
        self.assertEqual(_valor("10.000,00"), 10000.0)
        self.assertEqual(_valor("1.234.567,89"), 1234567.89)
        self.assertEqual(_valor("0,00"), 0.0)

    def test_vazio_vira_none(self):
        self.assertIsNone(_valor(""))
        self.assertIsNone(_valor(None))


class TestTransformacaoEmenda(unittest.TestCase):
    def test_shape_e_autor_codigo(self):
        p = transformar_emenda(_emenda())
        self.assertEqual(p["codigo_emenda"], "202440340007")
        self.assertEqual(p["ano"], 2024)
        self.assertEqual(p["autor_nome"], "LUISA CANZIANI")
        # §6.3: ano(4) + AUTOR + numero → '202440340007' com '0007' → '4034'
        self.assertEqual(p["autor_codigo"], "4034")
        self.assertEqual(p["valor_empenhado"], 10000.0)
        self.assertEqual(p["funcao"], "Saúde")


class TestPortaoEmenda(unittest.TestCase):
    def test_valida_passa(self):
        r = processar_emendas_para_prata([_bronze(_emenda())])
        self.assertEqual(len(r.aprovados), 1)

    def test_sem_codigo_vai_para_quarentena(self):
        e = _emenda()
        del e["codigoEmenda"]
        r = processar_emendas_para_prata([_bronze(e)])
        self.assertEqual(r.aprovados, [])
        self.assertEqual(r.quarentena[0][1].dimensao, "completude")

    def test_liquidado_maior_que_empenhado_e_incoerente(self):
        """§5.2: empenhado ≥ liquidado. Se a fonte publicar o contrário, quarentena."""
        r = processar_emendas_para_prata(
            [_bronze(_emenda(emp="5.000,00", liq="10.000,00"))])
        self.assertEqual(r.aprovados, [])
        self.assertEqual(r.quarentena[0][1].dimensao, "consistencia")

    def test_pago_maior_que_liquidado_e_incoerente(self):
        r = processar_emendas_para_prata(
            [_bronze(_emenda(liq="5.000,00", pago="10.000,00"))])
        self.assertEqual(r.aprovados, [])

    def test_estagios_iguais_passam(self):
        """Empenhado=liquidado=pago (o caso comum) é coerente."""
        r = processar_emendas_para_prata(
            [_bronze(_emenda(emp="9.000,00", liq="9.000,00", pago="9.000,00"))])
        self.assertEqual(len(r.aprovados), 1)


class TestRodadaEmendas(unittest.TestCase):
    def test_rodada_feliz_pagina_ate_vazio(self):
        cliente = ClienteFake({_URL: [
            _Resp(200, [_emenda("202440340007"), _emenda("202440340008", numero="0008")]),
            _Resp(200, []),  # página 2 vazia → para
        ]})
        r = rodada_emendas(cliente, 2024, canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 2)

    def test_401_sem_chave_vira_falha(self):
        cliente = ClienteFake({_URL: [_Resp(401, "sem chave")]})
        r = rodada_emendas(cliente, 2024, canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.FALHA)
        self.assertIsNone(r.prata)


if __name__ == "__main__":
    unittest.main(verbosity=2)
