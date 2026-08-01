"""Junção bicameral — o mesmo indivíduo nas duas casas (§17, §13).

O caso concreto: uma pessoa foi deputada (2019–2022) e hoje é senadora (2023–).
São dois identificadores de fonte (`camara_id` + `senado_codigo`), SEM CPF em
comum, e os mandatos NUNCA se sobrepõem no tempo. A resolução é probabilística
(Tier 2, §13): nome civil + data de nascimento + naturalidade.

Por que NÃO se reusa `resolvedor.resolver` diretamente:

    `resolver` responde "a QUEM atribuir ESTE fato, na data em que ele ocorreu?"
    e por isso aplica a condição necessária "mandato vigente na data do fato".
    Aqui a pergunta é outra — "estas duas fichas são a MESMA pessoa?" — e a
    resposta não pode exigir sobreposição temporal, que por construção não
    existe entre um mandato de deputado e um de senador subsequentes.

O que se REUSA é o núcleo que importa: `_coletar_sinais`, a regra §5.3 de
convergência por famílias INDEPENDENTES (nome, nascimento, origem — o município
implica a UF, então contam uma vez). Fonte única da disciplina de sinais: se ela
mudar, muda para os dois usos. Só o Tempo 1 (filtros) é substituído.

Disciplina preservada da §5.3:
  - 2+ famílias convergentes e nenhuma contradição → 'direto'.
  - 1 família só → 'com_ressalva', pendente de conferência humana (§13: "N
    pequeno, confirmação manual única").
  - Contradição (ex.: nascimento diferente) elimina o candidato.
  - Mais de um candidato convergindo → ambiguidade: RECUSA, nunca "o mais
    provável".
"""

from __future__ import annotations

from .resolvedor import (
    VERSAO_REGRA,
    Alvo,
    Candidato,
    Grau,
    Resultado,
    _coletar_sinais,
)

# Reexporta os tipos para quem importa daqui montar alvo e candidatos sem
# precisar conhecer o módulo `resolvedor`.
__all__ = ["Alvo", "Candidato", "Grau", "Resultado", "resolver_bicameral"]


def resolver_bicameral(alvo: Alvo, candidatos: list[Candidato]) -> Resultado:
    """Resolve a IDENTIDADE de uma pessoa (um senador) contra um universo de
    candidatos (deputados já ingeridos), SEM filtro de mandato vigente.

    Espelha o Tempo 2 de `resolver`: soma sinais por família independente entre
    os candidatos, exige ausência de contradição, e declara o grau pelo número
    de famílias. Ambiguidade recusa; sinal único fica com ressalva.
    """
    avaliados: list[tuple[Candidato, dict]] = []
    for cand in candidatos:
        sinais, contradicoes = _coletar_sinais(cand, alvo)
        if sinais and not contradicoes:
            avaliados.append((cand, sinais))

    if not avaliados:
        return Resultado(
            grau=Grau.RECUSADO,
            profile_id=None,
            divergencia="nenhum sinal convergente com deputado conhecido",
            candidatos_apos_filtro=len(candidatos),
        )

    # Mais de um candidato convergente = ambiguidade real. Recusa com a
    # divergência exposta; jamais escolher o mais provável (§5.3).
    if len(avaliados) > 1:
        ids = ", ".join(sorted(c.profile_id for c, _ in avaliados))
        return Resultado(
            grau=Grau.RECUSADO,
            profile_id=None,
            divergencia=f"ambiguidade: {len(avaliados)} deputados convergem ({ids})",
            pendente_conferencia=True,
            candidatos_apos_filtro=len(candidatos),
        )

    cand, sinais = avaliados[0]
    grau = Grau.DIRETO if len(sinais) >= 2 else Grau.COM_RESSALVA
    return Resultado(
        grau=grau,
        profile_id=cand.profile_id,
        sinais=sorted(sinais.values()),
        pendente_conferencia=(grau is Grau.COM_RESSALVA),
        versao_regra=VERSAO_REGRA,
        candidatos_apos_filtro=len(candidatos),
    )
