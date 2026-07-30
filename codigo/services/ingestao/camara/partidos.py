"""Coletor da Câmara — partidos canônicos (§4).

Fonte:
    https://dadosabertos.camara.leg.br/api/v2/partidos          (lista)
    https://dadosabertos.camara.leg.br/api/v2/partidos/{id}     (detalhe)

O partido é, no modelo, também um `profile` (tipo='partido') — para ser
seguível e para dar alvo estável ao `vinculo_temporal`, que resolve o partido
de uma pessoa NA DATA DO FATO. Este coletor cria o partido canônico; o vínculo
temporal (em `mandatos.py`) prende-se a ele por sigla.

FRONTEIRA DE CURADORIA (§4). Este coletor ingere os partidos ATUAIS que a API
publica — a parte mecânica. A Metodologia é explícita: "a fonte preserva o
identificador no renome, mas apaga as origens nas fusões, e a linhagem é
reconstruída por curadoria". Portanto:

  - Siglas HISTÓRICAS (PMDB→MDB, DEM/PSL→UNIÃO) e a LINHAGEM de fusões/renomes
    (tabelas `partido_sigla_historico` e `partido_linhagem`) exigem uma fonte de
    curadoria que NÃO vem desta API — ficam para etapa própria.
  - Em consequência, o `vinculo_temporal` resolve `partido_id` quando a
    `partido_sigla_fonte` casa com uma sigla ATUAL; siglas históricas ficam com
    `partido_id` nulo e `partido_sigla_fonte` preservado (a verdade da fonte).
    Dado ausente é melhor que dado errado (§1).
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

FONTE = "camara.partidos"
BASE = "https://dadosabertos.camara.leg.br/api/v2"

# Campos críticos da lista. Verificado ao vivo (2026-07-29): presentes.
CAMPOS_CRITICOS_PARTIDO = frozenset({"id", "sigla", "nome"})


# -----------------------------------------------------------------------------
# Coleta — bronze
# -----------------------------------------------------------------------------

def coletar_bronze_partidos(
    cliente: ClienteHttp,
    *,
    politica: PoliticaRetry = PoliticaRetry(),
    itens_por_pagina: int = 100,
    limite_paginas: int = 50,
) -> list[RegistroBronze]:
    """Lista de partidos. Sem filtro, a API devolve os ativos na legislatura
    corrente — os que interessam para resolver a maioria dos vínculos recentes."""
    url = f"{BASE}/partidos"
    params: dict[str, Any] = {"itens": itens_por_pagina, "ordem": "ASC",
                              "ordenarPor": "sigla"}
    bronze: list[RegistroBronze] = []
    pagina = 1
    proximo: str | None = None
    while pagina <= limite_paginas:
        corpo = obter_com_retry(
            cliente, proximo or url,
            params=None if proximo else params, politica=politica,
        )
        for item in (corpo or {}).get("dados", []):
            bronze.append(RegistroBronze.de(FONTE, url, item))
        proximo = _proximo_link(corpo)
        if proximo is None:
            break
        pagina += 1
    return bronze


def coletar_bronze_partido_detalhe(
    cliente: ClienteHttp, partido_id_fonte: str,
    *, politica: PoliticaRetry = PoliticaRetry(),
) -> RegistroBronze:
    """Detalhe de UM partido (numeroEleitoral, status/situação)."""
    url = f"{BASE}/partidos/{partido_id_fonte}"
    corpo = obter_com_retry(cliente, url, politica=politica)
    return RegistroBronze.de(FONTE, url, (corpo or {}).get("dados") or {})


def _proximo_link(corpo: Any) -> str | None:
    for link in (corpo or {}).get("links", []) or []:
        if link.get("rel") == "next" and link.get("href"):
            return link["href"]
    return None


# -----------------------------------------------------------------------------
# Transformação — bronze → prata (profile tipo=partido + partido)
# -----------------------------------------------------------------------------

def _slug(sigla: str, id_fonte: str) -> str:
    base = unicodedata.normalize("NFKD", sigla or "")
    base = base.encode("ascii", "ignore").decode("ascii").lower()
    limpo = "-".join(p for p in "".join(
        c if c.isalnum() else "-" for c in base).split("-") if p)
    return f"partido-{limpo}-{id_fonte}" if limpo else f"partido-{id_fonte}"


def _int(v: Any) -> int | None:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def transformar_partido(payload: dict, detalhe: dict | None = None) -> dict:
    id_fonte = str(payload["id"])
    sigla = payload.get("sigla")
    nome = payload.get("nome")
    d = detalhe or {}
    situacao = (d.get("status") or {}).get("situacao")
    return {
        "id_fonte": id_fonte,
        "tipo": "partido",
        "sigla": sigla,
        "nome": nome,
        "slug": _slug(sigla, id_fonte) if sigla else None,
        "numero_urna": _int(d.get("numeroEleitoral")),
        # Situação ausente (sem detalhe) → assume ativo; só marca inativo quando
        # a fonte disser explicitamente.
        "ativo": not (isinstance(situacao, str) and situacao.lower().startswith("inativ")),
    }


VERIFICADORES_PARTIDO = [
    campo_obrigatorio("id_fonte"),
    campo_obrigatorio("sigla"),
    campo_obrigatorio("nome"),
    campo_obrigatorio("slug"),
]


def processar_partidos_para_prata(
    bronze: list[RegistroBronze], detalhes: dict[str, dict] | None = None,
) -> ResultadoPortao:
    det = detalhes or {}

    def _transformar(item: dict) -> dict:
        return transformar_partido(item, det.get(str(item.get("id"))))

    return portao_bronze_prata(
        bronze, transformar=_transformar, verificadores=VERIFICADORES_PARTIDO,
    )


# -----------------------------------------------------------------------------
# Rodada
# -----------------------------------------------------------------------------

@dataclass
class ResultadoRodadaPartidos:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    prata: ResultadoPortao | None = None
    detalhes_bronze: list[RegistroBronze] | None = None


def rodada_partidos(
    cliente: ClienteHttp,
    *,
    canario_validado: bool,
    linha_base: frozenset[str] | None,
    enriquecer: bool = True,
    politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodadaPartidos:
    erro_falha: str | None = None
    erro_instabilidade: str | None = None
    bronze: list[RegistroBronze] = []

    try:
        bronze = coletar_bronze_partidos(cliente, politica=politica)
    except ErroFalha as e:
        erro_falha = str(e)
    except ErroInstabilidade as e:
        erro_instabilidade = str(e)

    amostra = bronze[0].payload if bronze else None
    contrato = avaliar(
        canario_validado=canario_validado,
        resposta=[amostra] if amostra is not None else None,
        erro_falha=erro_falha, erro_instabilidade=erro_instabilidade,
        linha_base=linha_base, criticos=CAMPOS_CRITICOS_PARTIDO,
    )

    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaPartidos(
            estado=contrato.estado, detalhe=contrato.detalhe, bronze=bronze,
        )

    detalhes: dict[str, dict] = {}
    detalhes_bronze: list[RegistroBronze] = []
    if enriquecer:
        for reg in bronze:
            pid = str(reg.payload.get("id"))
            try:
                d = coletar_bronze_partido_detalhe(cliente, pid, politica=politica)
                detalhes[pid] = d.payload
                detalhes_bronze.append(d)
            except (ErroFalha, ErroInstabilidade):
                continue

    prata = processar_partidos_para_prata(bronze, detalhes)
    return ResultadoRodadaPartidos(
        estado=contrato.estado, detalhe=contrato.detalhe,
        bronze=bronze, prata=prata, detalhes_bronze=detalhes_bronze,
    )
