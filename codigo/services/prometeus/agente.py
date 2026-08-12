"""O agente conversacional (ReAct): recebe uma pergunta, deixa o modelo escolher e
chamar ferramentas até responder, e devolve a resposta JÁ com as fontes e ressalvas
acumuladas (contrato §20).

O modelo (LLM) e o gateway são injetados — por isso o loop é testável sem rede e
sem chave (a suíte usa um modelo fake e o FakeGateway).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import ferramentas
from contrato import SYSTEM_PROMPT
from gateway import Gateway
from modelo import Modelo, RespostaModelo

MAX_PASSOS = 6  # teto de idas ao modelo por pergunta (evita loop infinito)


@dataclass
class RespostaChat:
    resposta: str
    fontes: list[dict] = field(default_factory=list)
    ressalvas: list[str] = field(default_factory=list)
    ferramentas_usadas: list[str] = field(default_factory=list)
    recusada: bool = False


class Agente:
    def __init__(self, modelo: Modelo, gateway: Gateway) -> None:
        self.modelo = modelo
        self.gateway = gateway
        self.esquemas = ferramentas.esquemas_anthropic()

    def responder(self, pergunta: str) -> RespostaChat:
        mensagens: list[dict] = [{"role": "user", "content": pergunta}]
        fontes: dict[tuple, dict] = {}
        ressalvas: list[str] = []
        usadas: list[str] = []

        for _ in range(MAX_PASSOS):
            r: RespostaModelo = self.modelo.conversar(
                system=SYSTEM_PROMPT, mensagens=mensagens, ferramentas=self.esquemas
            )

            if r.parou_por == "refusal":
                return RespostaChat(
                    resposta=r.texto or "Não posso responder isso.",
                    recusada=True,
                    fontes=list(fontes.values()),
                    ressalvas=_dedup(ressalvas),
                    ferramentas_usadas=usadas,
                )

            mensagens.append(self._turno_assistente(r))

            if not r.chamadas:
                return RespostaChat(
                    resposta=r.texto,
                    fontes=list(fontes.values()),
                    ressalvas=_dedup(ressalvas),
                    ferramentas_usadas=usadas,
                )

            blocos: list[dict] = []
            for c in r.chamadas:
                usadas.append(c.nome)
                res = ferramentas.executar(self.gateway, c.nome, c.args)
                for p in res.get("proveniencia", []) or []:
                    fontes[(p.get("source"), p.get("source_url"), p.get("synced_at"))] = p
                ressalvas.extend(res.get("ressalvas", []) or [])
                blocos.append(self._bloco_resultado(c.id, res))
            mensagens.append({"role": "user", "content": blocos})

        # Estourou o teto de passos sem chegar a uma resposta: recusa honesta (regra 7).
        return RespostaChat(
            resposta=(
                "Não consegui concluir a consulta em passos suficientes. "
                "Tente reformular a pergunta de forma mais específica."
            ),
            recusada=True,
            fontes=list(fontes.values()),
            ressalvas=_dedup(ressalvas),
            ferramentas_usadas=usadas,
        )

    # As formas abaixo estão no formato de mensagem da Claude API — o ModeloClaude
    # as consome direto; o modelo fake dos testes só as inspeciona.
    def _turno_assistente(self, r: RespostaModelo) -> dict:
        conteudo: list[dict] = []
        if r.texto:
            conteudo.append({"type": "text", "text": r.texto})
        for c in r.chamadas:
            conteudo.append(
                {"type": "tool_use", "id": c.id, "name": c.nome, "input": c.args}
            )
        return {"role": "assistant", "content": conteudo}

    def _bloco_resultado(self, id_: str, res: dict) -> dict:
        return {
            "type": "tool_result",
            "tool_use_id": id_,
            "content": json.dumps(res, ensure_ascii=False),
        }


def _dedup(xs: list[str]) -> list[str]:
    vistos: set[str] = set()
    out: list[str] = []
    for x in xs:
        if x not in vistos:
            vistos.add(x)
            out.append(x)
    return out
