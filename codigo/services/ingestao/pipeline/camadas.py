"""Pipeline em camadas — bronze, prata, ouro.

Implementa a seção 3.1 da Metodologia de Dados. Cada camada tem um contrato
próprio, e o que viola o portão entre duas camadas vai à quarentena com o
motivo registrado, não adiante.

    Bronze — cópia exata do que a fonte devolveu, com proveniência (fonte,
             instante da coleta e resumo criptográfico). Não se transforma.
    Prata  — padronizado, deduplicado, com identidades internas verificadas
             e entidade resolvida.
    Ouro   — modelo consumível pelo oráculo, com rótulos de proveniência,
             completude e frescor embutidos.

Este arquivo cobre bronze e prata. Ouro depende de agregações de leitura,
que entram na camada de API.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable


def hash_conteudo(payload: Any) -> str:
    """Resumo criptográfico do conteúdo. Estável entre execuções.

    A seção 3.4 é explícita sobre por que este hash existe: a contagem não
    detecta edição feita no lugar (estudo da seção 8, despesas). O hash por
    lançamento sim.
    """
    canonico = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"))
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def agora_utc() -> datetime:
    return datetime.now(timezone.utc)


# -----------------------------------------------------------------------------
# Bronze
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class RegistroBronze:
    """Um registro em camada bronze.

    Preservação sem transformação. O `payload` é literalmente o que a fonte
    devolveu para aquele item — nada renomeado, nada convertido. É esse
    conteúdo bruto que sustenta auditoria: para qualquer resposta servida,
    dá para chegar ao dado exato que a produziu.
    """

    fonte: str
    fonte_url: str
    payload: dict
    coletado_em: datetime
    hash_conteudo: str

    @classmethod
    def de(cls, fonte: str, fonte_url: str, payload: dict) -> RegistroBronze:
        return cls(
            fonte=fonte,
            fonte_url=fonte_url,
            payload=payload,
            coletado_em=agora_utc(),
            hash_conteudo=hash_conteudo(payload),
        )


# -----------------------------------------------------------------------------
# Portão de qualidade
# -----------------------------------------------------------------------------

DimensaoQualidade = str
# 'completude' | 'precisao' | 'consistencia' | 'integridade_referencial'
# | 'tempestividade' | 'unicidade'


@dataclass(frozen=True)
class Violacao:
    """O motivo pelo qual algo não passou no portão."""

    dimensao: DimensaoQualidade
    motivo: str


@dataclass
class ResultadoPortao:
    """Resultado da passagem pelo portão bronze → prata.

    Nunca lança exceção pelo caminho normal. Item que viola vai para
    `quarentena` com o motivo; item que passa vai para `aprovados`. Isso é
    deliberado: a seção 3.1 diz "o que viola um portão vai à quarentena com o
    motivo registrado, e não adiante" — quarentena é estado de dado, não
    ausência de dado.
    """

    aprovados: list[dict] = field(default_factory=list)
    quarentena: list[tuple[RegistroBronze, Violacao]] = field(default_factory=list)


# Um verificador é uma função que devolve None (passou) ou Violacao.
Verificador = Callable[[dict], Violacao | None]


def portao_bronze_prata(
    bronze: Iterable[RegistroBronze],
    transformar: Callable[[dict], dict],
    verificadores: list[Verificador],
) -> ResultadoPortao:
    """Aplica transformação e verificações. Não erra, tria."""
    resultado = ResultadoPortao()
    for registro in bronze:
        try:
            prata = transformar(registro.payload)
        except Exception as e:
            resultado.quarentena.append(
                (registro, Violacao("consistencia",
                                    f"erro na transformação: {e!r}"))
            )
            continue

        falhou = False
        for v in verificadores:
            violacao = v(prata)
            if violacao is not None:
                resultado.quarentena.append((registro, violacao))
                falhou = True
                break

        if not falhou:
            resultado.aprovados.append(prata)

    return resultado


# -----------------------------------------------------------------------------
# Verificadores gerais reutilizáveis
# -----------------------------------------------------------------------------

def campo_obrigatorio(nome: str) -> Verificador:
    """Fecha a dimensão de completude para um campo."""
    def _v(registro: dict) -> Violacao | None:
        valor = registro.get(nome)
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            return Violacao("completude", f"campo obrigatório ausente: {nome}")
        return None
    return _v


def campo_em(nome: str, permitidos: set[str]) -> Verificador:
    """Fecha a dimensão de precisão para um enum."""
    def _v(registro: dict) -> Violacao | None:
        valor = registro.get(nome)
        if valor is not None and valor not in permitidos:
            return Violacao(
                "precisao",
                f"valor fora do enum em {nome}: {valor!r}"
            )
        return None
    return _v
