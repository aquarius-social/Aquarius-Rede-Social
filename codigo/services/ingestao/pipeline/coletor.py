"""Coleta HTTP com retry exponencial, deduplicação e janela móvel.

Implementa as disciplinas das seções 3.3 (cadência e janela móvel) e 19
(instabilidade separada de falha).

Duas separações que a Metodologia trata como estados próprios:

    Instabilidade — a chamada falha e se recupera na retentativa. É estado
                    próprio, registrado com o código de erro, porque erro de
                    servidor, recusa por excesso de requisições e queda de
                    conexão pedem reações diferentes.

    Falha         — a fonte não responde, ou uma consulta-canário, cuja
                    resposta se sabe não vazia, volta vazia.

Este módulo trata da instabilidade. O canário e os quatro estados vivem em
`contrato/`. HTTP real é injetado — os testes rodam sem rede.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol


class RespostaHttp(Protocol):
    status: int
    corpo: Any
    def texto(self) -> str: ...


class ClienteHttp(Protocol):
    def get(self, url: str, params: dict[str, Any] | None = None) -> RespostaHttp: ...


class ErroInstabilidade(Exception):
    """Chamada falhou de forma potencialmente recuperável (5xx, 429, timeout)."""

    def __init__(self, motivo: str, status: int | None = None):
        super().__init__(motivo)
        self.status = status


class ErroFalha(Exception):
    """Chamada falhou de forma não recuperável (4xx exceto 429, DNS, TLS)."""

    def __init__(self, motivo: str, status: int | None = None):
        super().__init__(motivo)
        self.status = status


@dataclass(frozen=True)
class PoliticaRetry:
    """Retry exponencial com teto.

    Defaults escolhidos para o perfil das APIs governamentais brasileiras:
    tolerantes a instabilidade curta, sem martelar a fonte quando ela cai
    de vez.
    """

    tentativas_max: int = 4
    base_segundos: float = 0.5
    fator: float = 2.0
    teto_segundos: float = 30.0

    def espera(self, tentativa: int) -> float:
        return min(self.base_segundos * (self.fator ** tentativa), self.teto_segundos)


def _classificar(status: int) -> type[Exception] | None:
    if 200 <= status < 300:
        return None
    if status == 429 or status >= 500:
        return ErroInstabilidade
    return ErroFalha


def obter_com_retry(
    cliente: ClienteHttp,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    politica: PoliticaRetry = PoliticaRetry(),
    dormir: Callable[[float], None] = time.sleep,
) -> Any:
    """Executa GET com retry apenas em instabilidade.

    Devolve o corpo. Levanta `ErroInstabilidade` após esgotar tentativas, ou
    `ErroFalha` imediatamente para erros não recuperáveis. A distinção é o
    que permite ao chamador reagir diferente — o teste de contrato usa isso
    para diferenciar os quatro estados da seção 19.
    """
    ultima_excecao: Exception | None = None
    for tentativa in range(politica.tentativas_max):
        try:
            resp = cliente.get(url, params=params)
        except Exception as e:
            # Falha de camada de transporte é tratada como instabilidade,
            # com retry. Se persistir, será relatada como tal.
            ultima_excecao = ErroInstabilidade(f"erro de transporte: {e!r}")
        else:
            classe = _classificar(resp.status)
            if classe is None:
                return resp.corpo
            excecao = classe(
                f"HTTP {resp.status} em {url}: {resp.texto()[:200]}",
                status=resp.status,
            )
            if isinstance(excecao, ErroFalha):
                raise excecao
            ultima_excecao = excecao

        if tentativa + 1 < politica.tentativas_max:
            dormir(politica.espera(tentativa))

    assert ultima_excecao is not None
    raise ultima_excecao


# -----------------------------------------------------------------------------
# Janela móvel — releitura defensiva
# -----------------------------------------------------------------------------

from datetime import date, timedelta


@dataclass(frozen=True)
class JanelaMovel:
    """Janela de releitura.

    Seção 3.3: "Cada rodada relê uma janela móvel maior que a maior defasagem
    observada na área, porque o registro publicado com atraso (verificou-se
    votação registrada catorze dias após a sessão) se perde numa leitura
    restrita à véspera, e se perde em silêncio."
    """

    dias: int

    def intervalo(self, ate: date) -> tuple[date, date]:
        return ate - timedelta(days=self.dias), ate
