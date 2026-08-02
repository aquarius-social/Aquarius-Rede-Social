"""Orquestrador da ingestão da Câmara — uma rodada, na ordem certa.

Amarra os coletores e o repositório respeitando as chaves estrangeiras e a
disciplina de identidade. A ordem NÃO é arbitrária:

    0. Partidos    → bronze + profiles(tipo=partido) + partido (alvo do vínculo)
    1. Deputados   → bronze + profiles + id_externo
    2. (lookups: id_externo e partido-por-sigla, montados do banco)
    2b. Histórico  → bronze + vinculo_temporal (partido/UF/ocupação por vigência;
                     partido_id resolvido por sigla)
    2c. Despesas   → bronze + despesa (CEAP por parlamentar; o passo mais volumoso)
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
from camara.coletivos import (
    FONTE_COMISSOES, FONTE_FRENTES, rodada_comissoes, rodada_frentes,
)
from camara.deputados import rodada_deputados, ResultadoRodadaDeputados
from camara.despesas import rodada_despesas
from camara.discursos import rodada_discursos
from camara.eventos import rodada_eventos
from camara.mandatos import rodada_historico
from camara.partidos import rodada_partidos
from camara.proposicoes import ResultadoRodada
from camara.tramitacoes import rodada_tramitacoes
from camara.votacoes import ResultadoRodadaVotacoes, rodada_votacoes
from contrato.canario import EstadoContrato
from persistencia.repositorio import (
    BASE_CAMARA,
    BASE_SENADO,
    ClienteBanco,
    lookup_id_externo,
    lookup_partido_por_sigla,
    salvar_bronze,
    salvar_autores_orcamentarios,
    salvar_deputados,
    salvar_despesas,
    salvar_despesas_senado,
    salvar_discursos,
    salvar_eventos,
    salvar_partidos,
    salvar_perfis_coletivos,
    salvar_proposicoes,
    salvar_senadores,
    salvar_tramitacoes,
    salvar_vinculos_temporais,
    salvar_emendas,
    salvar_votacoes,
    salvar_votos_nominais,
)
from pipeline.coletor import ClienteHttp, JanelaMovel, PoliticaRetry
from resolucao.normalizacao import normalizar
from senado.coletivos import (
    FONTE_BLOCOS_SENADO, FONTE_COMISSOES_SENADO,
    rodada_blocos_senado, rodada_comissoes_senado,
)
from senado.despesas import rodada_ceaps
from senado.discursos import rodada_discursos_senado
from senado.eventos import rodada_eventos_senado
from senado.mandatos import rodada_mandatos_senado
from senado.materias import rodada_materias
from senado.senadores import rodada_senadores
from senado.tramitacoes import rodada_tramitacoes_senado
from senado.votacoes import rodada_votacoes_senado
from transparencia.autores import rodada_autores
from transparencia.emendas import rodada_emendas

_PROCESSAVEL = (EstadoContrato.OK, EstadoContrato.ALERTA)


@dataclass
class LinhasBase:
    """Linhas de base de campos por área para o teste de contrato (§19). None em
    todas na primeira rodada — o baseline é aprendido depois."""
    partidos: frozenset[str] | None = None
    comissoes: frozenset[str] | None = None
    frentes: frozenset[str] | None = None
    deputados: frozenset[str] | None = None
    proposicoes: frozenset[str] | None = None
    votacoes: frozenset[str] | None = None
    tramitacoes: frozenset[str] | None = None
    historico: frozenset[str] | None = None
    despesas: frozenset[str] | None = None
    emendas: frozenset[str] | None = None
    autores: frozenset[str] | None = None
    senadores: frozenset[str] | None = None
    discursos: frozenset[str] | None = None
    discursos_senado: frozenset[str] | None = None
    eventos: frozenset[str] | None = None
    eventos_senado: frozenset[str] | None = None
    materias_senado: frozenset[str] | None = None
    tramitacoes_senado: frozenset[str] | None = None
    votacoes_senado: frozenset[str] | None = None
    comissoes_senado: frozenset[str] | None = None
    blocos_senado: frozenset[str] | None = None
    mandatos_senado: frozenset[str] | None = None
    ceaps: frozenset[str] | None = None


@dataclass
class ResultadoIngestao:
    deputados: ResultadoRodadaDeputados
    proposicoes: ResultadoRodada
    votacoes: ResultadoRodadaVotacoes
    partidos_salvos: int = 0
    comissoes_salvas: int = 0
    frentes_salvas: int = 0
    perfis_salvos: int = 0
    vinculos_salvos: int = 0
    despesas_salvas: int = 0
    emendas_salvas: int = 0
    # Curadoria autor-de-emenda → perfil (§6.3): resolvidos por braço.
    autores_camara_resolvidos: int = 0
    autores_senado_resolvidos: int = 0
    # Senado (§17): perfis novos, os vinculados a um deputado (mesma pessoa), e
    # os marcados pendentes de conferência (match por 1 sinal só).
    senadores_novos: int = 0
    senadores_vinculados: int = 0
    senadores_pendentes: int = 0
    # Discursos das duas casas (Área G): total persistido (câmara + senado).
    discursos_salvos: int = 0
    # Eventos das duas casas (área nova): agenda legislativa.
    eventos_salvos: int = 0
    # Matérias do Senado (proposições, Área B bicameral).
    materias_senado_salvas: int = 0
    # Tramitações do Senado (Área D bicameral).
    tramitacoes_senado_salvas: int = 0
    # Perfis coletivos do Senado (comissões + blocos — o tipo 'bloco' estreia).
    comissoes_senado_salvas: int = 0
    blocos_senado_salvos: int = 0
    # Mandato histórico do Senado → vinculo_temporal (partido/UF por período, §4).
    vinculos_senado_salvos: int = 0
    # Despesas CEAPS do Senado (Área A bicameral).
    despesas_senado_salvas: int = 0
    # Votações + votos nominais do Senado (Área C bicameral).
    votacoes_senado_salvas: int = 0
    votos_senado_salvos: int = 0
    # Divergências placar × nominais do Senado (§5.2), por votação.
    placar_violacoes_senado: dict = field(default_factory=dict)
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
    coletar_despesas: bool = True,
    ano_despesas: int | None = None,
    cliente_transparencia: ClienteHttp | None = None,
    anos_emendas: list[int] | None = None,
    abrir_mapa_autores: "Callable[[], str] | None" = None,
    coletar_senado: bool = False,
    legislatura_senado: int | None = None,
    coletar_discursos: bool = False,
    coletar_eventos: bool = False,
    baixar_ceaps: "Callable[[str], str] | None" = None,
    anos_ceaps: list[int] | None = None,
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

    # -- 0b. Perfis coletivos: comissões + frentes (§12, Concepção §7) -------
    com = rodada_comissoes(
        cliente_http, canario_validado=canario_validado,
        linha_base=base.comissoes, politica=politica)
    bronze_salvo += salvar_bronze(banco, com.bronze)
    comissoes_salvas = 0
    if com.estado in _PROCESSAVEL and com.prata is not None:
        comissoes_salvas = salvar_perfis_coletivos(
            banco, com.prata.aprovados, source=FONTE_COMISSOES)

    fre = rodada_frentes(
        cliente_http, canario_validado=canario_validado,
        linha_base=base.frentes, politica=politica)
    bronze_salvo += salvar_bronze(banco, fre.bronze)
    frentes_salvas = 0
    if fre.estado in _PROCESSAVEL and fre.prata is not None:
        frentes_salvas = salvar_perfis_coletivos(
            banco, fre.prata.aprovados, source=FONTE_FRENTES)

    # -- 0c. Perfis coletivos do Senado: comissões + blocos ------------------
    # Polimórficos (mesma tabela profiles). O tipo 'bloco' estreia aqui. Sob o
    # gate do Senado; independem de senadores/matérias.
    comissoes_senado_salvas = blocos_senado_salvos = 0
    if coletar_senado:
        csen = rodada_comissoes_senado(
            cliente_http, canario_validado=canario_validado,
            linha_base=base.comissoes_senado, politica=politica)
        bronze_salvo += salvar_bronze(banco, csen.bronze, chave_id="Codigo")
        if csen.estado in _PROCESSAVEL and csen.prata is not None:
            comissoes_senado_salvas = salvar_perfis_coletivos(
                banco, csen.prata.aprovados, source=FONTE_COMISSOES_SENADO,
                source_url=BASE_SENADO)

        bsen = rodada_blocos_senado(
            cliente_http, canario_validado=canario_validado,
            linha_base=base.blocos_senado, politica=politica)
        bronze_salvo += salvar_bronze(banco, bsen.bronze, chave_id="CodigoBloco")
        if bsen.estado in _PROCESSAVEL and bsen.prata is not None:
            blocos_senado_salvos = salvar_perfis_coletivos(
                banco, bsen.prata.aprovados, source=FONTE_BLOCOS_SENADO,
                source_url=BASE_SENADO)

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
    candidatos_dep: list[dict] = []
    if dep.estado in _PROCESSAVEL and dep.prata is not None:
        pids_dep = salvar_deputados(banco, dep.prata.aprovados)
        perfis = len(pids_dep)
        # Candidatos para a junção bicameral (§17): cada deputado com seu
        # profile_id e os sinais §5.3 (nome civil/nascimento/naturalidade).
        candidatos_dep = [
            {"profile_id": pid, **d} for pid, d in zip(pids_dep, dep.prata.aprovados)
        ]

    # -- 1c. Senadores: profiles + id_externo(senado) + junção bicameral -----
    # Depois dos deputados (candidatos do match) e antes dos lookups. O senador
    # que já é deputado ingerido NÃO vira perfil novo — anexa-se o id_externo do
    # Senado ao perfil existente (§17). Fonte pública, sem chave; gated para não
    # pesar a rodada leve. Reusa o lookup_partido do passo 0.
    senadores_novos = senadores_vinculados = senadores_pendentes = 0
    senadores_prata = None
    if coletar_senado:
        sen = rodada_senadores(
            cliente_http, canario_validado=canario_validado,
            linha_base=base.senadores, legislatura=legislatura_senado,
            politica=politica)
        bronze_salvo += salvar_bronze(
            banco, sen.bronze,
            id_na_fonte_de=lambda r: str(
                (r.payload.get("IdentificacaoParlamentar") or {})
                .get("CodigoParlamentar")))
        if sen.estado in _PROCESSAVEL and sen.prata is not None:
            senadores_prata = sen.prata
            c = salvar_senadores(banco, sen.prata.aprovados, candidatos_dep)
            senadores_novos = c["novos"]
            senadores_vinculados = c["vinculados"]
            senadores_pendentes = c["pendentes"]

    # -- 2. Lookup real de id_externo (respaldado pelo banco) ----------------
    lookup = lookup_id_externo(banco)

    # Mapa nome parlamentar normalizado → perfil dos senadores ingeridos.
    # Usado onde a fonte identifica o senador por NOME (CEAPS; curadoria de
    # autores de emenda) — §6.2.
    lookup_senador_nome = None
    if senadores_prata is not None:
        _mapa_sen = {}
        for s in senadores_prata.aprovados:
            pid = lookup("senado", s["id_fonte"])
            if pid and s.get("nome"):
                _mapa_sen[normalizar(s["nome"])] = pid
        lookup_senador_nome = lambda nome: _mapa_sen.get(normalizar(nome or ""))

    # -- 2s. Mandato histórico do Senado → vinculo_temporal (§4/§17) ----------
    # Depois do lookup (o senador já tem id_externo). Uma rodada por senador
    # (81, endpoint estável). Períodos partidários acurados — corrige o §4
    # "partido no presente". Resolve partido_id por sigla como a Câmara.
    vinculos_senado_salvos = 0
    if coletar_senado and senadores_prata is not None:
        for s in senadores_prata.aprovados:
            rms = rodada_mandatos_senado(
                cliente_http, s["id_fonte"],
                canario_validado=canario_validado, linha_base=base.mandatos_senado,
                politica=politica)
            bronze_salvo += salvar_bronze(banco, rms.bronze, chave_id="CodigoMandato")
            if rms.estado in _PROCESSAVEL and rms.vinculos:
                vinculos_senado_salvos += salvar_vinculos_temporais(
                    banco, rms.vinculos, lookup, lookup_partido=lookup_partido,
                    source="senado.mandatos", source_url=BASE_SENADO)

    # -- 2c-senado. Despesas CEAPS do Senado (Área A) — CSV por exercício -----
    # Fonte CSV (não JSON), resolvida por NOME. Constrói o mapa nome→perfil dos
    # senadores já ingeridos. Só roda com um fetcher (baixar_ceaps) + anos.
    despesas_senado_salvas = 0
    if (coletar_senado and baixar_ceaps is not None and anos_ceaps
            and lookup_senador_nome is not None):
        for ano in anos_ceaps:
            rce = rodada_ceaps(
                baixar_ceaps, ano, canario_validado=canario_validado,
                linha_base=base.ceaps)
            bronze_salvo += salvar_bronze(banco, rce.bronze, chave_id="COD_DOCUMENTO")
            if rce.estado in _PROCESSAVEL and rce.prata is not None:
                despesas_senado_salvas += salvar_despesas_senado(
                    banco, rce.prata.aprovados, lookup_senador_nome)

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

    # -- 2c. Despesas / CEAP por parlamentar (§8) — o passo mais volumoso ----
    despesas_salvas = 0
    if (coletar_despesas and dep.estado in _PROCESSAVEL
            and dep.prata is not None):
        ano = ano_despesas or ate.year
        for d in dep.prata.aprovados:
            rd = rodada_despesas(
                cliente_http, d["id_fonte"], ano=ano,
                canario_validado=canario_validado,
                linha_base=base.despesas, politica=politica)
            # Bronze de despesa: id composto deputado:documento:parcela.
            bronze_salvo += salvar_bronze(
                banco, rd.bronze,
                id_na_fonte_de=lambda r, did=d["id_fonte"]: (
                    f"{did}:{r.payload.get('codDocumento')}:{r.payload.get('parcela')}"
                ))
            if rd.estado in _PROCESSAVEL and rd.prata is not None:
                despesas_salvas += salvar_despesas(banco, rd.prata.aprovados, lookup)

    # -- 2ca. Curadoria: autor de emenda → perfil (§6.3) ---------------------
    # ANTES das emendas, para que o lookup('autor_orcamentario', ...) resolva.
    # Materializa o mapa curado como id_externo. Dois braços (§17): deputado_id
    # (Câmara) e nome→senador (os que o mapa não achou por só tentar a Câmara).
    autores_camara_resolvidos = autores_senado_resolvidos = 0
    if abrir_mapa_autores is not None:
        ra = rodada_autores(
            abrir_mapa_autores, canario_validado=canario_validado,
            linha_base=base.autores)
        bronze_salvo += salvar_bronze(banco, ra.bronze, chave_id="codigo_autor")
        if ra.estado in _PROCESSAVEL and ra.prata is not None:
            ca = salvar_autores_orcamentarios(
                banco, ra.prata.aprovados, lookup, lookup_senador_nome)
            autores_camara_resolvidos = ca["camara"]
            autores_senado_resolvidos = ca["senado"]

    # -- 2d. Emendas orçamentárias (Área F, §13) — fonte Transparência -------
    # Só roda se um cliente da Transparência (com a chave) e anos forem dados.
    # Autor resolvido por id_externo 'autor_orcamentario' (§6.3) — null enquanto
    # o mapa de autores não é carregado por curadoria (furo conhecido).
    emendas_salvas = 0
    if cliente_transparencia is not None and anos_emendas:
        for ano in anos_emendas:
            re_ = rodada_emendas(
                cliente_transparencia, ano,
                canario_validado=canario_validado,
                linha_base=base.emendas, politica=politica)
            bronze_salvo += salvar_bronze(
                banco, re_.bronze, chave_id="codigoEmenda")
            if re_.estado in _PROCESSAVEL and re_.prata is not None:
                emendas_salvas += salvar_emendas(banco, re_.prata.aprovados, lookup)

    # -- 2e. Discursos das DUAS casas (Área G) — por parlamentar, na janela ---
    # Bicameral: Câmara (por deputado) + Senado (por senador). Volumoso, gated.
    # O autor resolve pelo lookup (passo 2); sem perfil, o discurso é pulado.
    discursos_salvos = 0
    if coletar_discursos:
        d_ini, d_fim = janela.intervalo(ate)
        if dep.estado in _PROCESSAVEL and dep.prata is not None:
            for d in dep.prata.aprovados:
                rdi = rodada_discursos(
                    cliente_http, d["id_fonte"],
                    canario_validado=canario_validado, linha_base=base.discursos,
                    data_inicio=d_ini.isoformat(), data_fim=d_fim.isoformat(),
                    politica=politica)
                bronze_salvo += salvar_bronze(
                    banco, rdi.bronze,
                    id_na_fonte_de=lambda r, did=d["id_fonte"]: (
                        f"{did}:{r.payload.get('dataHoraInicio')}"))
                if rdi.estado in _PROCESSAVEL and rdi.prata is not None:
                    discursos_salvos += salvar_discursos(
                        banco, rdi.prata.aprovados, lookup,
                        source="camara.discursos", source_url=BASE_CAMARA)
        if senadores_prata is not None:
            for s in senadores_prata.aprovados:
                rds = rodada_discursos_senado(
                    cliente_http, s["id_fonte"],
                    canario_validado=canario_validado,
                    linha_base=base.discursos_senado,
                    data_inicio=d_ini.isoformat(), data_fim=d_fim.isoformat(),
                    politica=politica)
                bronze_salvo += salvar_bronze(
                    banco, rds.bronze, chave_id="CodigoPronunciamento")
                if rds.estado in _PROCESSAVEL and rds.prata is not None:
                    discursos_salvos += salvar_discursos(
                        banco, rds.prata.aprovados, lookup,
                        source="senado.discursos", source_url=BASE_SENADO)

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

    # -- 3c. Matérias do Senado (proposições, bicameral §17) -----------------
    # Mesma tabela `proposicao` (casa_origem='senado'), mesma janela móvel. Sob
    # o mesmo gate do Senado. Tramitações/votações do Senado são passos próprios.
    materias_senado_salvas = 0
    tramitacoes_senado_salvas = 0
    if coletar_senado:
        m_ini, m_fim = janela.intervalo(ate)
        rm = rodada_materias(
            cliente_http, data_inicio=m_ini.isoformat(), data_fim=m_fim.isoformat(),
            canario_validado=canario_validado, linha_base=base.materias_senado,
            politica=politica)
        bronze_salvo += salvar_bronze(banco, rm.bronze, chave_id="Codigo")
        if rm.estado in _PROCESSAVEL and rm.prata is not None:
            materias_senado_salvas = salvar_proposicoes(
                banco, rm.prata.aprovados,
                source="senado.materias", source_url=BASE_SENADO)

            # Tramitações do Senado: uma rodada por matéria, via /processo/{id}
            # (endpoint substituto — o antigo /movimentacoes foi descontinuado).
            # Prende-se à matéria já persistida (FK), como na Câmara.
            for m in rm.prata.aprovados:
                id_proc = m.get("id_processo")
                if not id_proc:
                    continue
                rts = rodada_tramitacoes_senado(
                    cliente_http, id_proc, m["id_fonte"],
                    canario_validado=canario_validado,
                    linha_base=base.tramitacoes_senado, politica=politica)
                bronze_salvo += salvar_bronze(banco, rts.bronze, chave_id="id")
                if rts.estado in _PROCESSAVEL and rts.prata is not None:
                    tramitacoes_senado_salvas += salvar_tramitacoes(
                        banco, rts.prata.aprovados,
                        source="senado.tramitacoes", source_url=BASE_SENADO)

    # -- 3e. Eventos das DUAS casas (área nova) — agenda legislativa ----------
    # Câmara por janela de data; Senado por mês (a agenda de comissões é mensal).
    # O órgão resolve ao perfil da comissão pelo slug (null p/ plenário). Gated.
    eventos_salvos = 0
    if coletar_eventos:
        ev_ini, ev_fim = janela.intervalo(ate)
        rev = rodada_eventos(
            cliente_http, data_inicio=ev_ini.isoformat(), data_fim=ev_fim.isoformat(),
            canario_validado=canario_validado, linha_base=base.eventos)
        bronze_salvo += salvar_bronze(banco, rev.bronze)
        if rev.estado in _PROCESSAVEL and rev.prata is not None:
            eventos_salvos += salvar_eventos(
                banco, rev.prata.aprovados,
                source="camara.eventos", source_url=BASE_CAMARA)
        # Senado: um mês por consulta; cobre os meses tocados pela janela.
        y, m = ev_ini.year, ev_ini.month
        while (y, m) <= (ev_fim.year, ev_fim.month):
            revs = rodada_eventos_senado(
                cliente_http, f"{y}{m:02d}",
                canario_validado=canario_validado, linha_base=base.eventos_senado)
            bronze_salvo += salvar_bronze(banco, revs.bronze, chave_id="codigo")
            if revs.estado in _PROCESSAVEL and revs.prata is not None:
                eventos_salvos += salvar_eventos(
                    banco, revs.prata.aprovados,
                    source="senado.eventos", source_url=BASE_SENADO)
            m += 1
            if m > 12:
                m = 1
                y += 1

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

    # -- 5b. Votações + votos nominais do Senado (bicameral §10/§5.2) ---------
    # Placar e nominais vêm inline do /votacao (substituto). Resolve o senador
    # pelo mesmo lookup (id_externo sistema='senado'). Secreta não tem nominal.
    votacoes_senado_salvas = votos_senado_salvos = 0
    placar_violacoes_senado: dict = {}
    if coletar_senado:
        vs_ini, vs_fim = janela.intervalo(ate)
        rvs = rodada_votacoes_senado(
            cliente_http, data_inicio=vs_ini.isoformat(), data_fim=vs_fim.isoformat(),
            canario_validado=canario_validado, linha_base=base.votacoes_senado,
            lookup=lookup, politica=politica)
        bronze_salvo += salvar_bronze(banco, rvs.bronze, chave_id="codigoSessaoVotacao")
        if rvs.estado in _PROCESSAVEL and rvs.votacoes_prata is not None:
            votacoes_senado_salvas = salvar_votacoes(
                banco, rvs.votacoes_prata.aprovados,
                source="senado.votacoes", source_url=BASE_SENADO)
            for idf, resolvidos in rvs.nominais.items():
                votos_senado_salvos += salvar_votos_nominais(
                    banco, idf, resolvidos, casa="senado")
            placar_violacoes_senado = rvs.placar_violacoes

    return ResultadoIngestao(
        deputados=dep, proposicoes=prop, votacoes=vot,
        partidos_salvos=partidos_salvos,
        comissoes_salvas=comissoes_salvas,
        frentes_salvas=frentes_salvas,
        perfis_salvos=perfis,
        vinculos_salvos=vinculos_salvos,
        despesas_salvas=despesas_salvas,
        emendas_salvas=emendas_salvas,
        autores_camara_resolvidos=autores_camara_resolvidos,
        autores_senado_resolvidos=autores_senado_resolvidos,
        senadores_novos=senadores_novos,
        senadores_vinculados=senadores_vinculados,
        senadores_pendentes=senadores_pendentes,
        discursos_salvos=discursos_salvos,
        eventos_salvos=eventos_salvos,
        comissoes_senado_salvas=comissoes_senado_salvas,
        blocos_senado_salvos=blocos_senado_salvos,
        vinculos_senado_salvos=vinculos_senado_salvos,
        despesas_senado_salvas=despesas_senado_salvas,
        materias_senado_salvas=materias_senado_salvas,
        tramitacoes_senado_salvas=tramitacoes_senado_salvas,
        votacoes_senado_salvas=votacoes_senado_salvas,
        votos_senado_salvos=votos_senado_salvos,
        placar_violacoes_senado=placar_violacoes_senado,
        proposicoes_salvas=proposicoes_salvas,
        tramitacoes_salvas=tramitacoes_salvas,
        votacoes_salvas=votacoes_salvas,
        votos_salvos=votos_salvos,
        bronze_salvo=bronze_salvo,
        placar_violacoes=vot.placar_violacoes,
    )
