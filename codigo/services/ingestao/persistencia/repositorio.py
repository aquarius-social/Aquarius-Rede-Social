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

from datetime import date
from typing import Any, Callable, Iterable, Protocol, Sequence

BASE_CAMARA = "https://dadosabertos.camara.leg.br/api/v2"
BASE_TRANSPARENCIA = "https://api.portaldatransparencia.gov.br/api-de-dados"
BASE_SENADO = "https://legis.senado.leg.br/dadosabertos"

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

    def selecionar_muitos(
        self, tabela: str, onde: dict | None = None, colunas: str = "*",
        *, ordem: str | None = None,
    ) -> list[dict]:
        """Todas as linhas que casam com `onde` (igualdade em cada par),
        paginando. `onde` None/{} devolve a tabela inteira. `ordem` (nome de
        coluna) estabiliza a paginação — passe uma chave única (ex.: 'id')."""
        ...


# -----------------------------------------------------------------------------
# Bronze — imutável, insert ignorando conflito
# -----------------------------------------------------------------------------

def _upsert_lote(
    cliente: ClienteBanco, tabela: str, linhas: list[dict], *, conflito: str
) -> int:
    """Upsert de MUITAS linhas numa chamada (o adaptador loteia por baixo).
    Deduplica por chave de conflito — a última vence — porque o upsert em lote do
    Postgres recusa a mesma chave duas vezes na mesma requisição. Devolve quantas
    linhas DISTINTAS foram enviadas. Corta o nº de requisições de milhares para
    poucas (essencial no backfill histórico; ver supabase_adapter)."""
    cols = [c.strip() for c in conflito.split(",")]
    unicos: dict[tuple, dict] = {}
    for linha in linhas:
        unicos[tuple(linha.get(c) for c in cols)] = linha
    if unicos:
        cliente.upsert(tabela, list(unicos.values()), conflito=conflito)
    return len(unicos)


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


def salvar_autores_orcamentarios(
    cliente: ClienteBanco,
    autores: Sequence[dict],
    lookup,
    lookup_senador_nome=None,
) -> dict:
    """Materializa a curadoria autor-de-emenda → perfil como `id_externo`
    (sistema='autor_orcamentario', §6.3). Devolve {camara, senado, pendentes}.

    Dois braços (§17): `deputado_id` → perfil por id_externo(camara); senão, o
    nome casando um SENADOR → perfil por nome (1 sinal = 'nome'). Bancada/comissão
    sem perfil é pulada (não inventa). Grau vem do nº de sinais (§5.3): 2+ =
    'direto'; 1 = 'com_ressalva' + pendente (a constraint id_externo_grau_coerente
    exige ≥2 sinais para 'direto' com metodo 'convergencia')."""
    contadores = {"camara": 0, "senado": 0, "pendentes": 0}
    for a in autores:
        pid = None
        sinais = list(a.get("sinais") or [])
        if a.get("deputado_id"):
            pid = lookup("camara", a["deputado_id"])
        if pid is None and lookup_senador_nome is not None and a.get("nome_na_fonte"):
            pid = lookup_senador_nome(a["nome_na_fonte"])
            if pid is not None:
                sinais = sinais or ["nome"]     # match por nome parlamentar
                a = {**a, "_via": "senado"}
        if pid is None:
            continue
        grau = "direto" if len(sinais) >= 2 else "com_ressalva"
        cliente.upsert("id_externo", [{
            "profile_id": pid,
            "sistema": "autor_orcamentario",
            "identificador": a["codigo_autor"],
            "metodo": "convergencia",
            "grau": grau,
            "sinais": sinais,
            "versao_regra": VERSAO_REGRA,
            "pendente_conferencia": grau == "com_ressalva",
        }], conflito="sistema,identificador")
        if a.get("_via") == "senado":
            contadores["senado"] += 1
        else:
            contadores["camara"] += 1
        if grau == "com_ressalva":
            contadores["pendentes"] += 1
    return contadores


def lookup_id_externo(cliente: ClienteBanco):
    """Fábrica do lookup real de id_externo — mesma assinatura do que os
    coletores recebiam injetado, mas agora respaldado pela tabela.

        (sistema, identificador) -> profile_id | None

    MEMOIZADO (só ACERTOS): a mesma pessoa é resolvida MUITAS vezes numa rodada
    (um deputado vota em centenas de votações → o mesmo id_externo seria lido do
    banco a cada voto). Sem cache, um ano de votações fazia dezenas de milhares de
    reads sequenciais ao Supabase — o gargalo de tempo (horas) e a superfície de
    falha (um 502 avulso derrubava o ano). Cacheia só o ACERTO (profile_id != None)
    porque a MISSA pode ser transitória dentro da rodada: o fallback de emenda por
    nome resolve-e-INSERE o autor e relê esperando achar (miss → insert → hit).
    Uma vez existente, um id_externo não é removido nem re-apontado numa rodada."""
    cache: dict[tuple[str, str], str] = {}

    def _l(sistema: str, identificador: str) -> str | None:
        chave = (sistema, str(identificador))
        acerto = cache.get(chave)
        if acerto is not None:
            return acerto
        row = cliente.selecionar_um(
            "id_externo",
            {"sistema": sistema, "identificador": str(identificador)},
        )
        pid = row["profile_id"] if row else None
        if pid is not None:
            cache[chave] = pid
        return pid
    return _l


# -----------------------------------------------------------------------------
# Senadores → profiles + id_externo (+ junção bicameral §17) + vínculo
# -----------------------------------------------------------------------------

def _para_date(valor: Any) -> date | None:
    if not valor:
        return None
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        return None


def salvar_senadores(
    cliente: ClienteBanco,
    aprovados: Sequence[dict],
    candidatos: Sequence[dict] | None = None,
    *,
    source: str = "senado.senadores",
    source_url: str = BASE_SENADO,
) -> dict:
    """Persiste senadores com JUNÇÃO BICAMERAL (§17): perfil + id_externo.
    Devolve contadores {novos, vinculados, pendentes}.

    Para cada senador, tenta casar (probabilístico, §13 Tier 2) contra os
    `candidatos` — deputados já ingeridos, cada um um dict com `profile_id` +
    nome civil/nascimento/naturalidade. A decisão segue a disciplina §5.3:

      - Match 'direto' (2+ famílias independentes convergem): é a MESMA PESSOA.
        NÃO cria perfil — anexa o `id_externo` do Senado ao perfil do deputado
        (metodo='convergencia', grau='direto' sustentado pelos sinais).
      - Match 'com_ressalva' (1 sinal só) ou sem match: cria PERFIL PRÓPRIO. O
        vínculo senado→código é 'fonte_direta' (a fonte declara o código).
        Um sinal isolado marca `pendente_conferencia` — possível dup bicameral
        para conferência humana, jamais auto-fundida (ambíguo não auto-resolve).

    Sem `candidatos`, todo senador vira perfil próprio (passe só-Senado, honesto).

    O `vinculo_temporal` (partido/UF por período) NÃO é escrito aqui — é do passo
    de MANDATO HISTÓRICO (`senado/mandatos.py`), que tem os períodos partidários
    acurados. Espelha a Câmara: deputado = perfil; mandatos.py = vínculo.
    """
    from resolucao.bicameral import Alvo, Candidato, Grau, resolver_bicameral

    cand_objs = [
        Candidato(
            profile_id=c["profile_id"],
            nome_parlamentar=c.get("nome") or c.get("nome_parlamentar") or "",
            mandatos=(),
            nome_civil=c.get("nome_civil"),
            data_nascimento=_para_date(c.get("data_nascimento")),
            naturalidade_municipio=c.get("naturalidade_municipio"),
            naturalidade_uf=c.get("naturalidade_uf"),
        )
        for c in (candidatos or [])
    ]

    contadores = {"novos": 0, "vinculados": 0, "pendentes": 0}
    for s in aprovados:
        match = None
        if cand_objs:
            match = resolver_bicameral(
                Alvo(
                    nome=s.get("nome") or "",
                    data_do_fato=date(1900, 1, 1),  # bicameral ignora a data
                    nome_civil=s.get("nome_civil"),
                    data_nascimento=_para_date(s.get("data_nascimento")),
                    naturalidade_municipio=s.get("naturalidade_municipio"),
                    naturalidade_uf=s.get("naturalidade_uf"),
                ),
                cand_objs,
            )

        if match is not None and match.grau is Grau.DIRETO and match.profile_id:
            pid = match.profile_id
            cliente.upsert("id_externo", [{
                "profile_id": pid,
                "sistema": "senado",
                "identificador": s["identificador_externo"],
                "metodo": "convergencia",
                "grau": "direto",
                "sinais": list(match.sinais),
                "versao_regra": match.versao_regra,
                "pendente_conferencia": False,
            }], conflito="sistema,identificador")
            contadores["vinculados"] += 1
        else:
            pendente = bool(match and match.grau is Grau.COM_RESSALVA)
            linha_profile = {c: s.get(c) for c in _COLS_PROFILE}
            linha_profile["source"] = source
            linha_profile["source_url"] = source_url
            [perfil] = cliente.upsert("profiles", [linha_profile], conflito="slug")
            pid = perfil["id"]
            cliente.upsert("id_externo", [{
                "profile_id": pid,
                "sistema": "senado",
                "identificador": s["identificador_externo"],
                "metodo": "fonte_direta",
                "grau": "direto",
                "sinais": [],
                "versao_regra": VERSAO_REGRA,
                "pendente_conferencia": pendente,
            }], conflito="sistema,identificador")
            contadores["novos"] += 1
            if pendente:
                contadores["pendentes"] += 1
    return contadores


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


_COLS_EMENDA = (
    "codigo_emenda", "ano", "tipo", "numero", "autor_nome", "autor_codigo",
    "localidade_gasto", "funcao", "subfuncao",
    "valor_empenhado", "valor_liquidado", "valor_pago",
    "valor_resto_inscrito", "valor_resto_cancelado", "valor_resto_pago",
)


def _autor_emenda_coletivo(nome: str) -> bool:
    """Autoria coletiva (bancada estadual, comissão, relator) NÃO tem um
    parlamentar autor único — fica sem perfil por design (§6.3, não se inventa
    'bancada'). A fonte abrevia comissão de duas formas: `COMISSÃO…` e `COM. …`
    (com ponto) — ambas contam; `COM ` sem ponto NÃO, para não pegar um nome
    próprio que comece com essas três letras."""
    n = (nome or "").strip().upper()
    return (n.startswith("BANCADA") or n.startswith("COMISS")
            or n.startswith("COM.") or n.startswith("RELATOR"))


def _codigo_bancada(codigo) -> bool:
    """Código de autor orçamentário de bancada estadual (71xx). Guarda determinística
    (§6.3): nenhum autor individual usa a faixa 71xx, então o resolvedor por nome não
    deve tentar casar esses códigos a uma pessoa — a bancada é o autor (perfil coletivo)."""
    c = (str(codigo) if codigo is not None else "").strip()
    return len(c) == 4 and c.startswith("71") and c.isdigit()


def resolver_autores_emenda_por_nome(
    cliente: ClienteBanco,
    aprovados: Sequence[dict],
    lookup,
    lookup_parlamentar_nome,
) -> int:
    """Fallback §6.3 do mapa curado: autores de emenda que o mapa NÃO resolveu,
    casados por NOME contra os parlamentares ingeridos (deputado OU senador).

    Materializa `id_externo(autor_orcamentario → perfil)` com grau
    'com_ressalva' + `pendente_conferencia` — match por nome é 1 sinal, e §5.3
    manda não afirmar o que um sinal isolado não sustenta. `salvar_emendas`
    (chamado depois) resolve `autor_profile_id` por esse mesmo id_externo.

    Fica SEM atribuição (honesto): autoria coletiva (bancada/comissão), nome
    ambíguo (homônimo — `lookup_parlamentar_nome` devolve None) e código que o
    mapa curado já resolveu (2+ sinais, não se rebaixa). Idempotente."""
    if lookup is None or lookup_parlamentar_nome is None:
        return 0
    vistos: set[str] = set()
    novos: list[dict] = []
    for e in aprovados:
        cod = e.get("autor_codigo")
        nome = e.get("autor_nome")
        if not cod or not nome or cod in vistos:
            continue
        vistos.add(cod)
        if _autor_emenda_coletivo(nome) or _codigo_bancada(cod):
            continue  # coletivo por nome OU por código de bancada (71xx) — não casa pessoa
        if lookup("autor_orcamentario", cod) is not None:
            continue  # o mapa curado já resolveu este código (não rebaixa)
        pid = lookup_parlamentar_nome(nome)
        if pid is None:
            continue  # sem match ou ambíguo → fica null (§6.3)
        novos.append({
            "profile_id": pid,
            "sistema": "autor_orcamentario",
            "identificador": cod,
            "metodo": "convergencia",
            "grau": "com_ressalva",
            "sinais": ["nome"],
            "versao_regra": VERSAO_REGRA,
            "pendente_conferencia": True,
        })
    if novos:
        _upsert_lote(cliente, "id_externo", novos, conflito="sistema,identificador")
    return len(novos)


def salvar_emendas(
    cliente: ClienteBanco,
    aprovados: Sequence[dict],
    lookup=None,
    *,
    source: str = "transparencia.emendas",
    source_url: str = BASE_TRANSPARENCIA,
) -> int:
    """Persiste emendas orçamentárias. Resolve o autor pelo `id_externo`
    (sistema='autor_orcamentario', §6.3) quando `lookup` é dado e o mapa de
    autores foi carregado; senão `autor_profile_id` fica null (furo declarado).
    Upsert por `codigo_emenda`."""
    for e in aprovados:
        autor_profile_id = None
        if lookup is not None and e.get("autor_codigo"):
            autor_profile_id = lookup("autor_orcamentario", e["autor_codigo"])
        linha = {c: e.get(c) for c in _COLS_EMENDA}
        linha["autor_profile_id"] = autor_profile_id
        linha["source"] = source
        linha["source_url"] = source_url
        cliente.upsert("emenda", [linha], conflito="codigo_emenda")
    return len(aprovados)


def rebackfill_autor_profile_id(
    cliente: ClienteBanco, aprovados: Sequence[dict], lookup
) -> int:
    """Re-preenche APENAS `emenda.autor_profile_id` a partir do `id_externo`
    (sistema='autor_orcamentario') já resolvido — sem reescrever os demais campos.

    A fonte da atribuição continua sendo a resolução GRADUADA (id_externo, com
    grau/sinais/pendência), não um join cru autor_nome↔perfil. Serve à curadoria
    que re-roda a resolução com o universo completo de perfis: emendas cujo código
    passou a ter perfil recebem o vínculo; as sem código resolvido ficam como
    estão (honesto). Idempotente, upsert por `codigo_emenda`. Devolve quantas
    emendas foram (re)vinculadas."""
    if lookup is None:
        return 0
    linhas: list[dict] = []
    for e in aprovados:
        cod = e.get("autor_codigo")
        codigo_emenda = e.get("codigo_emenda")
        if not cod or not codigo_emenda:
            continue
        pid = lookup("autor_orcamentario", cod)
        if pid is None:
            continue
        linhas.append({"codigo_emenda": codigo_emenda, "autor_profile_id": pid})
    if linhas:
        _upsert_lote(cliente, "emenda", linhas, conflito="codigo_emenda")
    return len(linhas)


_COLS_EVENTO = (
    "casa", "id_fonte", "tipo", "titulo", "data_hora_inicio", "data_hora_fim",
    "situacao", "orgao_sigla", "orgao_nome", "local", "url",
)


def salvar_eventos(
    cliente: ClienteBanco,
    aprovados: Sequence[dict],
    *,
    source: str,
    source_url: str,
) -> int:
    """Persiste eventos da agenda (as duas casas — a prata carrega `casa`).
    Resolve `orgao_profile_id` pelo slug reconstruído da comissão (null quando
    não é comissão ingerida — plenário etc.). Upsert por (casa, id_fonte)."""
    for e in aprovados:
        orgao_profile_id = None
        slug = e.get("orgao_slug")
        if slug:
            prof = cliente.selecionar_um("profiles", {"slug": slug})
            orgao_profile_id = prof["id"] if prof else None
        linha = {c: e.get(c) for c in _COLS_EVENTO}
        linha["orgao_profile_id"] = orgao_profile_id
        linha["source"] = source
        linha["source_url"] = source_url
        cliente.upsert("evento", [linha], conflito="casa,id_fonte")
    return len(aprovados)


_COLS_DISCURSO = (
    "casa", "id_fonte", "data", "tipo", "sumario", "keywords",
    "url_texto", "url_video", "url_audio", "tem_transcricao",
)


def salvar_discursos(
    cliente: ClienteBanco,
    aprovados: Sequence[dict],
    lookup,
    *,
    source: str,
    source_url: str,
) -> int:
    """Persiste discursos das DUAS casas (a prata carrega `casa`). Resolve o
    autor por `id_externo` (sistema='camara'|'senado') antes de gravar — sem o
    perfil ingerido, o discurso é pulado (integridade referencial §6), não
    inventado. Upsert por (casa, id_fonte)."""
    cache: dict[tuple, str | None] = {}
    linhas: list[dict] = []
    for d in aprovados:
        chave = (d["sistema"], d["parlamentar_id_fonte"])
        if chave not in cache:
            cache[chave] = lookup(*chave)
        perfil_id = cache[chave]
        if perfil_id is None:
            continue
        linha = {c: d.get(c) for c in _COLS_DISCURSO}
        linha["profile_id"] = perfil_id
        linha["source"] = source
        linha["source_url"] = source_url
        linhas.append(linha)
    return _upsert_lote(cliente, "discurso", linhas, conflito="casa,id_fonte")


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
    pulados_sobrepostos = 0
    for v in vinculos:
        # A casa do vínculo é também o sistema do id_externo (camara↔camara,
        # senado↔senado) — resolve bicameral sem hardcode.
        perfil_id = lookup(v.get("casa", "camara"), v["id_fonte"])
        if perfil_id is None:
            continue
        partido_id = v.get("partido_id")
        if partido_id is None and lookup_partido is not None:
            partido_id = lookup_partido(v.get("partido_sigla_fonte"))
        # §6.4: resolve o titular quando a fonte o dá (Senado). A Câmara não expõe
        # o titular → fica None, e a constraint relaxada (0016) permite o suplente
        # sem link. Não se pula mais: melhor mostrar o suplente sem titular que
        # deixá-lo sumir.
        titular_profile_id = None
        if v.get("titular_id_fonte"):
            titular_profile_id = lookup(v.get("casa", "camara"), v["titular_id_fonte"])
        linha = {
            "profile_id": perfil_id,
            "casa": v["casa"],
            "legislatura": v.get("legislatura"),
            "uf": v["uf"],
            "partido_id": partido_id,
            "partido_sigla_fonte": v.get("partido_sigla_fonte"),
            "ocupacao": v["ocupacao"],
            "titular_profile_id": titular_profile_id,
            "causa": v.get("causa"),
            "vigencia": _daterange(v["vigencia_inicio"], v.get("vigencia_fim")),
            "source": source,
            "source_url": source_url,
        }
        try:
            cliente.upsert("vinculo_temporal", [linha], conflito="profile_id,casa,vigencia")
        except Exception as e:  # noqa: BLE001 — só a sobreposição é engolida; o resto sobe
            # A constraint de EXCLUSÃO `vinculo_sem_sobreposicao` rejeita um período que
            # SE SOBREPÕE a um já gravado — o que o ON CONFLICT (chave exata) não resolve.
            # Ocorre ao rebackfillar uma legislatura antiga cujos deputados já têm vínculos
            # MAIS FINOS de uma ingestão anterior (ex.: troca de partido no meio do período).
            # Mantém-se o existente (mais informativo) e pula-se o grosseiro: débito
            # declarado, não crash (§4/§5.1). Erro que NÃO é sobreposição sobe.
            if "vinculo_sem_sobreposicao" in str(e) or "23P01" in str(e):
                pulados_sobrepostos += 1
                continue
            raise
        salvos += 1
    if pulados_sobrepostos:
        print(f"  [{pulados_sobrepostos} vínculo(s) '{source}' pulado(s) por sobreposição "
              "com período já gravado — mantido o existente (§4/§5.1)]")
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
    linhas = [{
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
    } for p in aprovados]
    return _upsert_lote(cliente, "proposicao", linhas,
                        conflito="casa_origem,id_na_fonte")


# -----------------------------------------------------------------------------
# Despesas / CEAP — resolve o perfil (uuid) a partir do id do deputado na fonte
# -----------------------------------------------------------------------------

def salvar_despesas(
    cliente: ClienteBanco,
    aprovados: Sequence[dict],
    lookup,
    *,
    source: str = "camara.despesas",
    source_url: str = BASE_CAMARA,
) -> int:
    """Persiste despesas da cota parlamentar. Resolve `perfil_id` pelo lookup de
    id_externo (mesmo dos votos); sem o parlamentar ingerido, pula sem inventar.
    Upsert por (perfil_id, cod_documento, parcela)."""
    cache: dict[str, str | None] = {}   # lookup uma vez por deputado (não por linha)
    linhas: list[dict] = []
    for d in aprovados:
        did = d["deputado_id_fonte"]
        if did not in cache:
            cache[did] = lookup("camara", did)
        perfil_id = cache[did]
        if perfil_id is None:
            continue
        linhas.append({
            "perfil_id": perfil_id,
            "ano": d["ano"], "mes": d["mes"],
            "tipo_despesa": d.get("tipo_despesa"),
            "tipo_documento": d.get("tipo_documento"),
            "cod_documento": d.get("cod_documento"),
            "cod_lote": d.get("cod_lote"),
            "num_documento": d.get("num_documento"),
            "num_ressarcimento": d.get("num_ressarcimento"),
            "parcela": d.get("parcela"),
            "data_documento": d.get("data_documento"),
            "valor_documento": d.get("valor_documento"),
            "valor_glosa": d.get("valor_glosa"),
            "valor_liquido": d.get("valor_liquido"),
            "fornecedor_nome": d.get("fornecedor_nome"),
            "fornecedor_cnpj_cpf": d.get("fornecedor_cnpj_cpf"),
            "url_documento": d.get("url_documento"),
            "source": source, "source_url": source_url,
        })
    return _upsert_lote(cliente, "despesa", linhas,
                        conflito="perfil_id,cod_documento,parcela")


def salvar_despesas_senado(
    cliente: ClienteBanco,
    aprovados: Sequence[dict],
    lookup_senador,
    *,
    source: str = "senado.ceaps",
    source_url: str = BASE_SENADO,
) -> int:
    """Persiste a CEAPS do Senado na MESMA tabela `despesa`. Resolve o perfil por
    NOME (a fonte não traz código): `lookup_senador(nome)` → profile_id (uuid).
    Sem perfil resolvido, pula (§6, não inventa). Upsert por (perfil_id,
    cod_documento, parcela) — parcela=0 no Senado torna a chave efetiva."""
    cache: dict[str, str | None] = {}
    linhas: list[dict] = []
    for d in aprovados:
        nome = d.get("senador_nome")
        if nome not in cache:
            cache[nome] = lookup_senador(nome)
        perfil_id = cache[nome]
        if perfil_id is None:
            continue
        linhas.append({
            "perfil_id": perfil_id,
            "ano": d["ano"], "mes": d["mes"],
            "tipo_despesa": d.get("tipo_despesa"),
            "tipo_documento": d.get("tipo_documento"),
            "cod_documento": d.get("cod_documento"),
            "num_documento": d.get("num_documento"),
            "parcela": d.get("parcela"),
            "data_documento": d.get("data_documento"),
            "valor_documento": d.get("valor_documento"),
            "valor_glosa": d.get("valor_glosa"),
            "valor_liquido": d.get("valor_liquido"),
            "fornecedor_nome": d.get("fornecedor_nome"),
            "fornecedor_cnpj_cpf": d.get("fornecedor_cnpj_cpf"),
            "url_documento": d.get("url_documento"),
            "source": source, "source_url": source_url,
        })
    return _upsert_lote(cliente, "despesa", linhas,
                        conflito="perfil_id,cod_documento,parcela")


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
    cache: dict[tuple, str | None] = {}   # resolve a proposição uma vez, não por linha
    linhas: list[dict] = []
    for t in aprovados:
        chave = (t["casa"], t["proposicao_id_fonte"])
        if chave not in cache:
            prop = cliente.selecionar_um(
                "proposicao", {"casa_origem": chave[0], "id_na_fonte": chave[1]})
            cache[chave] = prop["id"] if prop else None
        proposicao_id = cache[chave]
        if proposicao_id is None:
            continue
        linhas.append({
            "proposicao_id": proposicao_id,
            "sequencia": t["sequencia"],
            "data_hora": t["data_hora"],
            "orgao_sigla": t.get("orgao_sigla"),
            "descricao": t["descricao"],
            "despacho": t.get("despacho"),
            "source": source,
            "source_url": source_url,
        })
    return _upsert_lote(cliente, "tramitacao", linhas,
                        conflito="proposicao_id,sequencia")


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


# -----------------------------------------------------------------------------
# Presença — sessões do Plenário + comparecimento (Área E, §11/§4)
# -----------------------------------------------------------------------------

def salvar_sessoes(
    cliente: ClienteBanco,
    aprovados: Sequence[dict],
    *,
    source: str = "camara.sessoes",
    source_url: str = BASE_CAMARA,
) -> int:
    """Persiste sessões deliberativas. Upsert por (casa, id_fonte)."""
    linhas = [{
        "casa": s["casa"],
        "id_fonte": s["id_fonte"],
        "tipo": s.get("tipo"),
        "data_hora": s.get("data_hora"),
        "orgao_sigla": s.get("orgao_sigla"),
        "source": source,
        "source_url": source_url,
    } for s in aprovados]
    if not linhas:
        return 0
    cliente.upsert("sessao", linhas, conflito="casa,id_fonte")
    return len(linhas)


def salvar_presencas(
    cliente: ClienteBanco,
    sessao_id_fonte: str,
    aprovados: Sequence[dict],
    lookup,
    *,
    casa: str = "camara",
    source: str = "camara.presenca",
    source_url: str = BASE_CAMARA,
) -> int:
    """Persiste a presença de UMA sessão. Resolve a sessão (uuid) e o perfil de
    cada presente por id_externo (a PESSOA, na data da sessão §4). Deputado não
    resolvido é PULADO (sem perfil não há a quem prender — não inventa fantasma).
    Upsert por (sessao_id, perfil_id).
    """
    if not aprovados:
        return 0
    sessao = cliente.selecionar_um("sessao", {"casa": casa, "id_fonte": sessao_id_fonte})
    if sessao is None:
        return 0
    sid = sessao["id"]
    linhas: list[dict] = []
    for p in aprovados:
        perfil_id = lookup(casa, p["id_parlamentar"]) if p.get("id_parlamentar") else None
        if perfil_id is None:
            continue
        linhas.append({
            "sessao_id": sid,
            "perfil_id": perfil_id,
            "presente": bool(p.get("presente", True)),
            "source": source,
            "source_url": source_url,
        })
    if not linhas:
        return 0
    cliente.upsert("presenca", linhas, conflito="sessao_id,perfil_id")
    return len(linhas)
