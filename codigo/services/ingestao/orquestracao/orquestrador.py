"""Orquestrador da ingestão da Câmara — uma rodada, na ordem certa.

Amarra os coletores e o repositório respeitando as chaves estrangeiras e a
disciplina de identidade. A ordem NÃO é arbitrária:

    0. Partidos    → bronze + profiles(tipo=partido) + partido (alvo do vínculo)
    1. Deputados   → bronze + profiles + id_externo
    2. (lookups: id_externo e partido-por-sigla, montados do banco)
    2b. Histórico  → bronze + vinculo_temporal (partido/UF/ocupação por vigência;
                     partido_id resolvido por sigla)
    3. Proposições → bronze + proposicao
    3b. Tramitações→ bronze + tramitacao (uma rodada por proposição; resolve proposicao_id)
    4. Votações    → bronze + votacao (resolve proposicao_id)
    5. Votos nom.  → voto_nominal (resolve votacao_id; perfil pelo lookup do passo 2)

Por que esta ordem: os votos nominais só resolvem contra perfis já ingeridos
(§6, integridade referencial). Deputados primeiro; então o lookup deixa de ser
injetado artificialmente e passa a ser a tabela `id_externo` (o que este
orquestrador prova de ponta a ponta). Proposições antes de votações para que a
votação prenda sua matéria.

HTTP e banco são INJETADOS (portas `ClienteHttp` e `ClienteBanco`), então o
fluxo inteiro é testável sem rede nem Supabase.

Contrato (§19): em FALHA/QUEBRA de uma área, sua prata NÃO é persistida (a
ingestão da área é suspensa). O bronze disponível é preservado de qualquer
modo — é cópia bruta, e preservar não fabrica nada.

Preservação de bronze completa (§3.1): lista, DETALHE e VOTOS de cada votação
são todos persistidos. O voto não tem id de fonte próprio — sua identidade é o
par (votação, deputado), gravado como `id_na_fonte = "{votacao}:{deputado}"`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from camara import proposicoes as prop_mod
from camara.deputados import rodada_deputados, ResultadoRodadaDeputados
from camara.mandatos import rodada_historico
from camara.partidos import rodada_partidos
from camara.proposicoes import ResultadoRodada
from camara.tramitacoes import rodada_tramitacoes
from camara.votacoes import ResultadoRodadaVotacoes, rodada_votacoes
from contrato.canario import EstadoContrato
from persistencia.repositorio import (
    ClienteBanco,
    lookup_id_externo,
    lookup_partido_por_sigla,
    salvar_bronze,
    salvar_deputados,
    salvar_partidos,
    salvar_proposicoes,
    salvar_tramitacoes,
    salvar_vinculos_temporais,
    salvar_votacoes,
    salvar_votos_nominais,
)
from pipeline.coletor import ClienteHttp, JanelaMovel, PoliticaRetry

_PROCESSAVEL = (EstadoContrato.OK, EstadoContrato.ALERTA)


@dataclass
class LinhasBase:
    """Linhas de base de campos por área para o teste de contrato (§19). None em
    todas na primeira rodada — o baseline é aprendido depois."""
    partidos: frozenset[str] | None = None
    deputados: frozenset[str] | None = None
    proposicoes: frozenset[str] | None = None
    votacoes: frozenset[str] | None = None
    tramitacoes: frozenset[str] | None = None
    historico: frozenset[str] | None = None


@dataclass
class ResultadoIngestao:
    deputados: ResultadoRodadaDeputados
    proposicoes: ResultadoRodada
    votacoes: ResultadoRodadaVotacoes
    partidos_salvos: int = 0
    perfis_salvos: int = 0
    vinculos_salvos: int = 0
    proposicoes_salvas: int = 0
    tramitacoes_salvas: int = 0
    votacoes_salvas: int = 0
    votos_salvos: int = 0
    bronze_salvo: int = 0
    # Divergências placar × nominais agregadas (§5.2), por votação.
    placar_violacoes: dict = field(default_factory=dict)


def ingerir(
    cliente_http: ClienteHttp,
    banco: ClienteBanco,
    *,
    ate: date,
    janela: JanelaMovel,
    id_legislatura: int | None = None,
    canario_validado: bool = True,
    linhas_base: LinhasBase | None = None,
    enriquecer_deputados: bool = True,
    coletar_historico: bool = True,
    politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoIngestao:
    """Executa uma rodada completa de ingestão da Câmara.

    `canario_validado` vale para as três fontes (refinar para um canário por
    fonte é passo próprio). `ate`/`janela` definem a janela móvel de proposições
    e votações (§3.3); deputados são por `id_legislatura`.
    """
    base = linhas_base or LinhasBase()
    bronze_salvo = 0

    # -- 0. Partidos canônicos: profiles(tipo=partido) + partido -------------
    # Primeiro, porque o vínculo temporal (passo 2b) resolve partido_id por
    # sigla contra esta tabela.
    part = rodada_partidos(
        cliente_http, canario_validado=canario_validado,
        linha_base=base.partidos, politica=politica,
    )
    bronze_salvo += salvar_bronze(banco, part.bronze)
    if part.detalhes_bronze:
        bronze_salvo += salvar_bronze(banco, part.detalhes_bronze)
    partidos_salvos = 0
    if part.estado in _PROCESSAVEL and part.prata is not None:
        partidos_salvos = salvar_partidos(banco, part.prata.aprovados)
    lookup_partido = lookup_partido_por_sigla(banco)

    # -- 1. Deputados: bronze + profiles + id_externo ------------------------
    dep = rodada_deputados(
        cliente_http,
        canario_validado=canario_validado,
        linha_base=base.deputados,
        id_legislatura=id_legislatura,
        enriquecer=enriquecer_deputados,
        politica=politica,
    )
    bronze_salvo += salvar_bronze(banco, dep.bronze)
    perfis = 0
    if dep.estado in _PROCESSAVEL and dep.prata is not None:
        perfis = len(salvar_deputados(banco, dep.prata.aprovados))

    # -- 2. Lookup real de id_externo (respaldado pelo banco) ----------------
    lookup = lookup_id_externo(banco)

    # -- 2b. Histórico de mandatos → vinculo_temporal (§12 D4, §4) -----------
    # Camada temporal dos deputados; precisa do lookup (passo 2). Uma rodada por
    # pessoa, sobre o endpoint mais instável da Câmara — falha pontual de uma
    # pessoa não derruba a ingestão (rodada_historico devolve FALHA e é pulada).
    vinculos_salvos = 0
    if (coletar_historico and dep.estado in _PROCESSAVEL
            and dep.prata is not None):
        for d in dep.prata.aprovados:
            rh = rodada_historico(
                cliente_http, d["id_fonte"],
                canario_validado=canario_validado,
                linha_base=base.historico,
                politica=politica,
            )
            # Bronze do histórico: id composto (deputado:dataHora) — o snapshot
            # não tem id próprio, todos compartilham o id do deputado.
            bronze_salvo += salvar_bronze(
                banco, rh.bronze,
                id_na_fonte_de=lambda r: (
                    f"{r.payload.get('id')}:{r.payload.get('dataHora')}"
                ),
            )
            if rh.estado in _PROCESSAVEL and rh.vinculos is not None:
                vinculos_salvos += salvar_vinculos_temporais(
                    banco, rh.vinculos.aprovados, lookup,
                    lookup_partido=lookup_partido,
                )

    # -- 3. Proposições: bronze + proposicao ---------------------------------
    prop = prop_mod.rodada(
        cliente_http,
        ate=ate, janela=janela,
        canario_validado=canario_validado,
        linha_base=base.proposicoes,
        politica=politica,
    )
    bronze_salvo += salvar_bronze(banco, prop.bronze)
    proposicoes_salvas = 0
    tramitacoes_salvas = 0
    if prop.estado in _PROCESSAVEL and prop.prata is not None:
        proposicoes_salvas = salvar_proposicoes(banco, prop.prata.aprovados)

        # -- 3b. Tramitações: uma rodada por proposição aprovada -------------
        # A tramitação prende-se à proposição já persistida (FK). Por isso vem
        # depois de salvar as proposições, e só para as que passaram o portão.
        for p in prop.prata.aprovados:
            rt = rodada_tramitacoes(
                cliente_http, p["id_fonte"],
                canario_validado=canario_validado,
                linha_base=base.tramitacoes,
                politica=politica,
            )
            bronze_salvo += salvar_bronze(banco, rt.bronze)
            if rt.estado in _PROCESSAVEL and rt.prata is not None:
                tramitacoes_salvas += salvar_tramitacoes(banco, rt.prata.aprovados)

    # -- 4/5. Votações + votos nominais --------------------------------------
    inicio, fim = janela.intervalo(ate)
    vot = rodada_votacoes(
        cliente_http,
        data_inicio=inicio.isoformat(), data_fim=fim.isoformat(),
        canario_validado=canario_validado,
        linha_base=base.votacoes,
        lookup=lookup,
        politica=politica,
    )
    bronze_salvo += salvar_bronze(banco, vot.votacoes_bronze)
    # Bronze das outras duas requisições da área (§3.1, preservação completa):
    # o detalhe de cada votação (id = id da votação) e os votos (id COMPOSTO
    # votação:deputado — o voto não tem id de fonte próprio).
    bronze_salvo += salvar_bronze(banco, vot.detalhes_bronze)
    for vid, votos_bronze in vot.votos_bronze.items():
        bronze_salvo += salvar_bronze(
            banco, votos_bronze,
            id_na_fonte_de=lambda r, vid=vid: (
                f"{vid}:{(r.payload.get('deputado_') or {}).get('id')}"
            ),
        )
    votacoes_salvas = 0
    votos_salvos = 0
    if vot.estado in _PROCESSAVEL and vot.votacoes_prata is not None:
        votacoes_salvas = salvar_votacoes(banco, vot.votacoes_prata.aprovados)
        for votacao_id_fonte, resultado_votos in vot.nominais.items():
            votos_salvos += salvar_votos_nominais(
                banco, votacao_id_fonte, resultado_votos.resolvidos
            )

    return ResultadoIngestao(
        deputados=dep, proposicoes=prop, votacoes=vot,
        partidos_salvos=partidos_salvos,
        perfis_salvos=perfis,
        vinculos_salvos=vinculos_salvos,
        proposicoes_salvas=proposicoes_salvas,
        tramitacoes_salvas=tramitacoes_salvas,
        votacoes_salvas=votacoes_salvas,
        votos_salvos=votos_salvos,
        bronze_salvo=bronze_salvo,
        placar_violacoes=vot.placar_violacoes,
    )
