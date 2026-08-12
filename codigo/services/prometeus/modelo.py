"""O 'porto' do modelo de linguagem + o adaptador real (Claude).

`Modelo` é o contrato que o agente usa; `ModeloClaude` é a implementação sobre a
Claude API — Sonnet 5 como principal, com fall-back NATIVO Claude→Claude (Opus 4.8)
em caso de recusa. Uma chave só (ANTHROPIC_API_KEY).

O `anthropic` é importado preguiçosamente (dentro do __init__): a suíte usa um
modelo fake e não precisa da dependência nem da chave.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol

MODELO_PRINCIPAL = "claude-sonnet-5"
MODELO_FALLBACK = "claude-opus-4-8"


@dataclass
class ChamadaFerramenta:
    id: str
    nome: str
    args: dict


@dataclass
class RespostaModelo:
    texto: str = ""
    chamadas: list[ChamadaFerramenta] = field(default_factory=list)
    parou_por: str = "end_turn"  # 'tool_use' | 'end_turn' | 'refusal'


class Modelo(Protocol):
    def conversar(
        self, *, system: str, mensagens: list[dict], ferramentas: list[dict]
    ) -> RespostaModelo:
        """Uma ida ao modelo: devolve texto e/ou chamadas de ferramenta."""
        ...


class ModeloClaude:
    def __init__(
        self,
        api_key: str | None = None,
        modelo: str = MODELO_PRINCIPAL,
        max_tokens: int = 4096,
    ) -> None:
        import anthropic  # dependência só de runtime

        self._cliente = anthropic.Anthropic(
            api_key=api_key or os.environ["ANTHROPIC_API_KEY"]
        )
        self.modelo = modelo
        self.max_tokens = max_tokens

    def conversar(self, *, system, mensagens, ferramentas) -> RespostaModelo:
        resp = self._cliente.beta.messages.create(
            model=self.modelo,
            max_tokens=self.max_tokens,
            system=system,
            messages=mensagens,
            tools=ferramentas,
            # Fall-back nativo Claude→Claude: se o Sonnet recusar por engano
            # (falso alarme de segurança), a Anthropic re-tenta no Opus 4.8.
            betas=["server-side-fallback-2026-06-01"],
            fallbacks=[{"model": MODELO_FALLBACK}],
        )
        if resp.stop_reason == "refusal":
            return RespostaModelo(texto=_texto(resp), parou_por="refusal")
        chamadas = [
            ChamadaFerramenta(id=b.id, nome=b.name, args=dict(b.input))
            for b in resp.content
            if b.type == "tool_use"
        ]
        return RespostaModelo(
            texto=_texto(resp),
            chamadas=chamadas,
            parou_por="tool_use" if chamadas else "end_turn",
        )


def _texto(resp: Any) -> str:
    return "".join(b.text for b in resp.content if b.type == "text")
