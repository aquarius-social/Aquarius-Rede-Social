"""Coletor da Câmara — votações e votos nominais.

Fonte:
    https://dadosabertos.camara.leg.br/api/v2/votacoes
    https://dadosabertos.camara.leg.br/api/v2/votacoes/{id}/votos

Este é o primeiro coletor que EXERCITA a Onda 0: cada voto nominal precisa ser
vinculado a um perfil. A ligação é feita por `id_externo` (sistema='camara',
identificador=id do deputado na Câmara) — a rota mais rápida e limpa, porque a
fonte declarou o identificador (grau 'direto', método 'fonte_direta').

Quando o lookup falha — deputado ainda não ingerido, id novo, voto histórico
de mandato antigo — o voto vai à quarentena com dimensão
'integridade_referencial'. É deliberado: criar perfil inline durante ingestão
de voto atropela toda a disciplina de identidade da seção 6, e faria com que
um erro de digitação da fonte virasse perfil fantasma no banco.

ATENÇÃO: nomes de campo e formatos vieram da documentação pública da API v2 da
Câmara e NÃO foram verificados contra a interface viva neste ambiente. Rodar
canário antes de produção — mesma disciplina do coletor de proposições.

Uma nota sobre voto secreto (regra 6 do contrato de resposta): votação
declarada como secreta pela fonte NÃO deve trazer nominais. Se vier, o portão
recusa por consistência — não é o coletor que decide o que é secreto, é a
fonte, e o dado interno tem que refletir isso.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from contrato.canario import EstadoContrato, avaliar
from pipeline.camadas import (
    RegistroBronze,
    Violacao,
    campo_em,
    campo_obrigatorio,
    portao_bronze_prata,
)
from pipeline.coletor import (
    ClienteHttp,
    ErroFalha,
    ErroInstabilidade,
    PoliticaRetry,
    obter_com_retry,
)

FONTE_VOTACAO = "camara.votacoes"
FONTE_VOTO = "camara.votos"
BASE = "https://dadosabertos.camara.leg.br/api/v2"

# Campos críticos da LISTA de votações (GET /votacoes). Verificado contra a API
# viva em 2026-07-29: todos presentes. NÃO inclui a matéria — na lista o campo
# de proposição vem NULO em toda a amostra (Metodologia §10). O vínculo à
# matéria vive no DETALHE, em `proposicoesAfetadas`, buscado à parte.
CAMPOS_CRITICOS_VOTACAO = frozenset({
    "id", "data", "dataHoraRegistro", "descricao"
})
CAMPOS_CRITICOS_VOTO = frozenset({"tipoVoto", "deputado_"})

# Rótulos que NÃO são posição de voto. "Artigo 17" registra quem presidiu a
# sessão (Metodologia §10, verificado em jul/2026): excluído do placar, nunca
# se conta como posição nem como ausência. Por isso fica FORA do MAPA_VOTO.
ROTULOS_PRESIDENCIA = frozenset({"Artigo 17"})

# Enum normalizado do produto. Os rótulos da fonte vão em `modalidade_fonte`.
VOTOS_NORMALIZADOS = {"sim", "nao", "abstencao", "obstrucao", "ausente"}

# Mapa de rótulos da Câmara para o enum. Preserva-se o rótulo original
# em `modalidade_fonte` porque a regra 5 do contrato exige "declarar a
# modalidade de toda manifestação parlamentar" — "Obstrução" e "Abstenção"
# são coisas distintas, e o normalizado colapsa. Sem a original, some sinal.
# "Artigo 17" é tratado à parte (ROTULOS_PRESIDENCIA), pois não é posição.
MAPA_VOTO = {
    "Sim": "sim",
    "Não": "nao",
    "Nao": "nao",  # sem acento também aparece
    "Abstenção": "abstencao",
    "Abstencao": "abstencao",
    "Obstrução": "obstrucao",
    "Obstrucao": "obstrucao",
    # "Artigo 17" NÃO entra aqui — não é posição, é marca de quem presidiu
    # (ver ROTULOS_PRESIDENCIA e Metodologia §10).
    "Ausência": "ausente",
    "Ausente": "ausente",
    # "Liberado": pauta permite liberação — decidir no produto se conta
    # como 'ausente' ou vira modalidade própria. Por ora, quarentena.
}

# Tamanho da Câmara dos Deputados. Nenhuma votação pode ter mais votantes que
# isto (identidade interna da Metodologia §5.2: "votantes não excedem o tamanho
# da casa"). Suplente em exercício ocupa a cadeira do titular, não soma cadeira.
TAMANHO_CAMARA = 513


# -----------------------------------------------------------------------------
# Extração do placar declarado — vive no TEXTO da descrição (Metodologia §10)
# -----------------------------------------------------------------------------
#
# A Câmara não entrega o placar como campo estruturado; ele está no texto, em
# formatos distintos entre plenário e comissão (§10, verificado em jul/2026):
#
#   Plenário:  "... Sim: 278; não: 88; abstenção: 4; total: 370."
#   Comissão:  "... Sim: 10; Não: 4; Abstenção: 0; ... Total de Votantes: 14."
#              "... 34 votos \"Sim\", 30 votos \"Não\". Quórum de votação: 64..."
#              "... Resultado: 13 votos \"Não\"."
#
# Descrições puramente narrativas (sem número) NÃO produzem placar: devolvem
# None. Dado ausente é melhor que dado errado (Metodologia, seção 1). O que este
# parser extrai é reconciliado depois contra a soma dos nominais (§5.2).

_RE_ROTULO = {
    "sim":       re.compile(r"\bsim\b\s*:?\s*(\d+)", re.I),
    "nao":       re.compile(r"\bn[ãa]o\b\s*:?\s*(\d+)", re.I),
    "abstencao": re.compile(r"\babstenç?[ãa]o\b\s*:?\s*(\d+)", re.I),
    "obstrucao": re.compile(r"\bobstruç?[ãa]o\b\s*:?\s*(\d+)", re.I),
}
# Formato "N votos \"Sim\"" — número ANTES do rótulo, usado em comissões.
_RE_VOTOS_ROTULO = re.compile(
    r"(\d+)\s+votos?\s+\"?(sim|n[ãa]o|abstenç?[ãa]o|obstruç?[ãa]o)\"?", re.I
)
_ROTULO_CANON = {"sim": "sim", "não": "nao", "nao": "nao",
                 "abstenção": "abstencao", "abstencao": "abstencao",
                 "obstrução": "obstrucao", "obstrucao": "obstrucao"}
# Total declarado: "total: 370" (plenário) ou "Total de Votantes: 14" (comissão).
_RE_TOTAL = re.compile(r"total(?:\s+de\s+votantes)?\s*:?\s*(\d+)", re.I)


def extrair_placar(descricao: str | None) -> dict | None:
    """Placar declarado a partir do texto da descrição, ou None se não houver.

    Retorna as posições encontradas (`sim`, `nao`, `abstencao`, `obstrucao` —
    cada uma pode faltar) e `total_declarado` quando o texto o traz. Devolve
    None quando nenhum número de posição é encontrado (descrição narrativa).
    """
    if not descricao:
        return None
    texto = descricao
    contagem: dict[str, int] = {}

    # Formato rótulo-dois-pontos (plenário e comissão-com-rótulo).
    for chave, rx in _RE_ROTULO.items():
        m = rx.search(texto)
        if m:
            contagem[chave] = int(m.group(1))

    # Formato "N votos \"Rótulo\"" — preenche o que faltar.
    for m in _RE_VOTOS_ROTULO.finditer(texto):
        canon = _ROTULO_CANON.get(m.group(2).lower())
        if canon and canon not in contagem:
            contagem[canon] = int(m.group(1))

    if not contagem:
        return None

    placar = {k: contagem.get(k) for k in ("sim", "nao", "abstencao", "obstrucao")}
    mt = _RE_TOTAL.search(texto)
    placar["total_declarado"] = int(mt.group(1)) if mt else None
    return placar


_CAMPOS_PLACAR = ("sim", "nao", "abstencao", "obstrucao", "total_declarado")


def _campos_placar(descricao: str | None) -> dict:
    """Sempre devolve as cinco chaves de placar; None onde não há dado."""
    placar = extrair_placar(descricao) or {}
    return {k: placar.get(k) for k in _CAMPOS_PLACAR}


# -----------------------------------------------------------------------------
# Coleta — bronze
# -----------------------------------------------------------------------------

def coletar_bronze_votacoes(
    cliente: ClienteHttp,
    *,
    data_inicio: str,
    data_fim: str,
    politica: PoliticaRetry = PoliticaRetry(),
    itens_por_pagina: int = 100,
    limite_paginas: int = 200,
) -> list[RegistroBronze]:
    """Lista votações no intervalo. Não busca votos aqui — cada votação é
    detalhada num segundo passo (`coletar_bronze_votos`).

    Motivo da separação: a lista de votações é barata e a lista de votos é
    cara (uma requisição por votação × ~513 votos). Separar permite ao
    orquestrador decidir se coleta nominais desta rodada ou não, e permite
    o teste de contrato rodar sobre a lista antes de gastar as chamadas caras.
    """
    url = f"{BASE}/votacoes"
    params: dict[str, Any] = {
        "dataInicio": data_inicio,
        "dataFim": data_fim,
        "itens": itens_por_pagina,
        "ordem": "ASC",
        "ordenarPor": "dataHoraRegistro",
    }
    bronze: list[RegistroBronze] = []
    pagina = 1
    proximo: str | None = None
    while pagina <= limite_paginas:
        corpo = obter_com_retry(
            cliente, proximo or url,
            params=None if proximo else params,
            politica=politica,
        )
        for item in (corpo or {}).get("dados", []):
            bronze.append(RegistroBronze.de(FONTE_VOTACAO, url, item))
        proximo = _proximo_link(corpo)
        if proximo is None:
            break
        pagina += 1
    return bronze


def coletar_bronze_votos(
    cliente: ClienteHttp,
    votacao_id_fonte: str,
    *,
    politica: PoliticaRetry = PoliticaRetry(),
) -> list[RegistroBronze]:
    """Votos nominais de UMA votação."""
    url = f"{BASE}/votacoes/{votacao_id_fonte}/votos"
    corpo = obter_com_retry(cliente, url, politica=politica)
    return [
        RegistroBronze.de(FONTE_VOTO, url, item)
        for item in (corpo or {}).get("dados", [])
    ]


def coletar_bronze_votacao_detalhe(
    cliente: ClienteHttp,
    votacao_id_fonte: str,
    *,
    politica: PoliticaRetry = PoliticaRetry(),
) -> RegistroBronze:
    """Detalhe de UMA votação (GET /votacoes/{id}).

    É aqui — e só aqui — que vive `proposicoesAfetadas`, o vínculo à matéria
    (Metodologia §10). O `dados` do detalhe é um objeto, não uma lista.
    """
    url = f"{BASE}/votacoes/{votacao_id_fonte}"
    corpo = obter_com_retry(cliente, url, politica=politica)
    dado = (corpo or {}).get("dados") or {}
    return RegistroBronze.de(FONTE_VOTACAO, url, dado)


def _proximo_link(corpo: Any) -> str | None:
    for link in (corpo or {}).get("links", []) or []:
        if link.get("rel") == "next" and link.get("href"):
            return link["href"]
    return None


# -----------------------------------------------------------------------------
# Transformação — votação
# -----------------------------------------------------------------------------

def transformar_votacao(payload: dict) -> dict:
    """Normaliza uma votação para o shape da camada prata."""
    aprov = _num(payload.get("aprovacao"))
    return {
        "id_fonte": str(payload["id"]),
        "casa": "camara",
        "titulo": (payload.get("descricao") or "").strip() or None,
        "data_hora": payload.get("dataHoraRegistro") or payload.get("data"),
        "resultado": _resultado(payload),
        # Placar: a API NÃO o devolve estruturado — vive no texto da `descricao`,
        # em formatos distintos entre plenário e comissão (Metodologia §10). É
        # extraído por parsing; descrição sem número → placar None (não extraído),
        # jamais 0, que fabricaria dado. A reconciliação contra os nominais (§5.2)
        # é feita na rodada, quando os votos individuais estão disponíveis.
        **_campos_placar(payload.get("descricao")),
        # Três estados distintos, não dois:
        #   secreta  = true             → sem nominais por design constitucional
        #   nominal  = false, secreta=false → simbólica ou por acordo, sem nominais
        #   nominal  = true             → deve trazer nominais
        # A validação disso contra o schema do Parlametria (leggo-backend) foi
        # o que revelou o bug — antes tratávamos só o binário secreta/não.
        # Uma votação simbólica que chega sem nominais é o caso NORMAL, não
        # falha de integridade referencial.
        "secreta": _secreta(payload),
        "nominal": _nominal(payload),
        "proposicao_id_fonte": _proposicao_id(payload),
        "aprovacao": aprov,
    }


def _resultado(payload: dict) -> str | None:
    aprov = _num(payload.get("aprovacao"))
    if aprov is None:
        return None
    return "aprovada" if aprov > 0 else "rejeitada"


def _id_de(prop: dict) -> str | None:
    """Id de uma proposição afetada — direto ou extraído da URI."""
    id_direto = prop.get("id")
    if id_direto is not None:
        return str(id_direto)
    uri = prop.get("uri") or ""
    return uri.rsplit("/", 1)[-1] if uri else None


def _proposicao_id(payload: dict) -> str | None:
    """Matéria em julgamento, a partir do DETALHE da votação.

    Metodologia §10 (verificado em jul/2026): o vínculo correto está em
    `proposicoesAfetadas`, e é corroborado pelo identificador da votação, que
    começa pelo id da proposição — ex.: votação `996958-88` → proposição
    `996958`. Usamos esse prefixo para escolher a afetada certa quando há mais
    de uma; sem corroboração, caímos na primeira. Votação procedimental pode
    vir sem afetadas: matéria `None` é resultado legítimo.
    """
    props = [
        p for p in (payload.get("proposicoesAfetadas") or [])
        if isinstance(p, dict)
    ]
    if not props:
        return None
    prefixo = str(payload.get("id") or "").split("-", 1)[0]
    for p in props:
        if _id_de(p) == prefixo:
            return _id_de(p)
    return _id_de(props[0])


def _secreta(payload: dict) -> bool | None:
    desc = (payload.get("descricao") or "").lower()
    if "secret" in desc:
        return True
    return None  # não declarado — leitura humana decide


def _nominal(payload: dict) -> bool | None:
    """Infere se a votação é nominal (produz votos individuais).

    [verificar] A Câmara não publica esse booleano diretamente na resposta
    de lista de votações da API v2 — nossa inferência atual é heurística
    sobre `descricao`. Substituir pela leitura de campo real quando a
    verificação contra a fonte viva estiver feita.

    Regra provisória: "simbólic" ou "por acordo" na descrição = não nominal;
    "nominal" na descrição = nominal explícito; caso contrário None (não
    inferido), e o processador de nominais NÃO recusa por ausência —
    apenas votação DECLARADA como não nominal recusa nominais.
    """
    desc = (payload.get("descricao") or "").lower()
    if "simbólic" in desc or "simbolic" in desc or "por acordo" in desc:
        return False
    if "nominal" in desc:
        return True
    return None


def _num(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _placar_coerente(registro: dict) -> Violacao | None:
    """Identidade aritmética interna (§5.2): as posições declaradas somam o
    total declarado.

    Só é checável quando o texto trouxe AMBOS (posições e total). Descrição
    narrativa ou incompleta → placar não extraído → silêncio, que é legítimo.
    Um `total` presente que não fecha com a soma é erro de dado.
    """
    total = registro.get("total_declarado")
    posicoes = [registro.get(c) for c in ("sim", "nao", "abstencao", "obstrucao")]
    presentes = [v for v in posicoes if v is not None]
    if total is None or not presentes:
        return None
    soma = sum(presentes)
    if soma != total:
        return Violacao(
            "precisao",
            f"placar incoerente: soma das posições {soma} ≠ total declarado {total}",
        )
    return None


VERIFICADORES_VOTACAO = [
    campo_obrigatorio("id_fonte"),
    campo_obrigatorio("data_hora"),
    campo_obrigatorio("titulo"),
    _placar_coerente,
]


def processar_votacoes_para_prata(bronze: list[RegistroBronze]):
    return portao_bronze_prata(
        bronze, transformar=transformar_votacao,
        verificadores=VERIFICADORES_VOTACAO,
    )


# -----------------------------------------------------------------------------
# Transformação — voto nominal, com resolução de identidade
# -----------------------------------------------------------------------------

class LookupIdExterno(Protocol):
    """Contrato para consulta à tabela id_externo.

    A implementação real consulta o banco; nos testes é um dicionário.
    Escolha deliberada: o coletor não conhece o Supabase — separar isso torna
    o coletor testável sem infra e reutilizável fora de ingestão.
    """

    def __call__(self, sistema: str, identificador: str) -> str | None: ...


@dataclass
class VotoNominalResolvido:
    """Voto pronto para inserir em `voto_nominal`."""
    votacao_id_fonte: str
    perfil_id: str
    voto: str  # enum VOTOS_NORMALIZADOS
    modalidade_fonte: str  # rótulo original da Câmara
    partido_sigla_na_epoca: str | None
    grau_atribuicao: str = "direto"


@dataclass
class ResultadoVotos:
    resolvidos: list[VotoNominalResolvido] = field(default_factory=list)
    quarentena: list[tuple[RegistroBronze, Violacao]] = field(default_factory=list)
    # perfil_id de quem presidiu a votação (voto "Artigo 17", Metodologia §10).
    # Fica FORA de `resolvidos` de propósito: nunca é posição nem ausência, e
    # nunca entra no placar.
    presidencia: list[str] = field(default_factory=list)


def processar_votos_para_prata(
    bronze: list[RegistroBronze],
    votacao_id_fonte: str,
    *,
    lookup: LookupIdExterno,
    votacao_declarada_secreta: bool = False,
    votacao_declarada_nominal: bool | None = None,
) -> ResultadoVotos:
    """Resolve cada nominal e triam o que não passa.

    Duas invariantes de consistência entre votação e seus nominais:

    1. Se a votação foi declarada SECRETA e vier nominal, o lote inteiro vai
       à quarentena — não cabe ao coletor salvar "só alguns nominais de
       secreta", isso produz o índice parcial que a regra 6 do contrato de
       resposta existe para impedir.

    2. Se a votação foi declarada NÃO NOMINAL (simbólica ou por acordo) e
       vier nominal, mesma coisa: incoerência entre o meta e o detalhe é
       coisa da fonte, não nossa para corrigir.

    O caso `nominal = None` (não inferido) é permissivo: a heurística sobre
    `descricao` erra para o lado de deixar passar. O processador só recusa
    quando a fonte foi EXPLÍCITA sobre não haver nominal.
    """
    resultado = ResultadoVotos()

    if not bronze:
        return resultado

    motivo_recusa_lote: str | None = None
    if votacao_declarada_secreta:
        motivo_recusa_lote = (
            "votação declarada secreta traz nominal — regra 6 do contrato "
            "de resposta exige exclusões estruturais coerentes"
        )
    elif votacao_declarada_nominal is False:
        motivo_recusa_lote = (
            "votação declarada não nominal (simbólica ou por acordo) traz "
            "nominal — incoerência entre lista e detalhe da fonte"
        )

    if motivo_recusa_lote:
        for reg in bronze:
            resultado.quarentena.append((
                reg, Violacao("consistencia", motivo_recusa_lote),
            ))
        return resultado

    for reg in bronze:
        p = reg.payload

        # 1. Rótulo presente?
        rotulo = p.get("tipoVoto")
        if not rotulo:
            resultado.quarentena.append((
                reg, Violacao("completude", "tipoVoto ausente")
            ))
            continue

        # 2. Identidade — a rota rápida via id_externo. Resolvida ANTES da
        # modalidade porque também "Artigo 17" (presidência) precisa saber QUEM
        # presidiu; sem perfil, nem posição nem presidência são registráveis.
        dep = p.get("deputado_") or {}
        id_camara = dep.get("id")
        if id_camara is None:
            resultado.quarentena.append((
                reg,
                Violacao(
                    "integridade_referencial",
                    "voto sem deputado_.id — não é resolvível",
                ),
            ))
            continue

        perfil_id = lookup("camara", str(id_camara))
        if perfil_id is None:
            resultado.quarentena.append((
                reg,
                Violacao(
                    "integridade_referencial",
                    f"deputado id_externo=camara:{id_camara} não encontrado — "
                    "coletor de deputados precisa preceder o de votações",
                ),
            ))
            continue

        # 3. Presidência (Metodologia §10): "Artigo 17" registra quem presidiu,
        # nunca é posição nem ausência, e fica fora do placar. Vai a uma lista
        # própria, não a `resolvidos`.
        if rotulo in ROTULOS_PRESIDENCIA:
            resultado.presidencia.append(perfil_id)
            continue

        # 4. Modalidade de posição
        normalizado = MAPA_VOTO.get(rotulo)
        if normalizado is None:
            resultado.quarentena.append((
                reg,
                Violacao(
                    "precisao",
                    f"modalidade de voto desconhecida: {rotulo!r} "
                    "(adicionar ao MAPA_VOTO exige decisão de produto)",
                ),
            ))
            continue

        # 5. Partido na época — vem da própria resposta de voto, é o snapshot
        # que a Câmara fez no momento do voto. Preservar como-é: a resolução
        # temporal contra `partido` canônico é responsabilidade da camada ouro.
        resultado.resolvidos.append(VotoNominalResolvido(
            votacao_id_fonte=votacao_id_fonte,
            perfil_id=perfil_id,
            voto=normalizado,
            modalidade_fonte=rotulo,
            partido_sigla_na_epoca=dep.get("siglaPartido"),
            grau_atribuicao="direto",
        ))

    return resultado


def conferir_placar_contra_nominais(
    votacao_prata: dict, votos: ResultadoVotos
) -> list[Violacao]:
    """Reconciliação da §5.2: o placar declarado (texto) bate com os votos
    individuais, e os votantes não excedem o tamanho da casa.

    Só se aplica quando há nominais resolvidos — votação simbólica não tem o que
    reconciliar. A presidência (Artigo 17) já está fora de `votos.resolvidos`,
    coerente com o placar declarado, que também a exclui.
    """
    violacoes: list[Violacao] = []
    resolvidos = votos.resolvidos
    if not resolvidos:
        return violacoes

    if len(resolvidos) > TAMANHO_CAMARA:
        violacoes.append(Violacao(
            "consistencia",
            f"votantes {len(resolvidos)} excedem o tamanho da casa "
            f"({TAMANHO_CAMARA})",
        ))

    contagem = {"sim": 0, "nao": 0, "abstencao": 0, "obstrucao": 0}
    for v in resolvidos:
        if v.voto in contagem:
            contagem[v.voto] += 1

    for cat in ("sim", "nao", "abstencao", "obstrucao"):
        declarado = votacao_prata.get(cat)
        if declarado is not None and declarado != contagem[cat]:
            violacoes.append(Violacao(
                "consistencia",
                f"placar {cat}={declarado} ≠ nominais {cat}={contagem[cat]}",
            ))
    return violacoes


# -----------------------------------------------------------------------------
# Rodada completa — votações + nominais + contrato
# -----------------------------------------------------------------------------

@dataclass
class ResultadoRodadaVotacoes:
    estado: EstadoContrato
    detalhe: str
    votacoes_bronze: list[RegistroBronze]
    votacoes_prata: Any = None  # ResultadoPortao
    nominais: dict[str, ResultadoVotos] = field(default_factory=dict)
    # Divergências placar-declarado × votos-individuais, por votação (§5.2).
    placar_violacoes: dict[str, list[Violacao]] = field(default_factory=dict)
    # Bronze bruto das outras duas requisições, para preservação/auditoria
    # (§3.1). Detalhe de cada votação e votos por votação. Antes eram consumidos
    # e descartados; agora são expostos para o orquestrador persistir.
    detalhes_bronze: list[RegistroBronze] = field(default_factory=list)
    votos_bronze: dict[str, list[RegistroBronze]] = field(default_factory=dict)


def rodada_votacoes(
    cliente: ClienteHttp,
    *,
    data_inicio: str,
    data_fim: str,
    canario_validado: bool,
    linha_base: frozenset[str] | None,
    lookup: LookupIdExterno,
    politica: PoliticaRetry = PoliticaRetry(),
    coletar_nominais: bool = True,
) -> ResultadoRodadaVotacoes:
    """Uma rodada: coleta votações, avalia contrato, para cada votação aprovada
    coleta e resolve os nominais."""
    erro_falha: str | None = None
    erro_instabilidade: str | None = None
    votacoes_bronze: list[RegistroBronze] = []

    try:
        votacoes_bronze = coletar_bronze_votacoes(
            cliente, data_inicio=data_inicio, data_fim=data_fim, politica=politica,
        )
    except ErroFalha as e:
        erro_falha = str(e)
    except ErroInstabilidade as e:
        erro_instabilidade = str(e)

    amostra = votacoes_bronze[0].payload if votacoes_bronze else None
    contrato = avaliar(
        canario_validado=canario_validado,
        resposta=[amostra] if amostra is not None else None,
        erro_falha=erro_falha,
        erro_instabilidade=erro_instabilidade,
        linha_base=linha_base,
        criticos=CAMPOS_CRITICOS_VOTACAO,
    )

    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaVotacoes(
            estado=contrato.estado, detalhe=contrato.detalhe,
            votacoes_bronze=votacoes_bronze,
        )

    # O contrato roda sobre a LISTA (barata). A transformação prata, porém,
    # precisa do DETALHE de cada votação — é só lá que existe
    # `proposicoesAfetadas` (Metodologia §10). Buscamos um detalhe por votação.
    # Se o detalhe falhar, não derruba a rodada: cai no payload da lista, e a
    # matéria fica None (degradação honesta, não invenção).
    detalhes_bronze: list[RegistroBronze] = []
    for reg in votacoes_bronze:
        vid = str(reg.payload.get("id"))
        try:
            detalhes_bronze.append(
                coletar_bronze_votacao_detalhe(cliente, vid, politica=politica)
            )
        except (ErroFalha, ErroInstabilidade):
            detalhes_bronze.append(reg)

    prata = processar_votacoes_para_prata(detalhes_bronze)

    nominais: dict[str, ResultadoVotos] = {}
    placar_violacoes: dict[str, list[Violacao]] = {}
    votos_bronze_por_votacao: dict[str, list[RegistroBronze]] = {}
    if coletar_nominais:
        for votacao_prata in prata.aprovados:
            vid = votacao_prata["id_fonte"]
            try:
                votos_bronze = coletar_bronze_votos(cliente, vid, politica=politica)
            except (ErroFalha, ErroInstabilidade):
                # Uma votação que não devolve nominais não derruba a rodada
                # inteira — vai como resultado vazio, chamador decide.
                nominais[vid] = ResultadoVotos()
                continue
            votos_bronze_por_votacao[vid] = votos_bronze
            res = processar_votos_para_prata(
                votos_bronze, vid,
                lookup=lookup,
                votacao_declarada_secreta=bool(votacao_prata.get("secreta")),
                votacao_declarada_nominal=votacao_prata.get("nominal"),
            )
            nominais[vid] = res
            # Reconciliação §5.2: placar declarado × votos individuais.
            viols = conferir_placar_contra_nominais(votacao_prata, res)
            if viols:
                placar_violacoes[vid] = viols

    return ResultadoRodadaVotacoes(
        estado=contrato.estado, detalhe=contrato.detalhe,
        votacoes_bronze=votacoes_bronze, votacoes_prata=prata,
        nominais=nominais, placar_violacoes=placar_violacoes,
        detalhes_bronze=detalhes_bronze, votos_bronze=votos_bronze_por_votacao,
    )
