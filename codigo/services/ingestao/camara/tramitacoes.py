"""Coletor da Câmara — tramitações (Área D, §11).

Fonte: `https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id}/tramitacoes`.
Cada linha é um despacho/movimentação de UMA proposição: sequência, data,
órgão onde está, descrição e o texto do despacho.

DISCIPLINAS DA §11 / §5.2 (campos verificados contra a API viva, 2026-07-29):

  - Sequência temporal monotônica (§5.2): ordenadas por `sequencia`, as datas
    não retrocedem. É identidade CRUZADA (precisa da lista inteira da
    proposição), então vive em `conferir_sequencia_monotonica`, não no portão
    linha a linha — do mesmo modo que a reconciliação de placar em votações.

  - Ressalva bicameral (§11): este endpoint traz SÓ a perna da Câmara. Uma
    matéria remetida ao Senado aparece aqui como parada, o que sugere falsamente
    projeto estagnado. Por isso todo registro carrega `casa='camara'` — a regra
    de resposta (§11) exige declarar qual casa se observa, ou juntar as duas.

  - Proveniência do texto (§11): `despacho` é texto da secretaria ou do relator
    — parte interessada. É uma proveniência CONSTANTE do campo (não varia por
    linha), documentada aqui; o consumidor jamais o lê como narração neutra.

O que a API v2 NÃO expõe: `sequencia` e o órgão de cada linha existem, mas NÃO
há par origem→destino explícito (só um `siglaOrgao` por linha). Logo a
identidade "destino de um despacho igual à origem do seguinte" (§5.2) não é
verificável neste endpoint — não a inventamos. Fica a monotonicidade, que é.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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

FONTE = "camara.tramitacoes"
BASE = "https://dadosabertos.camara.leg.br/api/v2"

# Campos críticos da tramitação. Verificado ao vivo (2026-07-29): presentes.
CAMPOS_CRITICOS_TRAMITACAO = frozenset({
    "sequencia", "dataHora", "descricaoTramitacao"
})


# -----------------------------------------------------------------------------
# Coleta — bronze
# -----------------------------------------------------------------------------

def coletar_bronze_tramitacoes(
    cliente: ClienteHttp,
    proposicao_id_fonte: str,
    *,
    politica: PoliticaRetry = PoliticaRetry(),
    limite_paginas: int = 50,
) -> list[RegistroBronze]:
    """Tramitações de UMA proposição.

    NÃO envia parâmetros de paginação/ordenação: este endpoint os REJEITA com
    HTTP 400 ("parâmetro inválido") — tanto `itens` quanto `ordem` sem
    `ordenarPor`. É o mesmo comportamento do endpoint de votos (§10): vem íntegro
    numa resposta. Medido ao vivo (2026-07-31): `?itens=100` → 400; sem params →
    200. A ordenação para a checagem monotônica é feita localmente, sobre
    `sequencia`. Mandar `itens` foi o bug que zerava as tramitações.
    """
    url = f"{BASE}/proposicoes/{proposicao_id_fonte}/tramitacoes"
    bronze: list[RegistroBronze] = []
    pagina = 1
    proximo: str | None = None
    while pagina <= limite_paginas:
        corpo = obter_com_retry(cliente, proximo or url, politica=politica)
        for item in (corpo or {}).get("dados", []):
            bronze.append(RegistroBronze.de(FONTE, url, item))
        proximo = _proximo_link(corpo)
        if proximo is None:
            break
        pagina += 1
    return bronze


def _proximo_link(corpo: Any) -> str | None:
    for link in (corpo or {}).get("links", []) or []:
        if link.get("rel") == "next" and link.get("href"):
            return link["href"]
    return None


# -----------------------------------------------------------------------------
# Transformação — bronze → prata
# -----------------------------------------------------------------------------

def _int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _texto(v: Any) -> str | None:
    """Normaliza texto livre: quebras de linha viram espaço, bordas aparadas.
    Preserva caso e acento (§3.2). Vazio vira None."""
    if v is None:
        return None
    t = str(v).replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    t = " ".join(t.split())
    return t or None


def transformar_tramitacao(payload: dict, proposicao_id_fonte: str,
                           *, casa: str = "camara") -> dict:
    """Normaliza uma tramitação para a prata (alvo: tabela `tramitacao`).

    `proposicao_id_fonte` é injetado — a tramitação pertence à proposição pela
    URL, não por um campo do payload. `casa` fica explícito para a ressalva
    bicameral da §11.
    """
    return {
        "proposicao_id_fonte": str(proposicao_id_fonte),
        "casa": casa,
        "sequencia": _int(payload.get("sequencia")),
        "data_hora": payload.get("dataHora"),
        "orgao_sigla": payload.get("siglaOrgao"),
        "descricao": _texto(payload.get("descricaoTramitacao")),
        # Texto de parte interessada (secretaria/relator) — proveniência
        # constante do campo, ver docstring do módulo.
        "despacho": _texto(payload.get("despacho")),
    }


def _sequencia_valida(registro: dict) -> Violacao | None:
    seq = registro.get("sequencia")
    if seq is None or seq < 1:
        return Violacao("precisao", f"sequência inválida: {seq!r}")
    return None


VERIFICADORES_TRAMITACAO = [
    campo_obrigatorio("data_hora"),
    campo_obrigatorio("descricao"),
    _sequencia_valida,
]


def processar_tramitacoes_para_prata(
    bronze: list[RegistroBronze], proposicao_id_fonte: str,
) -> ResultadoPortao:
    def _transformar(payload: dict) -> dict:
        return transformar_tramitacao(payload, proposicao_id_fonte)

    return portao_bronze_prata(
        bronze, transformar=_transformar, verificadores=VERIFICADORES_TRAMITACAO,
    )


def conferir_sequencia_monotonica(tramitacoes: list[dict]) -> list[Violacao]:
    """Identidade §5.2: ordenadas por `sequencia`, as DATAS não retrocedem.

    Comparação por data de calendário (`data_hora[:10]`), não por instante — e
    isto é deliberado, aprendido da fonte viva. Medição em 2026-07-29 (PL
    736/2015): algumas tramitações vêm carimbadas às 00:00 (só data, sem hora
    real), então uma sequência posterior do MESMO dia parece "anterior" a uma de
    13:16. Isso não é violação — é hora ausente, não anterioridade. A `sequencia`
    é a ordem autoritativa; a identidade útil é a data não recuar de um passo
    para o seguinte. Comparar por instante gritaria à toa (§19), que é o oposto
    de um monitor útil. Uma data que de fato retrocede é incoerência real.

    Formato ISO-8601 estável → prefixo de 10 chars é a data, e a ordem
    lexicográfica coincide com a cronológica.
    """
    ordenadas = sorted(
        (t for t in tramitacoes if t.get("sequencia") is not None),
        key=lambda t: t["sequencia"],
    )
    violacoes: list[Violacao] = []
    anterior: dict | None = None
    for t in ordenadas:
        data_t = (t.get("data_hora") or "")[:10]
        data_ant = (anterior.get("data_hora") or "")[:10] if anterior else ""
        if anterior is not None and data_t and data_ant and data_t < data_ant:
            violacoes.append(Violacao(
                "consistencia",
                f"sequência {t['sequencia']} tem data {data_t} anterior à "
                f"sequência {anterior['sequencia']} ({data_ant}) — "
                f"cadeia não monotônica",
            ))
        anterior = t
    return violacoes


# -----------------------------------------------------------------------------
# Rodada completa com teste de contrato
# -----------------------------------------------------------------------------

@dataclass
class ResultadoRodadaTramitacoes:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    prata: ResultadoPortao | None = None
    sequencia_violacoes: list[Violacao] = field(default_factory=list)


def rodada_tramitacoes(
    cliente: ClienteHttp,
    proposicao_id_fonte: str,
    *,
    canario_validado: bool,
    linha_base: frozenset[str] | None,
    politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodadaTramitacoes:
    """Uma rodada para UMA proposição: coleta, contrato, portão, monotonicidade.

    Em FALHA/QUEBRA a prata é pulada (§19). O bronze disponível é preservado.
    """
    erro_falha: str | None = None
    erro_instabilidade: str | None = None
    bronze: list[RegistroBronze] = []

    try:
        bronze = coletar_bronze_tramitacoes(
            cliente, proposicao_id_fonte, politica=politica,
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
        criticos=CAMPOS_CRITICOS_TRAMITACAO,
    )

    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaTramitacoes(
            estado=contrato.estado, detalhe=contrato.detalhe, bronze=bronze,
        )

    prata = processar_tramitacoes_para_prata(bronze, proposicao_id_fonte)
    seq_viol = conferir_sequencia_monotonica(prata.aprovados)
    return ResultadoRodadaTramitacoes(
        estado=contrato.estado, detalhe=contrato.detalhe,
        bronze=bronze, prata=prata, sequencia_violacoes=seq_viol,
    )
