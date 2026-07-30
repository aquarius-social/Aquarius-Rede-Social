"""Resolvedor de identidade por convergência de sinais.

Implementa o procedimento da seção 5.3 da Metodologia de Dados, com dois tempos
e ordem essencial:

    "Primeiro aplicam-se as condições necessárias, que eliminam candidatos:
     mandato vigente na data do fato, casa compatível, período compatível; quem
     não os satisfaz sai do conjunto de candidatos. Só então somam-se as
     evidências entre os que restaram."

Inverter essa ordem é um dos doze modos de falha catalogados (Tabela 9:
"Condição necessária tratada como evidência" — candidato fora de mandato somava
pontos, fabricando ambiguidade).

E a regra de independência, que é o que impede confiança fabricada:

    "Sinais só se somam quando erram por motivos diferentes: o nome parlamentar
     e o nome civil derivam do mesmo cadastro e falham juntos; o município de
     nascimento implica a unidade federativa, e contá-los como dois fabrica
     confiança."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from .normalizacao import (
    VERSAO_REGRA as VERSAO_NORMALIZACAO,
    mesmo_nome,
    sufixo_geracional,
    tem_titulo_ou_patente,
)

VERSAO_REGRA = f"resolvedor-1.0.0+{VERSAO_NORMALIZACAO}"


class Grau(str, Enum):
    """Grau declarado da ligação (seção 5.3).

    Espelha o enum `grau_confianca` da migration 0001.
    """

    DIRETO = "direto"              # 2+ sinais independentes
    COM_RESSALVA = "com_ressalva"  # 1 sinal isolado
    RECUSADO = "recusado"          # sinais contraditórios


# Famílias de sinal. Sinais da MESMA família falham juntos e por isso contam
# uma única vez. É a formalização da regra de independência da seção 5.3.
class Familia(str, Enum):
    NOME = "nome"                # nome civil e nome parlamentar: mesmo cadastro
    NASCIMENTO = "nascimento"    # data de nascimento
    ORIGEM = "origem"            # município e UF de nascimento: um implica o outro


@dataclass(frozen=True)
class Mandato:
    """Uma janela de ocupação de cadeira. Espelha `vinculo_temporal`."""

    casa: str                 # 'camara' | 'senado' | 'congresso'
    inicio: date
    fim: date | None          # None = em exercício
    uf: str
    partido_sigla: str | None = None

    def vigente_em(self, quando: date) -> bool:
        if quando < self.inicio:
            return False
        return self.fim is None or quando <= self.fim


@dataclass(frozen=True)
class Candidato:
    """Um perfil que pode ser a pessoa procurada."""

    profile_id: str
    nome_parlamentar: str
    mandatos: tuple[Mandato, ...]
    nome_civil: str | None = None
    data_nascimento: date | None = None
    naturalidade_municipio: str | None = None
    naturalidade_uf: str | None = None


@dataclass(frozen=True)
class Alvo:
    """O registro a resolver, tal como veio da fonte."""

    nome: str
    # A DATA DO FATO. Não é a data de hoje.
    #
    # A seção 6.3 documenta o erro concreto de usar a composição corrente:
    # "Em ano eleitoral, ministros que reassumem o mandato deslocam os
    #  suplentes que efetivamente exerceram, e apresentaram emendas, no
    #  exercício anterior."
    data_do_fato: date
    casa: str | None = None
    nome_civil: str | None = None
    data_nascimento: date | None = None
    naturalidade_municipio: str | None = None
    naturalidade_uf: str | None = None
    uf: str | None = None


@dataclass
class Resultado:
    grau: Grau
    profile_id: str | None
    sinais: list[str] = field(default_factory=list)
    divergencia: str | None = None
    pendente_conferencia: bool = False
    versao_regra: str = VERSAO_REGRA
    # Candidatos que sobreviveram aos filtros. Exposto para auditoria.
    candidatos_apos_filtro: int = 0

    @property
    def resolvido(self) -> bool:
        return self.grau in (Grau.DIRETO, Grau.COM_RESSALVA) and self.profile_id is not None


# -----------------------------------------------------------------------------
# Tempo 1 — condições necessárias (filtros)
# -----------------------------------------------------------------------------

def _passa_condicoes_necessarias(cand: Candidato, alvo: Alvo) -> bool:
    """Elimina candidatos. NÃO produz pontuação — essa é a distinção que a
    Tabela 9 identifica como modo de falha quando confundida."""
    mandatos = cand.mandatos
    if alvo.casa is not None:
        mandatos = tuple(m for m in mandatos if m.casa == alvo.casa)
        if not mandatos:
            return False
    # Mandato vigente na data do fato.
    if not any(m.vigente_em(alvo.data_do_fato) for m in mandatos):
        return False
    return True


# -----------------------------------------------------------------------------
# Tempo 2 — evidências, apenas entre os sobreviventes
# -----------------------------------------------------------------------------

def _coletar_sinais(cand: Candidato, alvo: Alvo) -> tuple[dict[Familia, str], list[str]]:
    """Devolve (sinais por família, contradições).

    Uma família contribui no máximo uma vez, por mais evidências que tenha
    dentro dela.
    """
    sinais: dict[Familia, str] = {}
    contradicoes: list[str] = []

    # --- Família NOME ---------------------------------------------------------
    # nome civil é o sinal forte (a seção 6.1 mediu: não colidiu no universo
    # examinado). O nome parlamentar colide em seis casos, e deriva do mesmo
    # cadastro — por isso não soma em cima do nome civil.
    if alvo.nome_civil and cand.nome_civil:
        if mesmo_nome(alvo.nome_civil, cand.nome_civil):
            sinais[Familia.NOME] = "nome_civil"
        else:
            # Nome civil presente dos dois lados e divergente é CONTRADIÇÃO,
            # sempre — não ausência de sinal.
            #
            # A distinção importa: sem ela, a data de nascimento sozinha
            # bastaria para aceitar duas pessoas distintas nascidas no mesmo
            # dia. A seção 6.1 mediu que a data isolada colide em nove por
            # cento do universo, com até quatro parlamentares no mesmo dia, e
            # registra que os dez pares assim foram todos rejeitados pela
            # exigência de segundo sinal, sem falso aceite.
            #
            # O sufixo geracional entra como detalhe da mensagem quando é a
            # marca que separa (seção 6.2, o caso pai e filho), mas não é
            # condição para reconhecer a contradição.
            sa = sufixo_geracional(alvo.nome_civil)
            sc = sufixo_geracional(cand.nome_civil)
            if sa != sc:
                contradicoes.append(
                    "nome civil divergente por sufixo geracional: "
                    f"{sa or 'nenhum'} != {sc or 'nenhum'}"
                )
            else:
                contradicoes.append("nome civil divergente")
    elif mesmo_nome(alvo.nome, cand.nome_parlamentar):
        sinais[Familia.NOME] = "nome_parlamentar"

    # --- Família NASCIMENTO ---------------------------------------------------
    if alvo.data_nascimento and cand.data_nascimento:
        if alvo.data_nascimento == cand.data_nascimento:
            sinais[Familia.NASCIMENTO] = "data_nascimento"
        else:
            contradicoes.append(
                f"data de nascimento divergente: {alvo.data_nascimento} != {cand.data_nascimento}"
            )

    # --- Família ORIGEM -------------------------------------------------------
    # Município implica UF. Contar os dois fabrica confiança (seção 5.3).
    if alvo.naturalidade_municipio and cand.naturalidade_municipio:
        if mesmo_nome(alvo.naturalidade_municipio, cand.naturalidade_municipio):
            sinais[Familia.ORIGEM] = "naturalidade_municipio"
        else:
            contradicoes.append("município de nascimento divergente")
    elif alvo.naturalidade_uf and cand.naturalidade_uf:
        if alvo.naturalidade_uf == cand.naturalidade_uf:
            sinais[Familia.ORIGEM] = "naturalidade_uf"
        else:
            contradicoes.append(
                f"UF de nascimento divergente: {alvo.naturalidade_uf} != {cand.naturalidade_uf}"
            )

    return sinais, contradicoes


def resolver(alvo: Alvo, universo: list[Candidato]) -> Resultado:
    """Resolve um alvo contra o universo de candidatos.

    Ordem obrigatória: filtros primeiro, evidências depois, grau declarado.
    """
    # Tempo 1 — filtros.
    sobreviventes = [c for c in universo if _passa_condicoes_necessarias(c, alvo)]

    if not sobreviventes:
        return Resultado(
            grau=Grau.RECUSADO,
            profile_id=None,
            divergencia=(
                "nenhum candidato com mandato vigente em "
                f"{alvo.data_do_fato.isoformat()}"
                + (f" na casa {alvo.casa}" if alvo.casa else "")
            ),
            candidatos_apos_filtro=0,
        )

    # Tempo 2 — evidências.
    avaliados: list[tuple[Candidato, dict[Familia, str], list[str]]] = []
    for cand in sobreviventes:
        sinais, contradicoes = _coletar_sinais(cand, alvo)
        if sinais and not contradicoes:
            avaliados.append((cand, sinais, contradicoes))

    if not avaliados:
        # Nenhuma convergência. Se o nome carrega título/patente, é o resíduo
        # que a seção 6.3 manda deixar para conferência humana em vez de
        # aproximar por regra.
        pendente = tem_titulo_ou_patente(alvo.nome)
        return Resultado(
            grau=Grau.RECUSADO,
            profile_id=None,
            divergencia=(
                "variante de nome não aproximável por regra (título ou patente)"
                if pendente
                else "nenhum sinal convergente entre os candidatos elegíveis"
            ),
            pendente_conferencia=pendente,
            candidatos_apos_filtro=len(sobreviventes),
        )

    # Mais de um candidato convergente = ambiguidade real. Recusa com a
    # divergência exposta; jamais escolher o mais provável (seção 5.3).
    if len(avaliados) > 1:
        ids = ", ".join(sorted(c.profile_id for c, _, _ in avaliados))
        return Resultado(
            grau=Grau.RECUSADO,
            profile_id=None,
            divergencia=f"ambiguidade: {len(avaliados)} candidatos convergem ({ids})",
            pendente_conferencia=True,
            candidatos_apos_filtro=len(sobreviventes),
        )

    cand, sinais, _ = avaliados[0]
    nomes_sinais = sorted(sinais.values())

    # Grau declarado pelo número de FAMÍLIAS independentes que convergiram.
    if len(sinais) >= 2:
        grau = Grau.DIRETO
    else:
        grau = Grau.COM_RESSALVA

    return Resultado(
        grau=grau,
        profile_id=cand.profile_id,
        sinais=nomes_sinais,
        pendente_conferencia=(grau is Grau.COM_RESSALVA),
        candidatos_apos_filtro=len(sobreviventes),
    )


# -----------------------------------------------------------------------------
# Autoria de emenda — o identificador embutido no código (seção 6.3)
# -----------------------------------------------------------------------------

def extrair_codigo_autor(codigo_emenda: str) -> str | None:
    """Extrai o identificador de autor embutido no código da emenda.

    A seção 6.3 documenta o achado: "nos 6.310 registros do exercício de 2025,
    seus dígitos formam 628 códigos para 628 nomes, em bijeção perfeita".

    ATENÇÃO — o layout exato do código NÃO consta da Metodologia em prosa e
    NÃO pôde ser verificado contra a fonte viva neste ambiente. Esta função é
    um ponto de extensão: o recorte real precisa ser confirmado contra o
    conjunto completo de um exercício, e a bijeção reverificada, antes de
    entrar em regime. Ver `verificar_bijecao_autoria`.
    """
    raise NotImplementedError(
        "Layout do código de emenda pendente de verificação contra a fonte real. "
        "Ver Metodologia de Dados, seção 6.3."
    )


def verificar_bijecao_autoria(
    registros: list[tuple[str, str]]
) -> tuple[bool, dict[str, set[str]]]:
    """Verifica se código de autor e nome estão em bijeção no exercício.

    Recebe pares (codigo_autor, nome_autor) e devolve (é_bijecao, violacoes).

    Esta é uma verificação de conjunto, não de amostra — a seção 4 fixa a régua:
    "a afirmação de uma ausência exige o conjunto inteiro, porque é o tipo de
    asserção que uma amostra não sustenta".
    """
    por_codigo: dict[str, set[str]] = {}
    por_nome: dict[str, set[str]] = {}
    for codigo, nome in registros:
        por_codigo.setdefault(codigo, set()).add(nome)
        por_nome.setdefault(nome, set()).add(codigo)

    violacoes = {c: n for c, n in por_codigo.items() if len(n) > 1}
    violacoes.update({n: c for n, c in por_nome.items() if len(c) > 1})
    return (not violacoes), violacoes
