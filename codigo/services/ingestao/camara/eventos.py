"""Coletor da Câmara — eventos da agenda legislativa (Área nova, bicameral).

Fonte: https://dadosabertos.camara.leg.br/api/v2/eventos?dataInicio&dataFim
Sessões do plenário, reuniões e audiências de comissão. Verificado ao vivo
(2026-08-02). Produz a MESMA prata que `senado/eventos.py` (tabela `evento`,
`casa='camara'`).

`orgao_slug` reconstrói o slug do perfil da comissão (mesma fórmula de
`camara/coletivos.py`) para a persistência ligar `orgao_profile_id`; plenário e
órgãos não-ingeridos ficam sem perfil (null, honesto).
"""

from __future__ import annotations

import unicodedata
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

FONTE = "camara.eventos"
BASE = "https://dadosabertos.camara.leg.br/api/v2"

CAMPOS_CRITICOS_EVENTO = frozenset({"id", "dataHoraInicio", "situacao"})


def _proximo_link(corpo: Any) -> str | None:
    for link in (corpo or {}).get("links", []) or []:
        if link.get("rel") == "next" and link.get("href"):
            return link["href"]
    return None


def coletar_bronze_eventos(
    cliente: ClienteHttp,
    *,
    data_inicio: str,
    data_fim: str,
    politica: PoliticaRetry = PoliticaRetry(),
    itens_por_pagina: int = 100,
    limite_paginas: int = 50,
) -> list[RegistroBronze]:
    """Eventos na janela [data_inicio, data_fim] (YYYY-MM-DD)."""
    url = f"{BASE}/eventos"
    params: dict[str, Any] = {
        "dataInicio": data_inicio, "dataFim": data_fim,
        "itens": itens_por_pagina, "ordem": "ASC",
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


def _slug(prefixo: str, texto: str, id_fonte: str) -> str:
    base = unicodedata.normalize("NFKD", texto or "")
    base = base.encode("ascii", "ignore").decode("ascii").lower()
    limpo = "-".join(p for p in "".join(
        c if c.isalnum() else "-" for c in base).split("-") if p)
    corpo = f"{limpo}-{id_fonte}" if limpo else id_fonte
    return f"{prefixo}-{corpo}"


def _texto(v: Any) -> str | None:
    if v is None:
        return None
    t = str(v).replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    t = " ".join(t.split())
    return t or None


def transformar_evento(payload: dict) -> dict:
    orgaos = payload.get("orgaos") or []
    org = orgaos[0] if orgaos else {}
    loc = payload.get("localCamara") or {}
    sigla = org.get("sigla")
    org_id = org.get("id")
    return {
        "casa": "camara",
        "id_fonte": str(payload.get("id") or "") or None,
        "tipo": payload.get("descricaoTipo"),
        "titulo": _texto(payload.get("descricao")),
        "data_hora_inicio": payload.get("dataHoraInicio"),
        "data_hora_fim": payload.get("dataHoraFim"),
        "situacao": payload.get("situacao"),
        "orgao_sigla": sigla,
        "orgao_nome": org.get("nome"),
        "orgao_slug": (_slug("comissao", sigla, str(org_id))
                       if sigla and org_id else None),
        "local": loc.get("nome") or payload.get("localExterno"),
        "url": payload.get("urlRegistro") or payload.get("uri"),
    }


VERIFICADORES_EVENTO = [
    campo_obrigatorio("id_fonte"),
    campo_obrigatorio("data_hora_inicio"),
]


def processar_eventos_para_prata(bronze: list[RegistroBronze]) -> ResultadoPortao:
    return portao_bronze_prata(
        bronze, transformar=transformar_evento, verificadores=VERIFICADORES_EVENTO)


@dataclass
class ResultadoRodadaEventos:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    prata: ResultadoPortao | None = None


def rodada_eventos(
    cliente: ClienteHttp, *,
    data_inicio: str, data_fim: str,
    canario_validado: bool, linha_base: frozenset[str] | None,
    politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodadaEventos:
    erro_falha = erro_instabilidade = None
    bronze: list[RegistroBronze] = []
    try:
        bronze = coletar_bronze_eventos(
            cliente, data_inicio=data_inicio, data_fim=data_fim, politica=politica)
    except ErroFalha as e:
        erro_falha = str(e)
    except ErroInstabilidade as e:
        erro_instabilidade = str(e)

    amostra = bronze[0].payload if bronze else None
    contrato = avaliar(
        canario_validado=canario_validado,
        resposta=[amostra] if amostra is not None else None,
        erro_falha=erro_falha, erro_instabilidade=erro_instabilidade,
        linha_base=linha_base, criticos=CAMPOS_CRITICOS_EVENTO,
    )
    if not bronze and erro_falha is None and erro_instabilidade is None:
        return ResultadoRodadaEventos(
            EstadoContrato.OK, "sem eventos na janela", bronze, ResultadoPortao())
    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaEventos(contrato.estado, contrato.detalhe, bronze)
    prata = processar_eventos_para_prata(bronze)
    return ResultadoRodadaEventos(contrato.estado, contrato.detalhe, bronze, prata)
