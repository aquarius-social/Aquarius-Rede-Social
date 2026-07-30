"""Cliente HTTP concreto para produção — implementa `ClienteHttp` sobre urllib.

Os coletores falam com a porta `ClienteHttp` (coletor.py); os testes injetam um
fake. Esta é a implementação real, e usa só a biblioteca padrão (`urllib`), que
está sempre disponível — nenhuma dependência externa a instalar no deploy.

Contrato com `obter_com_retry` (coletor.py):
  - Resposta HTTP (inclusive 4xx/5xx) volta como objeto com `.status`, `.corpo`
    (JSON já parseado, ou None em erro) e `.texto()`. Quem classifica os estados
    da §19 é o `obter_com_retry`, não este cliente — por isso um 4xx/5xx NÃO
    levanta exceção aqui, apenas devolve o status.
  - Erro de TRANSPORTE (conexão caiu, timeout, DNS) levanta exceção, e o
    `obter_com_retry` a trata como instabilidade com retry.

O `abrir` (por padrão `urllib.request.urlopen`) é injetável para o teste rodar
sem rede.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable


class RespostaUrllib:
    def __init__(self, status: int, corpo: Any, texto: str):
        self.status = status
        self.corpo = corpo
        self._texto = texto

    def texto(self) -> str:
        return self._texto


class ClienteHttpUrllib:
    """Cliente HTTP real sobre urllib. Sem dependências externas."""

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        user_agent: str = "Aquarius/1.0 (ingestao; dados abertos)",
        abrir: Callable[..., Any] | None = None,
    ):
        self._timeout = timeout
        self._ua = user_agent
        self._abrir = abrir or urllib.request.urlopen

    def get(self, url: str, params: dict[str, Any] | None = None) -> RespostaUrllib:
        alvo = url
        if params:
            alvo = f"{url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            alvo,
            headers={"Accept": "application/json", "User-Agent": self._ua},
        )
        try:
            with self._abrir(req, timeout=self._timeout) as r:
                bruto = r.read().decode("utf-8")
                status = getattr(r, "status", 200)
        except urllib.error.HTTPError as e:
            # 4xx/5xx: devolve o status para o obter_com_retry classificar.
            bruto = e.read().decode("utf-8", "ignore")
            status = e.code
        # URLError, timeout e afins NÃO são capturados: sobem como erro de
        # transporte, que o obter_com_retry trata como instabilidade.

        corpo = None
        if bruto and status < 400:
            try:
                corpo = json.loads(bruto)
            except json.JSONDecodeError:
                corpo = None
        return RespostaUrllib(status, corpo, bruto)
