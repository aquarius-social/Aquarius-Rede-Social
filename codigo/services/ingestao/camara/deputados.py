"""Coletor da Câmara — deputados (perfis parlamentares).

Fonte:
    https://dadosabertos.camara.leg.br/api/v2/deputados            (lista por legislatura)
    https://dadosabertos.camara.leg.br/api/v2/deputados/{id}       (detalhe)

Por que este coletor precede o de votações na prática: cada voto nominal se
vincula a um perfil por `id_externo` (sistema='camara'). Sem os deputados
ingeridos, todo nominal cai na quarentena por integridade referencial. Este é
o gargalo natural (ESTADO_ATUAL.md, Rota A → depois deputados).

DISCIPLINAS DA METODOLOGIA §12 (verificado contra a API viva em 2026-07-29):

  - Dedup por identificador ANTES de qualquer contagem. A listagem por
    legislatura repete o mesmo `id` uma vez por filiação partidária vigente no
    período; contar linhas mede estados de filiação, não pessoas. Aqui, dedup
    por `id` produz um perfil por pessoa (`deduplicar_por_id`).
  - Atributo resolvido na data do fato. UF de mandato e partido são TEMPORAIS
    (mudam ao longo do mandato) e NÃO viram atributo atemporal do perfil — vão
    como pista (`mandato_hint`) para o passo próprio de `vinculo_temporal`, que
    NÃO é feito neste primeiro passe. O perfil recebe só identidade estável.
  - O histórico de transições é a fonte menos disponível de todas (alterna
    resposta e falha, timeout ~15s): é etapa própria, coletada em lote com
    retry e persistida, nunca consultada ao vivo. Fora deste primeiro passe.

Vínculo por identificador embutido, grau 'direto', método 'fonte_direta' (§6):
a própria fonte declara o `id`, então a ligação é direta, sem convergência.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any

from contrato.canario import EstadoContrato, avaliar
from pipeline.camadas import (
    RegistroBronze,
    ResultadoPortao,
    Violacao,
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

FONTE = "camara.deputados"
BASE = "https://dadosabertos.camara.leg.br/api/v2"

# Campos críticos da LISTA de deputados. Verificado contra a API viva em
# 2026-07-29: todos presentes. Se algum sumir, é QUEBRA (§19).
CAMPOS_CRITICOS_DEPUTADO = frozenset({
    "id", "nome", "siglaUf", "siglaPartido", "idLegislatura"
})


# -----------------------------------------------------------------------------
# Coleta — bronze
# -----------------------------------------------------------------------------

def coletar_bronze_deputados(
    cliente: ClienteHttp,
    *,
    id_legislatura: int | None = None,
    politica: PoliticaRetry = PoliticaRetry(),
    itens_por_pagina: int = 100,
    limite_paginas: int = 100,
) -> list[RegistroBronze]:
    """Lista deputados. Sem `id_legislatura`, a fonte devolve a atual.

    Ainda NÃO deduplica: a lista pode trazer o mesmo `id` mais de uma vez (uma
    linha por filiação vigente). A dedup é etapa própria, aplicada na prata.
    """
    url = f"{BASE}/deputados"
    params: dict[str, Any] = {"itens": itens_por_pagina, "ordem": "ASC",
                              "ordenarPor": "id"}
    if id_legislatura is not None:
        params["idLegislatura"] = id_legislatura

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
            bronze.append(RegistroBronze.de(FONTE, url, item))
        proximo = _proximo_link(corpo)
        if proximo is None:
            break
        pagina += 1
    return bronze


def coletar_bronze_deputado_detalhe(
    cliente: ClienteHttp,
    deputado_id: str,
    *,
    politica: PoliticaRetry = PoliticaRetry(),
) -> RegistroBronze:
    """Detalhe de UM deputado (GET /deputados/{id}).

    Traz os atributos de pessoa natural (nomeCivil, dataNascimento,
    naturalidade) que a lista não tem — sinais de resolução da §5.3. O `dados`
    do detalhe é um objeto, não uma lista.
    """
    url = f"{BASE}/deputados/{deputado_id}"
    corpo = obter_com_retry(cliente, url, politica=politica)
    dado = (corpo or {}).get("dados") or {}
    return RegistroBronze.de(FONTE, url, dado)


def _proximo_link(corpo: Any) -> str | None:
    for link in (corpo or {}).get("links", []) or []:
        if link.get("rel") == "next" and link.get("href"):
            return link["href"]
    return None


# -----------------------------------------------------------------------------
# Dedup por identificador — a disciplina central da §12
# -----------------------------------------------------------------------------

def deduplicar_por_id(bronze: list[RegistroBronze]) -> list[RegistroBronze]:
    """Um registro por `id` de deputado, preservando a ordem de chegada.

    §12: a listagem repete o mesmo `id` uma vez por filiação vigente; dedup por
    identificador PRECEDE qualquer contagem de pessoas. Mantém-se a primeira
    ocorrência — as demais diferem só na filiação partidária, que é dado
    temporal e não pertence ao perfil (vai por `vinculo_temporal`, à parte).
    """
    vistos: set[str] = set()
    unicos: list[RegistroBronze] = []
    for reg in bronze:
        ident = str(reg.payload.get("id"))
        if ident in vistos:
            continue
        vistos.add(ident)
        unicos.append(reg)
    return unicos


# -----------------------------------------------------------------------------
# Transformação — bronze → prata (perfil + vínculo id_externo)
# -----------------------------------------------------------------------------

def _slug(nome: str, id_fonte: str) -> str:
    """Slug estável e único. Nome sozinho colide (homonímia, §6.2), então o id
    da fonte entra como desambiguador — o mesmo papel do sufixo geracional."""
    base = unicodedata.normalize("NFKD", nome or "")
    base = base.encode("ascii", "ignore").decode("ascii").lower()
    limpo = "".join(c if c.isalnum() else "-" for c in base)
    limpo = "-".join(p for p in limpo.split("-") if p)
    return f"{limpo}-{id_fonte}" if limpo else id_fonte


def transformar_deputado(payload: dict, detalhe: dict | None = None) -> dict:
    """Normaliza um item de deputado para a prata.

    `payload` é o item da LISTA (traz o nome parlamentar, foto e a filiação
    vigente). `detalhe`, quando fornecido, é a resposta de `GET /deputados/{id}`
    e adiciona os atributos de PESSOA NATURAL — nome civil, nascimento e
    naturalidade — que a §5.3 usa como sinais de convergência na resolução
    bicameral, e que a §3.5 mantém restritos à camada interna.

    Sem `detalhe`, esses campos ficam None (passe só-lista, ainda válido).

    Produz o alvo de persistência: identidade ESTÁVEL do perfil (`profiles`) +
    vínculo para `id_externo`. UF de mandato e partido são temporais (§12, D3) e
    vão em `mandato_hint`, jamais como atributo atemporal do perfil. Do detalhe
    tomamos SÓ os atributos estáveis: `ultimoStatus` (partido/UF correntes) é
    temporal e é deliberadamente ignorado aqui.
    """
    id_fonte = str(payload["id"])
    nome = payload.get("nome")
    d = detalhe or {}
    return {
        "id_fonte": id_fonte,
        "tipo": "parlamentar",
        "nome": nome,
        "slug": _slug(nome, id_fonte) if nome else None,
        "foto_url": payload.get("urlFoto"),
        "ativo": True,
        # Atributos de pessoa natural (do detalhe) — PII restrita à resolução
        # (§3.5), sinais da §5.3. Ausentes quando não houve enriquecimento.
        "nome_civil": d.get("nomeCivil"),
        "data_nascimento": d.get("dataNascimento"),
        "naturalidade_municipio": d.get("municipioNascimento"),
        "naturalidade_uf": d.get("ufNascimento"),
        # Vínculo → id_externo (§6): a fonte declarou o id, ligação direta.
        "sistema_externo": "camara",
        "identificador_externo": id_fonte,
        "metodo_ligacao": "fonte_direta",
        "grau": "direto",
        # Pista temporal para o passo de vinculo_temporal — NÃO é atributo
        # atemporal do perfil. Preserva o snapshot da fonte sem achatá-lo.
        "mandato_hint": {
            "uf": payload.get("siglaUf"),
            "partido": payload.get("siglaPartido"),
            "id_legislatura": payload.get("idLegislatura"),
        },
    }


def _ligacao_coerente(registro: dict) -> Violacao | None:
    """A migration `id_externo` exige: grau 'direto' só com método declarado
    pela fonte (fonte_direta) ou conferência humana. Guardamos a mesma regra no
    portão para não empurrar à persistência algo que o banco recusaria."""
    if registro.get("grau") == "direto" and \
            registro.get("metodo_ligacao") not in ("fonte_direta", "conferencia_humana"):
        return Violacao(
            "integridade_referencial",
            "grau 'direto' exige método 'fonte_direta' ou 'conferencia_humana'",
        )
    return None


VERIFICADORES_DEPUTADO = [
    campo_obrigatorio("id_fonte"),
    campo_obrigatorio("nome"),
    campo_obrigatorio("slug"),
    campo_obrigatorio("identificador_externo"),
    _ligacao_coerente,
]


def processar_deputados_para_prata(
    bronze: list[RegistroBronze],
    detalhes: dict[str, dict] | None = None,
) -> ResultadoPortao:
    """Dedup por id (§12) e então o portão bronze → prata.

    A ordem importa: deduplicar ANTES do portão evita contar a mesma pessoa
    duas vezes e evita gerar dois perfis com o mesmo `id_externo` (que a
    constraint `id_externo_unico` recusaria de qualquer modo). O dedup é
    idempotente, então chamar sobre lista já deduplicada é inócuo.

    `detalhes` (opcional) mapeia id da fonte → payload do detalhe, para o
    enriquecimento com atributos de pessoa natural. Quem não tem detalhe entra
    com esses campos em None — degradação honesta, não erro.
    """
    det = detalhes or {}

    def _transformar(item: dict) -> dict:
        return transformar_deputado(item, det.get(str(item.get("id"))))

    return portao_bronze_prata(
        deduplicar_por_id(bronze),
        transformar=_transformar,
        verificadores=VERIFICADORES_DEPUTADO,
    )


# -----------------------------------------------------------------------------
# Rodada completa com teste de contrato
# -----------------------------------------------------------------------------

@dataclass
class ResultadoRodadaDeputados:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    prata: ResultadoPortao | None = None


def rodada_deputados(
    cliente: ClienteHttp,
    *,
    canario_validado: bool,
    linha_base: frozenset[str] | None,
    id_legislatura: int | None = None,
    enriquecer: bool = True,
    politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodadaDeputados:
    """Uma rodada: coleta a lista, avalia o contrato, dedup + (detalhe) + portão.

    Em FALHA ou QUEBRA a fase de prata é pulada — a §19 suspende a ingestão da
    área. ALERTA (campo novo) segue processando.

    Com `enriquecer=True`, busca o detalhe de cada pessoa (uma chamada por id
    deduplicado) para preencher os atributos de pessoa natural. O detalhe é o
    endpoint estável (`/deputados/{id}`), não o histórico instável (§12, D2):
    ainda assim, uma falha pontual não derruba a rodada — aquela pessoa entra
    sem PII, com o restante intacto.
    """
    erro_falha: str | None = None
    erro_instabilidade: str | None = None
    bronze: list[RegistroBronze] = []

    try:
        bronze = coletar_bronze_deputados(
            cliente, id_legislatura=id_legislatura, politica=politica,
        )
    except ErroFalha as e:
        erro_falha = str(e)
    except ErroInstabilidade as e:
        erro_instabilidade = str(e)

    amostra = bronze[0].payload if bronze else None
    contrato = avaliar(
        canario_validado=canario_validado,
        resposta=[amostra] if amostra is not None else None,
        erro_falha=erro_falha,
        erro_instabilidade=erro_instabilidade,
        linha_base=linha_base,
        criticos=CAMPOS_CRITICOS_DEPUTADO,
    )

    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaDeputados(
            estado=contrato.estado, detalhe=contrato.detalhe, bronze=bronze,
        )

    if not bronze:
        return ResultadoRodadaDeputados(
            estado=contrato.estado, detalhe=contrato.detalhe,
            bronze=bronze, prata=ResultadoPortao(),
        )

    unicos = deduplicar_por_id(bronze)

    detalhes: dict[str, dict] = {}
    if enriquecer:
        for reg in unicos:
            did = str(reg.payload.get("id"))
            try:
                det = coletar_bronze_deputado_detalhe(cliente, did, politica=politica)
                detalhes[did] = det.payload
            except (ErroFalha, ErroInstabilidade):
                # Falha pontual do detalhe não derruba a rodada — segue sem PII.
                continue

    prata = processar_deputados_para_prata(unicos, detalhes)
    return ResultadoRodadaDeputados(
        estado=contrato.estado, detalhe=contrato.detalhe,
        bronze=bronze, prata=prata,
    )
