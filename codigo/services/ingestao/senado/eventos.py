"""Coletor do Senado — agenda de reuniões de comissão (Área nova, bicameral).

Fonte: https://legis.senado.leg.br/dadosabertos/comissao/agenda/mes/{YYYYMM}
Agenda das reuniões das comissões no mês. Verificado ao vivo (2026-08-02).
Produz a MESMA prata que `camara/eventos.py` (tabela `evento`, `casa='senado'`).

Estrutura: `AgendaReuniao.reunioes.reuniao[]` — codigo, titulo, dataInicio,
situacao, local, colegiadoCriador{codigo,sigla,nome}. O `orgao_slug` reconstrói
o slug do perfil da comissão do Senado (prefixo `comissao-sf`, de
`senado/coletivos.py`) para a persistência ligar `orgao_profile_id`.
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

FONTE = "senado.eventos"
BASE = "https://legis.senado.leg.br/dadosabertos"

CAMPOS_CRITICOS_EVENTO_SENADO = frozenset({"codigo", "dataInicio", "titulo"})


def _como_lista(v: Any) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


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


def _aaaammm(iso: str) -> str:
    """YYYY-MM (ou já YYYYMM) → YYYYMM, o formato do path /agenda/mes/{}."""
    return str(iso).replace("-", "")[:6]


def coletar_bronze_eventos_senado(
    cliente: ClienteHttp, mes: str, *, politica: PoliticaRetry = PoliticaRetry(),
) -> list[RegistroBronze]:
    """Reuniões de comissão do mês `mes` (YYYYMM). A fonte devolve o mês inteiro
    numa resposta."""
    url = f"{BASE}/comissao/agenda/mes/{_aaaammm(mes)}"
    corpo = obter_com_retry(cliente, url, politica=politica)
    ag = (corpo or {}).get("AgendaReuniao") or {}
    reunioes = (ag.get("reunioes") or {})
    return [RegistroBronze.de(FONTE, url, r)
            for r in _como_lista(reunioes.get("reuniao"))]


def transformar_evento_senado(payload: dict) -> dict:
    col = payload.get("colegiadoCriador") or {}
    sigla = col.get("sigla")
    codigo = col.get("codigo")
    return {
        "casa": "senado",
        "id_fonte": str(payload.get("codigo") or "") or None,
        "tipo": col.get("descricaoTipo") or "Reunião de Comissão",
        "titulo": _texto(payload.get("titulo") or payload.get("descricao")),
        "data_hora_inicio": payload.get("dataInicio"),
        "data_hora_fim": None,   # a agenda não traz fim
        "situacao": payload.get("situacao"),
        "orgao_sigla": sigla,
        "orgao_nome": col.get("nome"),
        "orgao_slug": (_slug("comissao-sf", sigla, str(codigo))
                       if sigla and codigo else None),
        "local": _texto(payload.get("local")),
        "url": None,
    }


VERIFICADORES_EVENTO_SENADO = [
    campo_obrigatorio("id_fonte"),
    campo_obrigatorio("data_hora_inicio"),
]


def processar_eventos_senado_para_prata(bronze: list[RegistroBronze]) -> ResultadoPortao:
    return portao_bronze_prata(
        bronze, transformar=transformar_evento_senado,
        verificadores=VERIFICADORES_EVENTO_SENADO)


@dataclass
class ResultadoRodadaEventosSenado:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    prata: ResultadoPortao | None = None


def rodada_eventos_senado(
    cliente: ClienteHttp, mes: str, *,
    canario_validado: bool, linha_base: frozenset[str] | None,
    politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodadaEventosSenado:
    erro_falha = erro_instabilidade = None
    bronze: list[RegistroBronze] = []
    try:
        bronze = coletar_bronze_eventos_senado(cliente, mes, politica=politica)
    except ErroFalha as e:
        erro_falha = str(e)
    except ErroInstabilidade as e:
        erro_instabilidade = str(e)

    amostra = bronze[0].payload if bronze else None
    contrato = avaliar(
        canario_validado=canario_validado,
        resposta=[amostra] if amostra is not None else None,
        erro_falha=erro_falha, erro_instabilidade=erro_instabilidade,
        linha_base=linha_base, criticos=CAMPOS_CRITICOS_EVENTO_SENADO,
    )
    if not bronze and erro_falha is None and erro_instabilidade is None:
        return ResultadoRodadaEventosSenado(
            EstadoContrato.OK, "sem reuniões no mês", bronze, ResultadoPortao())
    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaEventosSenado(contrato.estado, contrato.detalhe, bronze)
    prata = processar_eventos_senado_para_prata(bronze)
    return ResultadoRodadaEventosSenado(contrato.estado, contrato.detalhe, bronze, prata)
