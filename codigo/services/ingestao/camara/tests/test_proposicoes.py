"""Testes do coletor da Câmara — proposições.

HTTP totalmente stubado. Cada teste ataca um comportamento específico:
retry por instabilidade, falha imediata em 4xx, dedup por conteúdo, portão
de qualidade recusando o que a seção 3.1 manda recusar, e os quatro estados
do contrato.
"""

import unittest
from datetime import date
from typing import Any

from camara.proposicoes import (
    CAMPOS_CRITICOS_PROPOSICAO,
    processar_para_prata,
    rodada,
    transformar_proposicao,
)
from contrato.canario import EstadoContrato, avaliar, extrair_campos
from pipeline.camadas import RegistroBronze, hash_conteudo
from pipeline.coletor import (
    ErroFalha,
    ErroInstabilidade,
    JanelaMovel,
    PoliticaRetry,
    obter_com_retry,
)
from pipeline.dedup import deduplicar


# -----------------------------------------------------------------------------
# Cliente HTTP falso
# -----------------------------------------------------------------------------

class _Resp:
    def __init__(self, status: int, corpo: Any):
        self.status = status
        self.corpo = corpo
    def texto(self) -> str:
        return str(self.corpo)


class ClienteFake:
    """Aceita uma lista de respostas ou callables por URL."""

    def __init__(self, respostas: list[Any] | None = None,
                 por_url: dict[str, list[Any]] | None = None):
        self.respostas = list(respostas or [])
        self.por_url = {k: list(v) for k, v in (por_url or {}).items()}
        self.chamadas: list[tuple[str, dict | None]] = []

    def get(self, url: str, params: dict | None = None) -> _Resp:
        self.chamadas.append((url, params))
        fila = self.por_url.get(url) or self.respostas
        if not fila:
            raise AssertionError(f"sem resposta programada para {url}")
        item = fila.pop(0)
        if callable(item):
            return item(url, params)
        return item


def _proposicao_fonte(pid: int = 100, sigla: str = "PL", numero: int = 1,
                      ano: int = 2025, ementa: str = "Dispõe sobre ...",
                      data: str = "2025-03-14") -> dict:
    """Formato como a API v2 da Câmara devolve (best effort)."""
    return {
        "id": pid,
        "siglaTipo": sigla,
        "numero": numero,
        "ano": ano,
        "ementa": ementa,
        "dataApresentacao": data,
        "statusProposicao": {"descricaoSituacao": "Aguardando parecer"},
        "uriAutores": f"https://ex.com/proposicoes/{pid}/autores",
    }


# =============================================================================
# Retry — instabilidade vs falha
# =============================================================================

class TestRetryPorInstabilidade(unittest.TestCase):
    def _sleep_nop(self, _: float) -> None:
        pass

    def test_5xx_e_recuperado_na_retentativa(self):
        cliente = ClienteFake([
            _Resp(503, {"erro": "unavailable"}),
            _Resp(503, {"erro": "unavailable"}),
            _Resp(200, {"dados": [], "links": []}),
        ])
        corpo = obter_com_retry(cliente, "https://x/api",
                                politica=PoliticaRetry(tentativas_max=4),
                                dormir=self._sleep_nop)
        self.assertEqual(corpo, {"dados": [], "links": []})
        self.assertEqual(len(cliente.chamadas), 3)

    def test_429_conta_como_instabilidade(self):
        cliente = ClienteFake([
            _Resp(429, "rate limited"),
            _Resp(200, {"dados": []}),
        ])
        corpo = obter_com_retry(cliente, "https://x/api",
                                politica=PoliticaRetry(tentativas_max=2),
                                dormir=self._sleep_nop)
        self.assertEqual(corpo, {"dados": []})

    def test_4xx_e_falha_imediata_sem_retry(self):
        """404 não deve tentar de novo. É a distinção crítica da seção 19."""
        cliente = ClienteFake([_Resp(404, "not found")])
        with self.assertRaises(ErroFalha) as ctx:
            obter_com_retry(cliente, "https://x/api",
                            politica=PoliticaRetry(tentativas_max=4),
                            dormir=self._sleep_nop)
        self.assertEqual(ctx.exception.status, 404)
        self.assertEqual(len(cliente.chamadas), 1)

    def test_instabilidade_persistente_esgota_tentativas(self):
        cliente = ClienteFake([_Resp(500, "boom")] * 3)
        with self.assertRaises(ErroInstabilidade):
            obter_com_retry(cliente, "https://x/api",
                            politica=PoliticaRetry(tentativas_max=3),
                            dormir=self._sleep_nop)
        self.assertEqual(len(cliente.chamadas), 3)

    def test_espera_e_exponencial_com_teto(self):
        p = PoliticaRetry(base_segundos=1.0, fator=2.0, teto_segundos=5.0)
        self.assertEqual(p.espera(0), 1.0)
        self.assertEqual(p.espera(1), 2.0)
        self.assertEqual(p.espera(2), 4.0)
        # A quinta tentativa daria 16, o teto corta em 5.
        self.assertEqual(p.espera(4), 5.0)


# =============================================================================
# Transformação bronze → prata
# =============================================================================

class TestTransformacao(unittest.TestCase):
    def test_shape_completo(self):
        prata = transformar_proposicao(_proposicao_fonte())
        self.assertEqual(prata["id_fonte"], "100")
        self.assertEqual(prata["tipo"], "PL")
        self.assertEqual(prata["identificador"], "PL 1/2025")
        self.assertEqual(prata["casa_origem"], "camara")
        self.assertEqual(prata["situacao"], "Aguardando parecer")

    def test_ementa_vazia_vira_none_para_ser_barrada_no_portao(self):
        p = _proposicao_fonte(ementa="   ")
        prata = transformar_proposicao(p)
        self.assertIsNone(prata["ementa"])


# =============================================================================
# Portão de qualidade — a seção 3.1
# =============================================================================

class TestPortaoQualidade(unittest.TestCase):
    def _bronze(self, payload: dict) -> RegistroBronze:
        return RegistroBronze.de("camara.proposicoes", "https://x", payload)

    def test_registro_valido_e_aprovado(self):
        r = processar_para_prata([self._bronze(_proposicao_fonte())])
        self.assertEqual(len(r.aprovados), 1)
        self.assertEqual(r.quarentena, [])

    def test_ementa_vazia_vai_para_quarentena_por_completude(self):
        r = processar_para_prata([self._bronze(_proposicao_fonte(ementa=""))])
        self.assertEqual(r.aprovados, [])
        self.assertEqual(len(r.quarentena), 1)
        _, v = r.quarentena[0]
        self.assertEqual(v.dimensao, "completude")
        self.assertIn("ementa", v.motivo)

    def test_tipo_fora_do_enum_vai_para_quarentena_por_precisao(self):
        r = processar_para_prata([self._bronze(_proposicao_fonte(sigla="XYZ"))])
        _, v = r.quarentena[0]
        self.assertEqual(v.dimensao, "precisao")

    def test_ano_zero_vai_para_quarentena(self):
        r = processar_para_prata([self._bronze(_proposicao_fonte(ano=0))])
        _, v = r.quarentena[0]
        self.assertEqual(v.dimensao, "precisao")

    def test_erro_na_transformacao_e_capturado_e_triado(self):
        """Payload corrompido não deve derrubar o pipeline — vai à quarentena.

        Seção 3.1: 'O que viola um portão vai à quarentena com o motivo
        registrado, e não adiante.'
        """
        r = processar_para_prata([self._bronze({"lixo": True})])
        self.assertEqual(r.aprovados, [])
        self.assertEqual(len(r.quarentena), 1)


# =============================================================================
# Dedup por conteúdo — o instrumento de detecção da seção 5.4
# =============================================================================

class TestDedup(unittest.TestCase):
    def _bronze(self, payload: dict) -> RegistroBronze:
        return RegistroBronze.de("camara.proposicoes", "https://x", payload)

    def test_repeticao_pura_e_descartada(self):
        anterior = self._bronze(_proposicao_fonte(pid=1))
        atual = self._bronze(_proposicao_fonte(pid=1))
        r = deduplicar([atual], {"1": anterior}, chave_id="id_fonte"
                       if False else "id")
        self.assertEqual(r.repetidos, [atual])
        self.assertEqual(r.novos, [])
        self.assertEqual(r.alterados, [])

    def test_edicao_retroativa_e_detectada_nao_descartada(self):
        """Mesmo id, conteúdo diferente entre coletas.

        A seção 5.4 aponta isso como o instrumento que revelou edição feita
        no lugar em despesas. Aqui a expectativa é: NÃO descartar, sinalizar.
        """
        anterior = self._bronze(_proposicao_fonte(pid=1, ementa="Versão A"))
        atual = self._bronze(_proposicao_fonte(pid=1, ementa="Versão B"))
        r = deduplicar([atual], {"1": anterior}, chave_id="id")
        self.assertEqual(r.repetidos, [])
        self.assertEqual(r.novos, [])
        self.assertEqual(len(r.alterados), 1)
        ant, atu = r.alterados[0]
        self.assertNotEqual(ant.hash_conteudo, atu.hash_conteudo)

    def test_novo_id_vai_para_novos(self):
        atual = self._bronze(_proposicao_fonte(pid=99))
        r = deduplicar([atual], {}, chave_id="id")
        self.assertEqual(r.novos, [atual])

    def test_hash_de_conteudo_e_estavel_entre_ordens_de_chave(self):
        """JSON canonizado por chave é o que sustenta o hash.

        Sem isso, servidor que troca a ordem das chaves derrubaria o hash e
        pareceria edição — falso positivo custoso.
        """
        h1 = hash_conteudo({"a": 1, "b": 2})
        h2 = hash_conteudo({"b": 2, "a": 1})
        self.assertEqual(h1, h2)


# =============================================================================
# Teste de contrato — os quatro estados
# =============================================================================

class TestContrato(unittest.TestCase):
    def test_canario_nao_validado_impede_ok(self):
        r = avaliar(
            canario_validado=False,
            resposta=[{"id": 1, "siglaTipo": "PL", "numero": 1, "ano": 2025,
                       "ementa": "x", "dataApresentacao": "2025-01-01"}],
            linha_base=CAMPOS_CRITICOS_PROPOSICAO,
            criticos=CAMPOS_CRITICOS_PROPOSICAO,
        )
        self.assertIs(r.estado, EstadoContrato.FALHA)

    def test_falha_por_erro_nao_recuperavel(self):
        r = avaliar(canario_validado=True, resposta=None,
                    erro_falha="HTTP 404",
                    linha_base=None, criticos=CAMPOS_CRITICOS_PROPOSICAO)
        self.assertIs(r.estado, EstadoContrato.FALHA)

    def test_instabilidade_e_reportada_como_tal_nao_como_falha(self):
        """A distinção da seção 19: 5xx/timeout != 4xx/DNS."""
        r = avaliar(canario_validado=True, resposta=None,
                    erro_instabilidade="HTTP 503 x3",
                    linha_base=None, criticos=CAMPOS_CRITICOS_PROPOSICAO)
        self.assertIs(r.estado, EstadoContrato.INSTABILIDADE)

    def test_resposta_vazia_com_canario_validado_e_falha(self):
        """Consulta que se sabe não vazia voltar vazia é FALHA (seção 19)."""
        r = avaliar(canario_validado=True, resposta=[],
                    linha_base=CAMPOS_CRITICOS_PROPOSICAO,
                    criticos=CAMPOS_CRITICOS_PROPOSICAO)
        self.assertIs(r.estado, EstadoContrato.FALHA)

    def test_campo_critico_ausente_e_quebra(self):
        r = avaliar(canario_validado=True,
                    resposta=[{"id": 1, "siglaTipo": "PL", "numero": 1,
                               "ano": 2025, "ementa": "x"}],  # sem dataApresentacao
                    linha_base=CAMPOS_CRITICOS_PROPOSICAO,
                    criticos=CAMPOS_CRITICOS_PROPOSICAO)
        self.assertIs(r.estado, EstadoContrato.QUEBRA)
        self.assertIn("dataApresentacao", r.campos_faltando)

    def test_campo_novo_e_alerta_nao_quebra(self):
        base = CAMPOS_CRITICOS_PROPOSICAO
        completo = dict.fromkeys(base, "v")
        completo["campoNovo"] = "v"
        r = avaliar(canario_validado=True, resposta=[completo],
                    linha_base=base, criticos=base)
        self.assertIs(r.estado, EstadoContrato.ALERTA)
        self.assertIn("campoNovo", r.campos_novos)

    def test_ok_quando_nada_diverge(self):
        base = CAMPOS_CRITICOS_PROPOSICAO
        completo = dict.fromkeys(base, "v")
        r = avaliar(canario_validado=True, resposta=[completo],
                    linha_base=base, criticos=base)
        self.assertIs(r.estado, EstadoContrato.OK)

    def test_extrair_campos_lida_com_lista_e_objeto(self):
        self.assertEqual(extrair_campos([{"a": 1, "b": 2}]), frozenset({"a", "b"}))
        self.assertEqual(extrair_campos({"a": 1}), frozenset({"a"}))
        self.assertEqual(extrair_campos([]), frozenset())
        self.assertEqual(extrair_campos(None), frozenset())


# =============================================================================
# Rodada completa
# =============================================================================

class TestRodadaCompleta(unittest.TestCase):
    def _bronze_ok(self, n=2):
        dados = [_proposicao_fonte(pid=i, numero=i) for i in range(1, n + 1)]
        return _Resp(200, {"dados": dados, "links": []})

    def test_rodada_feliz(self):
        cliente = ClienteFake([self._bronze_ok(3)])
        r = rodada(
            cliente,
            ate=date(2026, 3, 1),
            janela=JanelaMovel(dias=30),
            canario_validado=True,
            # linha_base = tudo que a fonte devolveu no dia da validação.
            # criticos é subset (o que não pode faltar). Aqui igualamos ao
            # payload real de _proposicao_fonte, senão os extras acionam ALERTA.
            linha_base=frozenset({
                "id", "siglaTipo", "numero", "ano", "ementa",
                "dataApresentacao", "statusProposicao", "uriAutores",
            }),
        )
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.bronze), 3)
        self.assertIsNotNone(r.prata)
        assert r.prata is not None
        self.assertEqual(len(r.prata.aprovados), 3)

    def test_rodada_com_quebra_pula_portao(self):
        """Quebra suspende a ingestão da área (seção 19)."""
        item_quebrado = {"id": 1, "siglaTipo": "PL", "numero": 1, "ano": 2025,
                         "ementa": "x"}  # sem dataApresentacao
        cliente = ClienteFake([_Resp(200, {"dados": [item_quebrado], "links": []})])
        r = rodada(
            cliente,
            ate=date(2026, 3, 1),
            janela=JanelaMovel(dias=30),
            canario_validado=True,
            # Linha de base do dia da validação = payload completo.
            linha_base=frozenset({
                "id", "siglaTipo", "numero", "ano", "ementa",
                "dataApresentacao", "statusProposicao", "uriAutores",
            }),
        )
        self.assertIs(r.estado, EstadoContrato.QUEBRA)
        self.assertIsNone(r.prata)  # portão não roda

    def test_rodada_com_alerta_ainda_processa(self):
        """Campo novo não bloqueia — só sinaliza leitura humana."""
        item_com_novo = _proposicao_fonte()
        item_com_novo["campoNovo"] = "surpresa"
        cliente = ClienteFake([_Resp(200, {"dados": [item_com_novo], "links": []})])
        r = rodada(
            cliente,
            ate=date(2026, 3, 1),
            janela=JanelaMovel(dias=30),
            canario_validado=True,
            linha_base=frozenset({
                "id", "siglaTipo", "numero", "ano", "ementa",
                "dataApresentacao", "statusProposicao", "uriAutores",
            }),
        )
        self.assertIs(r.estado, EstadoContrato.ALERTA)
        self.assertIsNotNone(r.prata)
        assert r.prata is not None
        self.assertEqual(len(r.prata.aprovados), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
