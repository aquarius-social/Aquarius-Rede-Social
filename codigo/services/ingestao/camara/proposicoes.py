"""Coletor da Câmara — proposições.

Fonte: `https://dadosabertos.camara.leg.br/api/v2/proposicoes`.

Este é o primeiro tentáculo, e tem o papel deliberado de exercitar todas as
disciplinas antes da largada em escala: pipeline em camadas, portão de
qualidade, contrato com canário, dedup por conteúdo, janela móvel.

CANÁRIO VALIDADO AO VIVO em 2026-09-16 (janela jun/2025, endpoint `/proposicoes`).
A resposta de lista traz as chaves: `id, siglaTipo, numero, ano, ementa,
dataApresentacao, codTipo, uri`. Os 6 campos críticos (`CAMPOS_CRITICOS_PROPOSICAO`)
estão TODOS presentes (§2 — amostra e data registradas).

Ressalvas confirmadas contra a interface real:
- `statusProposicao` NÃO vem na resposta de lista → `situacao` fica None aqui; a
  situação real exige um passo de enriquecimento pelo detalhe (futuro).
- `uriAutores` também NÃO vem na lista (ela traz `uri`, da própria proposição) →
  `uri_autores` fica None; a autoria não é resolvida por aqui.

`CAMPOS_CRITICOS_PROPOSICAO` é a lista mínima que o portão exige; qualquer
divergência futura precisa ser tratada como QUEBRA (seção 19) e a transformação
ajustada, não silenciada.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from contrato.canario import EstadoContrato, avaliar
from pipeline.camadas import (
    RegistroBronze,
    ResultadoPortao,
    Violacao,
    campo_em,
    campo_obrigatorio,
    portao_bronze_prata,
)
from pipeline.coletor import (
    MAX_JANELA_CAMARA_DIAS,
    ClienteHttp,
    ErroFalha,
    ErroInstabilidade,
    JanelaMovel,
    PoliticaRetry,
    fatiar_periodo,
    obter_com_retry,
)

FONTE = "camara.proposicoes"
BASE = "https://dadosabertos.camara.leg.br/api/v2"

# Campos que a camada prata exige. Se algum sumir, é QUEBRA (seção 19).
CAMPOS_CRITICOS_PROPOSICAO = frozenset({
    "id", "siglaTipo", "numero", "ano", "ementa", "dataApresentacao"
})

# Enum de tipos que o modelo suporta hoje. A Câmara publica outros
# (`REQ`, `INC`, etc.); adicionar aqui é decisão de escopo do produto, não
# ausência técnica.
TIPOS_SUPORTADOS = {"PL", "PEC", "MP", "PLP", "PDL"}


# -----------------------------------------------------------------------------
# Coleta em bronze — janela móvel, retry, sem transformar nada
# -----------------------------------------------------------------------------

def coletar_bronze(
    cliente: ClienteHttp,
    ate: date,
    janela: JanelaMovel,
    *,
    politica: PoliticaRetry = PoliticaRetry(),
    itens_por_pagina: int = 100,
    limite_paginas: int = 100,
) -> list[RegistroBronze]:
    """Coleta proposições apresentadas na janela móvel.

    A API `/proposicoes` rejeita intervalos de `dataApresentacao` largos (HTTP
    400, verificado ao vivo 2026-09): a janela é FATIADA em pedaços curtos
    (`MAX_JANELA_CAMARA_DIAS`). A janela incremental (30 dias) cabe num pedaço só;
    o backfill (~1 ano) vira ~6 pedaços. Paginação segue os `links`; `limite_paginas`
    é backstop contra laço infinito por bug de contrato — nunca contra volume.
    """
    inicio, fim = janela.intervalo(ate)
    url = f"{BASE}/proposicoes"
    bronze: list[RegistroBronze] = []
    for sub_ini, sub_fim in fatiar_periodo(inicio, fim, MAX_JANELA_CAMARA_DIAS):
        bronze.extend(_coletar_intervalo(
            cliente, url, sub_ini, sub_fim, politica=politica,
            itens_por_pagina=itens_por_pagina, limite_paginas=limite_paginas))
    return bronze


def _coletar_intervalo(
    cliente: ClienteHttp,
    url: str,
    inicio: date,
    fim: date,
    *,
    politica: PoliticaRetry,
    itens_por_pagina: int,
    limite_paginas: int,
) -> list[RegistroBronze]:
    """Coleta UM sub-intervalo curto, paginando pelos `links` da API."""
    params: dict[str, Any] = {
        "dataApresentacaoInicio": inicio.isoformat(),
        "dataApresentacaoFim": fim.isoformat(),
        "itens": itens_por_pagina,
        "ordem": "ASC",
        "ordenarPor": "id",
    }
    bronze: list[RegistroBronze] = []
    pagina = 1
    proximo: str | None = None
    while pagina <= limite_paginas:
        if proximo is None:
            corpo = obter_com_retry(cliente, url, params=params, politica=politica)
        else:
            corpo = obter_com_retry(cliente, proximo, politica=politica)
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
# Portão bronze → prata
# -----------------------------------------------------------------------------

def transformar_proposicao(payload: dict) -> dict:
    """Normaliza um item da Câmara para o shape da camada prata.

    A camada prata tem o vocabulário do Aquarius, não o da fonte. É aqui que
    `siglaTipo` vira `tipo`, e datas viram ISO-8601 (a fonte já entrega em
    ISO — a conversão explícita é para blindar contra mudança).
    """
    return {
        "id_fonte": str(payload["id"]),
        "tipo": payload.get("siglaTipo"),
        "numero": _int(payload.get("numero")),
        "ano": _int(payload.get("ano")),
        "identificador": _identificador(payload),
        # Limpeza defensiva. A Metodologia (seção 3.2) manda decompor campos
        # de texto livre "segundo o formato real observado". A prática da BD
        # em `pipelines/crawler/camara_dados_abertos/tasks.py` confirma
        # empiricamente que a fonte publica `;`, `\n` e `\r` DENTRO da ementa.
        # Sem esta limpeza, qualquer exportação CSV nossa quebra em silêncio.
        "ementa": _limpar_texto_livre(payload.get("ementa")),
        "data_apresentacao": payload.get("dataApresentacao"),
        # `statusProposicao` pode faltar em resposta de lista; é enriquecido
        # depois. Mantemos o campo mesmo quando ausente para que a camada
        # ouro conheça o formato.
        "situacao": _situacao(payload),
        "uri_autores": payload.get("uriAutores"),
        "casa_origem": "camara",
    }


def _identificador(payload: dict) -> str | None:
    sigla = payload.get("siglaTipo")
    numero = payload.get("numero")
    ano = payload.get("ano")
    if not sigla or numero is None or ano is None:
        return None
    return f"{sigla} {numero}/{ano}"


def _int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _limpar_texto_livre(v: Any) -> str | None:
    """Remove separadores CSV e quebras de linha internas.

    Não converte para minúscula, não altera acentos — a Metodologia (seção
    3.2) é explícita ao preservar codificação e caso.
    """
    if v is None:
        return None
    texto = str(v)
    # Ordem importa: normalizar CRLF -> LF antes de trocar por espaço evita
    # espaços duplos quando a fonte usa \r\n.
    texto = texto.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    texto = texto.replace(";", ",")  # ; vira , (preserva significado de listagem)
    texto = " ".join(texto.split())  # normaliza espaços múltiplos
    return texto or None


def _situacao(payload: dict) -> str | None:
    status = payload.get("statusProposicao") or {}
    if isinstance(status, dict):
        return status.get("descricaoSituacao") or status.get("descricaoTramitacao")
    return None


# Verificadores extras específicos das proposições.

def _numero_ano_positivos(registro: dict) -> Violacao | None:
    for campo in ("numero", "ano"):
        v = registro.get(campo)
        if v is None or (isinstance(v, int) and v <= 0):
            return Violacao("precisao", f"{campo} inválido: {v!r}")
    return None


VERIFICADORES_PROPOSICAO = [
    campo_obrigatorio("id_fonte"),
    campo_obrigatorio("tipo"),
    campo_em("tipo", TIPOS_SUPORTADOS),
    campo_obrigatorio("ementa"),
    campo_obrigatorio("data_apresentacao"),
    _numero_ano_positivos,
]


def processar_para_prata(bronze: list[RegistroBronze]) -> ResultadoPortao:
    """Aplica o portão bronze → prata para proposições."""
    return portao_bronze_prata(
        bronze,
        transformar=transformar_proposicao,
        verificadores=VERIFICADORES_PROPOSICAO,
    )


# -----------------------------------------------------------------------------
# Rodada completa com teste de contrato
# -----------------------------------------------------------------------------

@dataclass
class ResultadoRodada:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    prata: ResultadoPortao | None


def rodada(
    cliente: ClienteHttp,
    *,
    ate: date,
    janela: JanelaMovel,
    canario_validado: bool,
    linha_base: frozenset[str] | None,
    politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodada:
    """Uma rodada completa: coleta, avalia contrato, aplica portão.

    Em qualquer estado diferente de OK e ALERTA, a fase de portão é
    pulada — a seção 19 é clara ao suspender a ingestão da área em QUEBRA.
    ALERTA (campo novo) segue processando: campo novo não muda o que já
    existe, só sinaliza leitura humana.
    """
    erro_instabilidade: str | None = None
    erro_falha: str | None = None
    bronze: list[RegistroBronze] = []

    try:
        bronze = coletar_bronze(cliente, ate, janela, politica=politica)
    except ErroInstabilidade as e:
        erro_instabilidade = str(e)
    except ErroFalha as e:
        erro_falha = str(e)

    # Para o teste de contrato, examinamos o payload do primeiro item bronze
    # como amostra da estrutura atual — a linha de base é comparada campo a
    # campo (seção 19).
    amostra = bronze[0].payload if bronze else None
    resultado_contrato = avaliar(
        canario_validado=canario_validado,
        resposta=[amostra] if amostra is not None else None,
        erro_instabilidade=erro_instabilidade,
        erro_falha=erro_falha,
        linha_base=linha_base,
        criticos=CAMPOS_CRITICOS_PROPOSICAO,
    )

    if resultado_contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodada(
            estado=resultado_contrato.estado,
            detalhe=resultado_contrato.detalhe,
            bronze=bronze,
            prata=None,
        )

    prata = processar_para_prata(bronze) if bronze else ResultadoPortao()
    return ResultadoRodada(
        estado=resultado_contrato.estado,
        detalhe=resultado_contrato.detalhe,
        bronze=bronze,
        prata=prata,
    )
