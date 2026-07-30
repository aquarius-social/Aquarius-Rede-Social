"""Repositório de persistência — camadas bronze e prata no Supabase.

Fecha o ciclo: os coletores produzem shapes prata; aqui eles viram linhas nas
tabelas das migrations 0001–0004. E o `lookup` de `id_externo` que os coletores
recebiam injetado passa a ser a TABELA real (`lookup_id_externo`), ligando a
resolução de votos ponta a ponta.

Disciplina (mesma dos coletores): o banco é INJETADO por uma porta (`ClienteBanco`),
para que a lógica de mapeamento e resolução de chaves seja testável sem rede nem
Supabase.

Adaptador concreto: ainda NÃO existe. O pacote `supabase` não está instalado
neste ambiente (verificado — a pasta local `supabase/` de migrations induz um
falso-positivo em `find_spec`). Quando for wireado no deploy, o adaptador
implementa os três métodos de `ClienteBanco` sobre o cliente Supabase
(service role) — `table(t).upsert(linhas, on_conflict=...).execute()`,
`insert(..., upsert=False)` e `select().eq(...).limit(1)`. Requer
`SUPABASE_URL` e `SUPABASE_SERVICE_KEY`. Não foi escrito aqui para não deixar
código não-testável contra uma dependência ausente (CLAUDE.md, regra 4).

Ordem de persistência (respeita as chaves estrangeiras, minimiza retrabalho):

    1. bronze_registro           (imutável; insert ignorando conflito)
    2. deputados → profiles + id_externo   (cria o alvo do lookup)
    3. proposicao
    4. votacao                   (resolve proposicao_id a partir do id da fonte)
    5. voto_nominal              (resolve votacao_id; perfil_id já vem resolvido)

Convenções do schema honradas aqui:
  - Proveniência (seção 3.1): `source`/`source_url` em toda linha prata.
  - `id_externo`: método 'fonte_direta', grau 'direto' (§6) — a fonte declara o
    id, então a ligação é direta e a constraint `id_externo_grau_coerente` passa.
  - `versao_regra` (§3.4): a versão da regra de ligação, para reprocessamento.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Protocol, Sequence

BASE_CAMARA = "https://dadosabertos.camara.leg.br/api/v2"

# Versão da regra de ligação id_externo (§3.4). Bump quando a regra mudar.
VERSAO_REGRA = "camara.v1"


class ClienteBanco(Protocol):
    """Porta de persistência. O adaptador real fala com o Supabase; os testes
    usam um fake em memória. Métodos deliberadamente mínimos."""

    def upsert(
        self, tabela: str, linhas: list[dict], *, conflito: str
    ) -> list[dict]:
        """Insere ou atualiza por `conflito` (colunas separadas por vírgula).
        Devolve as linhas resultantes, com `id` preenchido."""
        ...

    def inserir_ignorando_conflito(self, tabela: str, linhas: list[dict]) -> int:
        """Insere; linhas que colidem com constraint única são ignoradas.
        Devolve quantas foram efetivamente inseridas."""
        ...

    def selecionar_um(self, tabela: str, onde: dict) -> dict | None:
        """Primeira linha que casa com todos os pares de `onde`, ou None."""
        ...


# -----------------------------------------------------------------------------
# Bronze — imutável, insert ignorando conflito
# -----------------------------------------------------------------------------

def salvar_bronze(
    cliente: ClienteBanco,
    registros: Iterable[Any],
    *,
    chave_id: str = "id",
    id_na_fonte_de: Callable[[Any], str] | None = None,
) -> int:
    """Persiste registros bronze. Nunca sobrescreve: coleta é evento, não estado
    (constraint `bronze_unico_por_coleta`). `registros` são RegistroBronze.

    `id_na_fonte_de` permite id composto quando a fonte não dá um id próprio ao
    item. É o caso do VOTO: ele não tem id de fonte — sua identidade é o par
    (votação, deputado). O chamador passa `lambda r: f"{vid}:{r.payload['deputado_']['id']}"`.
    Sem o callable, cai no `payload[chave_id]` (o caso de proposição, votação,
    deputado, que têm `id`).
    """
    def _id(r: Any) -> str:
        if id_na_fonte_de is not None:
            return id_na_fonte_de(r)
        return str(r.payload.get(chave_id))

    linhas = [{
        "fonte": r.fonte,
        "fonte_url": r.fonte_url,
        "id_na_fonte": _id(r),
        "payload": r.payload,
        "hash_conteudo": r.hash_conteudo,
        "coletado_em": r.coletado_em.isoformat(),
    } for r in registros]
    if not linhas:
        return 0
    return cliente.inserir_ignorando_conflito("bronze_registro", linhas)


# -----------------------------------------------------------------------------
# Deputados → profiles + id_externo, e o lookup real
# -----------------------------------------------------------------------------

_COLS_PROFILE = (
    "tipo", "nome", "slug", "foto_url", "ativo",
    "nome_civil", "data_nascimento", "naturalidade_municipio", "naturalidade_uf",
)


def salvar_deputados(
    cliente: ClienteBanco,
    aprovados: Sequence[dict],
    *,
    source: str = "camara.deputados",
    source_url: str = BASE_CAMARA,
) -> list[str]:
    """Upsert de perfis parlamentares + vínculo id_externo. Devolve os
    profile_id (uuid) na ordem de entrada.

    Um perfil por pessoa (a lista já foi deduplicada no coletor). O upsert é por
    `slug` (estável e único por id da fonte); o id_externo por (sistema,
    identificador), que é a chave que o lookup consulta.
    """
    ids: list[str] = []
    for d in aprovados:
        linha_profile = {c: d.get(c) for c in _COLS_PROFILE}
        linha_profile["source"] = source
        linha_profile["source_url"] = source_url
        [perfil] = cliente.upsert("profiles", [linha_profile], conflito="slug")
        pid = perfil["id"]

        cliente.upsert("id_externo", [{
            "profile_id": pid,
            "sistema": d["sistema_externo"],
            "identificador": d["identificador_externo"],
            "metodo": d["metodo_ligacao"],
            "grau": d["grau"],
            "versao_regra": VERSAO_REGRA,
        }], conflito="sistema,identificador")
        ids.append(pid)
    return ids


def lookup_id_externo(cliente: ClienteBanco):
    """Fábrica do lookup real de id_externo — mesma assinatura do que os
    coletores recebiam injetado, mas agora respaldado pela tabela.

        (sistema, identificador) -> profile_id | None
    """
    def _l(sistema: str, identificador: str) -> str | None:
        row = cliente.selecionar_um(
            "id_externo",
            {"sistema": sistema, "identificador": str(identificador)},
        )
        return row["profile_id"] if row else None
    return _l


def salvar_partidos(
    cliente: ClienteBanco,
    aprovados: Sequence[dict],
    *,
    source: str = "camara.partidos",
    source_url: str = BASE_CAMARA,
) -> int:
    """Cria o partido canônico: profile (tipo='partido') + linha `partido`.
    Upsert do profile por `slug`, do partido por `profile_id`."""
    for p in aprovados:
        [prof] = cliente.upsert("profiles", [{
            "tipo": "partido",
            "nome": p["nome"],
            "sigla": p["sigla"],
            "slug": p["slug"],
            "ativo": p.get("ativo", True),
            "source": source,
            "source_url": source_url,
        }], conflito="slug")
        cliente.upsert("partido", [{
            "profile_id": prof["id"],
            "sigla_atual": p["sigla"],
            "nome_atual": p["nome"],
            "numero_urna": p.get("numero_urna"),
            "source": source,
            "source_url": source_url,
        }], conflito="profile_id")
    return len(aprovados)


def salvar_perfis_coletivos(
    cliente: ClienteBanco,
    aprovados: Sequence[dict],
    *,
    source: str,
    source_url: str = BASE_CAMARA,
) -> int:
    """Persiste perfis coletivos seguíveis (comissão, frente) — só `profiles`,
    sem tabela de domínio nem id_externo. Upsert por `slug`."""
    for p in aprovados:
        cliente.upsert("profiles", [{
            "tipo": p["tipo"],
            "nome": p["nome"],
            "sigla": p.get("sigla"),
            "slug": p["slug"],
            "ativo": p.get("ativo", True),
            "source": source,
            "source_url": source_url,
        }], conflito="slug")
    return len(aprovados)


def lookup_partido_por_sigla(cliente: ClienteBanco):
    """Fábrica do lookup de partido por sigla atual → `partido.id` (o alvo da FK
    `vinculo_temporal.partido_id`). Devolve None para sigla desconhecida
    (histórica ou 'S.PART.') — resolução por linhagem é curadoria (§4)."""
    def _l(sigla: str | None) -> str | None:
        if not sigla:
            return None
        row = cliente.selecionar_um("partido", {"sigla_atual": sigla})
        return row["id"] if row else None
    return _l


def _daterange(inicio: str, fim: str | None) -> str:
    """Literal daterange do Postgres: `[inicio, fim)` — início inclusivo, fim
    exclusivo. Fim ausente = em aberto: `[inicio,)`."""
    return f"[{inicio},{fim or ''})"


def salvar_vinculos_temporais(
    cliente: ClienteBanco,
    vinculos: Sequence[dict],
    lookup,
    *,
    lookup_partido=None,
    source: str = "camara.historico",
    source_url: str = BASE_CAMARA,
) -> int:
    """Persiste os vínculos temporais (partido/UF/ocupação por vigência, §4).

    Resolve `profile_id` pelo mesmo `lookup` de id_externo dos votos — sem o
    perfil ingerido, não há a quem prender o vínculo, pula sem inventar. Upsert
    por (profile_id, casa, vigencia): reingerir o mesmo período atualiza, não
    duplica (constraint `vinculo_temporal_unico`, migration 0005).

    `lookup_partido` (opcional) resolve `partido_id` a partir da
    `partido_sigla_fonte`. Sigla histórica ou 'S.PART.' não resolve → `partido_id`
    fica None e a sigla-fonte é preservada; resolver por linhagem é curadoria (§4).
    """
    salvos = 0
    for v in vinculos:
        perfil_id = lookup("camara", v["id_fonte"])
        if perfil_id is None:
            continue
        partido_id = v.get("partido_id")
        if partido_id is None and lookup_partido is not None:
            partido_id = lookup_partido(v.get("partido_sigla_fonte"))
        cliente.upsert("vinculo_temporal", [{
            "profile_id": perfil_id,
            "casa": v["casa"],
            "legislatura": v.get("legislatura"),
            "uf": v["uf"],
            "partido_id": partido_id,
            "partido_sigla_fonte": v.get("partido_sigla_fonte"),
            "ocupacao": v["ocupacao"],
            "vigencia": _daterange(v["vigencia_inicio"], v.get("vigencia_fim")),
            "source": source,
            "source_url": source_url,
        }], conflito="profile_id,casa,vigencia")
        salvos += 1
    return salvos


# -----------------------------------------------------------------------------
# Proposições
# -----------------------------------------------------------------------------

def _data(valor: Any) -> str | None:
    """Trunca datetime para DATE (YYYY-MM-DD). A API entrega `dataApresentacao`
    com precisão de minuto ('2026-07-29T15:57'), e a coluna é `date`."""
    if not valor:
        return None
    return str(valor)[:10]


def salvar_proposicoes(
    cliente: ClienteBanco,
    aprovados: Sequence[dict],
    *,
    source: str = "camara.proposicoes",
    source_url: str = BASE_CAMARA,
) -> int:
    for p in aprovados:
        cliente.upsert("proposicao", [{
            "casa_origem": p["casa_origem"],
            "id_na_fonte": p["id_fonte"],
            "tipo": p["tipo"],
            "numero": p["numero"],
            "ano": p["ano"],
            "identificador": p["identificador"],
            "ementa": p["ementa"],
            "situacao": p.get("situacao"),
            "data_apresentacao": _data(p.get("data_apresentacao")),
            "source": source,
            "source_url": source_url,
        }], conflito="casa_origem,id_na_fonte")
    return len(aprovados)


# -----------------------------------------------------------------------------
# Tramitações — resolve a proposição (uuid) a partir do id da fonte
# -----------------------------------------------------------------------------

def salvar_tramitacoes(
    cliente: ClienteBanco,
    aprovados: Sequence[dict],
    *,
    source: str = "camara.tramitacoes",
    source_url: str = BASE_CAMARA,
) -> int:
    """Persiste tramitações. Cada uma prende-se à proposição pela resolução do
    uuid; sem a proposição persistida, não há a quem prender — pula sem inventar.
    Upsert por (proposicao_id, sequencia), a constraint `tramitacao_unica_por_seq`.
    """
    salvas = 0
    for t in aprovados:
        prop = cliente.selecionar_um(
            "proposicao",
            {"casa_origem": t["casa"], "id_na_fonte": t["proposicao_id_fonte"]},
        )
        if prop is None:
            continue
        cliente.upsert("tramitacao", [{
            "proposicao_id": prop["id"],
            "sequencia": t["sequencia"],
            "data_hora": t["data_hora"],
            "orgao_sigla": t.get("orgao_sigla"),
            "descricao": t["descricao"],
            "despacho": t.get("despacho"),
            "source": source,
            "source_url": source_url,
        }], conflito="proposicao_id,sequencia")
        salvas += 1
    return salvas


# -----------------------------------------------------------------------------
# Votações — resolve a proposição (uuid) a partir do id da fonte
# -----------------------------------------------------------------------------

def salvar_votacoes(
    cliente: ClienteBanco,
    aprovados: Sequence[dict],
    *,
    source: str = "camara.votacoes",
    source_url: str = BASE_CAMARA,
) -> int:
    for v in aprovados:
        proposicao_uuid = None
        pid_fonte = v.get("proposicao_id_fonte")
        if pid_fonte:
            prop = cliente.selecionar_um(
                "proposicao",
                {"casa_origem": v["casa"], "id_na_fonte": pid_fonte},
            )
            proposicao_uuid = prop["id"] if prop else None

        cliente.upsert("votacao", [{
            "casa": v["casa"],
            "id_na_fonte": v["id_fonte"],
            "proposicao_id": proposicao_uuid,
            "titulo": v["titulo"],
            "data_hora": v["data_hora"],
            "resultado": v.get("resultado"),
            # Placar: None = não extraído (nullable desde a 0004). Nunca 0.
            "sim": v.get("sim"),
            "nao": v.get("nao"),
            "abstencao": v.get("abstencao"),
            # secreta é not null default false; None (não declarada) = não secreta.
            "secreta": bool(v.get("secreta")),
            "nominal": v.get("nominal"),
            "source": source,
            "source_url": source_url,
        }], conflito="casa,id_na_fonte")
    return len(aprovados)


# -----------------------------------------------------------------------------
# Votos nominais — resolve a votação (uuid); o perfil já vem resolvido
# -----------------------------------------------------------------------------

def salvar_votos_nominais(
    cliente: ClienteBanco,
    votacao_id_fonte: str,
    resolvidos: Sequence[Any],
    *,
    casa: str = "camara",
) -> int:
    """Persiste os votos nominais de UMA votação. `resolvidos` são
    VotoNominalResolvido (perfil_id já é uuid, resolvido na coleta).

    Se a votação não está persistida ainda, não há a quem prender o voto —
    devolve 0 sem inventar. A presidência (Artigo 17) NÃO entra aqui: não é
    posição de voto (§10), e o enum `voto_tipo` não a comporta.
    """
    if not resolvidos:
        return 0
    votacao = cliente.selecionar_um(
        "votacao", {"casa": casa, "id_na_fonte": votacao_id_fonte}
    )
    if votacao is None:
        return 0
    vid = votacao["id"]
    linhas = [{
        "votacao_id": vid,
        "perfil_id": r.perfil_id,
        "voto": r.voto,
        "partido_sigla_na_epoca": r.partido_sigla_na_epoca,
        "grau_atribuicao": r.grau_atribuicao,
    } for r in resolvidos]
    cliente.upsert("voto_nominal", linhas, conflito="votacao_id,perfil_id")
    return len(linhas)
