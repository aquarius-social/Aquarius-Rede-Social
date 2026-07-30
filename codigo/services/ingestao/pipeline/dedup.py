"""Deduplicação por conteúdo.

Seção 3.3: "A reconciliação por conteúdo descarta as repetições da releitura,
e a diferença entre coletas sucessivas é aproveitada como instrumento de
verificação (seção 5.4)."

E seção 5.3 do PRD_agent: "upsert on conflict em Python para manter a
integridade da tabela de Posts".

A dedup opera sobre CONTEÚDO (hash), não sobre id da fonte. Isso porque duas
coletas do mesmo id com payloads diferentes NÃO são repetição — são o
instrumento que detecta edição retroativa (seção 3.4).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .camadas import RegistroBronze


@dataclass
class ResultadoDedup:
    novos: list[RegistroBronze] = field(default_factory=list)
    repetidos: list[RegistroBronze] = field(default_factory=list)
    alterados: list[tuple[RegistroBronze, RegistroBronze]] = field(default_factory=list)
    """Pares (anterior, atual) para o mesmo id de fonte com hashes distintos.

    Este é o sinal da seção 5.4: comparação temporal entre coletas detectou
    edição retroativa em despesas. NÃO é erro — é achado que exige inspeção.
    """


def deduplicar(
    novos: list[RegistroBronze],
    ja_vistos_por_id: dict[str, RegistroBronze],
    chave_id: str,
) -> ResultadoDedup:
    """Compara uma leva de bronze contra o que já está em banco.

    `ja_vistos_por_id` é o índice (id_da_fonte -> último bronze conhecido).
    `chave_id` é o campo do payload que identifica o item na fonte.
    """
    resultado = ResultadoDedup()
    for atual in novos:
        id_fonte = atual.payload.get(chave_id)
        if id_fonte is None:
            # Sem chave de fonte, é sempre novo. Não podemos afirmar repetição
            # sem uma âncora — melhor errar para o lado da preservação.
            resultado.novos.append(atual)
            continue

        anterior = ja_vistos_por_id.get(str(id_fonte))
        if anterior is None:
            resultado.novos.append(atual)
        elif anterior.hash_conteudo == atual.hash_conteudo:
            resultado.repetidos.append(atual)
        else:
            resultado.alterados.append((anterior, atual))
    return resultado
