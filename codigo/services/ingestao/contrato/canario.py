"""Teste de contrato — os quatro estados da seção 19.

    Falha        — a fonte não responde, ou uma consulta-canário, cuja resposta
                   se sabe não vazia, volta vazia.
    Instabilidade— a chamada falha e se recupera na retentativa.
    Quebra       — um campo crítico desapareceu; a ingestão da área é suspensa.
    Alerta       — surgiu campo novo, ou a fonte anunciou descontinuação.

Duas disciplinas ficam nas invariantes deste módulo:

    - Canário validado antes de entrar em regime, porque monitor que grita à
      toa é monitor ignorado. Uma fonte com canário não validado NÃO pode ser
      declarada 'ok' — a função `avaliar` recusa.
    - Alerta e Quebra são estados distintos. A linha de base de campos é
      extraída da resposta e comparada entre execuções: campo desapareceu vira
      Quebra, campo novo vira Alerta. Confundi-los produz alarme falso num
      caso e silêncio indevido no outro (seção 19).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class EstadoContrato(str, Enum):
    OK = "ok"
    INSTABILIDADE = "instabilidade"
    FALHA = "falha"
    QUEBRA = "quebra"
    ALERTA = "alerta"


@dataclass(frozen=True)
class ResultadoContrato:
    estado: EstadoContrato
    detalhe: str
    campos_faltando: frozenset[str] = frozenset()
    campos_novos: frozenset[str] = frozenset()


def extrair_campos(resposta: Any) -> frozenset[str]:
    """Extrai a linha de base de campos da resposta.

    Trabalha em dois formatos comuns: lista de objetos (pega o primeiro) e
    objeto direto. Se a resposta vier vazia ou não estruturada, devolve
    conjunto vazio — quem chama decide o que fazer com isso.
    """
    if isinstance(resposta, list):
        if not resposta:
            return frozenset()
        resposta = resposta[0]
    if isinstance(resposta, dict):
        return frozenset(resposta.keys())
    return frozenset()


def avaliar(
    *,
    canario_validado: bool,
    resposta: Any | None,
    erro_instabilidade: str | None = None,
    erro_falha: str | None = None,
    linha_base: frozenset[str] | None,
    criticos: frozenset[str],
) -> ResultadoContrato:
    """Classifica o resultado de uma leitura da fonte.

    Precondição: `canario_validado` diz se o canário desta fonte já foi
    aprovado antes de entrar em regime. Fonte com canário pendente é sempre
    classificada como FALHA — sem essa disciplina, o monitor perde utilidade.

    Ordem de avaliação:
      1. Canário validado?           não → FALHA
      2. Erro de falha?               sim → FALHA
      3. Erro de instabilidade?       sim → INSTABILIDADE
      4. Resposta vazia?              sim → FALHA (canário volta vazio)
      5. Campo crítico desapareceu?   sim → QUEBRA
      6. Campo novo apareceu?         sim → ALERTA
      7. Nada disso                       → OK
    """
    if not canario_validado:
        return ResultadoContrato(
            EstadoContrato.FALHA,
            "canário não validado; fonte não pode ser declarada ok",
        )

    if erro_falha is not None:
        return ResultadoContrato(EstadoContrato.FALHA, erro_falha)

    if erro_instabilidade is not None:
        return ResultadoContrato(EstadoContrato.INSTABILIDADE, erro_instabilidade)

    if resposta is None or (isinstance(resposta, list) and not resposta):
        return ResultadoContrato(
            EstadoContrato.FALHA,
            "consulta-canário voltou vazia (resposta que se sabe não vazia)",
        )

    campos_atuais = extrair_campos(resposta)

    if linha_base is not None:
        faltando = frozenset(c for c in criticos if c not in campos_atuais)
        if faltando:
            return ResultadoContrato(
                EstadoContrato.QUEBRA,
                f"campo(s) crítico(s) desapareceu(ram): {sorted(faltando)}",
                campos_faltando=faltando,
            )
        novos = campos_atuais - linha_base
        if novos:
            return ResultadoContrato(
                EstadoContrato.ALERTA,
                f"campo(s) novo(s) na resposta: {sorted(novos)}",
                campos_novos=novos,
            )

    return ResultadoContrato(EstadoContrato.OK, "contrato íntegro")
