"""Coletor da Câmara — discursos de deputados (Área G, §13).

Fonte: https://dadosabertos.camara.leg.br/api/v2/deputados/{id}/discursos
Por deputado, com janela de data (dataInicio/dataFim), paginado por `links`.
Verificado ao vivo em 2026-07-31 (deputado 74784, janela 2024).

Como o VOTO (§10), o discurso NÃO tem id próprio na fonte — sua identidade é o
par (deputado, dataHoraInicio). A prata carrega `id_fonte` composto e o
`parlamentar_id_fonte` (o deputado), que a persistência resolve a `profile_id`
por `id_externo` (sistema='camara') antes de gravar (§6).

A transcrição integral (milhares de caracteres) NÃO vai para a prata: guarda-se
o resumo + a flag `tem_transcricao` + a `url_texto` (citação da fonte, princípio
inegociável de proveniência).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contrato.canario import EstadoContrato, avaliar
from pipeline.camadas import (
    RegistroBronze,
    ResultadoPortao,
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

FONTE = "camara.discursos"
BASE = "https://dadosabertos.camara.leg.br/api/v2"

CAMPOS_CRITICOS_DISCURSO = frozenset({
    "dataHoraInicio", "tipoDiscurso", "urlTexto",
})


def _proximo_link(corpo: Any) -> str | None:
    for link in (corpo or {}).get("links", []) or []:
        if link.get("rel") == "next" and link.get("href"):
            return link["href"]
    return None


def coletar_bronze_discursos(
    cliente: ClienteHttp,
    deputado_id: str,
    *,
    data_inicio: str,
    data_fim: str,
    politica: PoliticaRetry = PoliticaRetry(),
    itens_por_pagina: int = 100,
    limite_paginas: int = 100,
) -> list[RegistroBronze]:
    """Discursos de UM deputado na janela [data_inicio, data_fim] (YYYY-MM-DD)."""
    url = f"{BASE}/deputados/{deputado_id}/discursos"
    params: dict[str, Any] = {
        "dataInicio": data_inicio, "dataFim": data_fim,
        "itens": itens_por_pagina, "ordem": "DESC",
        "ordenarPor": "dataHoraInicio",
    }
    bronze: list[RegistroBronze] = []
    pagina = 1
    proximo: str | None = None
    while pagina <= limite_paginas:
        corpo = obter_com_retry(
            cliente, proximo or url,
            params=None if proximo else params, politica=politica)
        for item in (corpo or {}).get("dados", []):
            bronze.append(RegistroBronze.de(FONTE, url, item))
        proximo = _proximo_link(corpo)
        if proximo is None:
            break
        pagina += 1
    return bronze


def _data(valor: Any) -> str | None:
    if not valor:
        return None
    return str(valor)[:10]


def transformar_discurso(payload: dict, deputado_id: str) -> dict:
    inicio = payload.get("dataHoraInicio")
    return {
        "casa": "camara",
        "sistema": "camara",
        "parlamentar_id_fonte": str(deputado_id),
        # Identidade composta (discurso não tem id de fonte próprio).
        "id_fonte": f"{deputado_id}:{inicio}",
        "data": _data(inicio),
        "tipo": payload.get("tipoDiscurso"),
        "sumario": payload.get("sumario"),
        "keywords": payload.get("keywords"),
        "url_texto": payload.get("urlTexto"),
        "url_video": payload.get("urlVideo"),
        "url_audio": payload.get("urlAudio"),
        "tem_transcricao": bool((payload.get("transcricao") or "").strip()),
    }


VERIFICADORES_DISCURSO = [
    campo_obrigatorio("parlamentar_id_fonte"),
    campo_obrigatorio("id_fonte"),
    campo_obrigatorio("data"),
]


def processar_discursos_para_prata(
    bronze: list[RegistroBronze], deputado_id: str
) -> ResultadoPortao:
    def _transformar(item: dict) -> dict:
        return transformar_discurso(item, deputado_id)

    return portao_bronze_prata(
        bronze, transformar=_transformar, verificadores=VERIFICADORES_DISCURSO)


@dataclass
class ResultadoRodadaDiscursos:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    prata: ResultadoPortao | None = None


def rodada_discursos(
    cliente: ClienteHttp,
    deputado_id: str,
    *,
    canario_validado: bool,
    linha_base: frozenset[str] | None,
    data_inicio: str,
    data_fim: str,
    politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodadaDiscursos:
    erro_falha: str | None = None
    erro_instabilidade: str | None = None
    bronze: list[RegistroBronze] = []
    try:
        bronze = coletar_bronze_discursos(
            cliente, deputado_id, data_inicio=data_inicio, data_fim=data_fim,
            politica=politica)
    except ErroFalha as e:
        erro_falha = str(e)
    except ErroInstabilidade as e:
        erro_instabilidade = str(e)

    amostra = bronze[0].payload if bronze else None
    contrato = avaliar(
        canario_validado=canario_validado,
        resposta=[amostra] if amostra is not None else None,
        erro_falha=erro_falha, erro_instabilidade=erro_instabilidade,
        linha_base=linha_base, criticos=CAMPOS_CRITICOS_DISCURSO,
    )
    # Deputado sem discurso na janela é NORMAL (resposta vazia legítima), não
    # falha de contrato: não há canário aqui, então trata-se lista vazia como OK.
    if not bronze and erro_falha is None and erro_instabilidade is None:
        return ResultadoRodadaDiscursos(
            EstadoContrato.OK, "sem discursos na janela", bronze, ResultadoPortao())
    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaDiscursos(contrato.estado, contrato.detalhe, bronze)
    prata = processar_discursos_para_prata(bronze, deputado_id)
    return ResultadoRodadaDiscursos(contrato.estado, contrato.detalhe, bronze, prata)
