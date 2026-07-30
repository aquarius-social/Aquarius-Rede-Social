"""Coletor da Câmara — perfis coletivos: comissões e frentes (§12, Concepção §7).

Comissões e frentes são o MESMO objeto que parlamentar e partido — perfis
polimórficos seguíveis (tabela `profiles`, campo `tipo`). A Concepção: "Partidos,
comissões e frentes são o mesmo objeto, com o conjunto de abas próprio de cada
um". Este coletor popula os tipos `comissao` e `frente`.

Fontes (verificado ao vivo, 2026-07-29):
    /orgaos?codTipoOrgao=2   → comissões PERMANENTES. codTipoOrgao=2 é
                               'Comissão Permanente' (ex.: CCJC=id 2003). A lista
                               NÃO traz o tipo em texto (§12), então filtramos
                               pelo código verificado, sem chutar.
    /frentes                 → frentes parlamentares da legislatura corrente.

ESCOPO deste passe: comissões PERMANENTES (as que têm tela própria e maior peso)
e as frentes. Outros tipos de órgão (especiais, MPV, subcomissões) e o
enriquecimento de composição/membros são etapas próprias (§12 D5).

Como no partido, NÃO usamos `id_externo` aqui: o vínculo relevante (tramitação →
comissão) é por SIGLA, e pôr o id do órgão sob sistema='camara' arriscaria colidir
com id de deputado. A resolução por sigla é enriquecimento posterior.
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

BASE = "https://dadosabertos.camara.leg.br/api/v2"
FONTE_COMISSOES = "camara.orgaos"
FONTE_FRENTES = "camara.frentes"

COD_COMISSAO_PERMANENTE = 2  # verificado ao vivo (tipoOrgao='Comissão Permanente')

CAMPOS_CRITICOS_COMISSAO = frozenset({"id", "sigla", "nome"})
CAMPOS_CRITICOS_FRENTE = frozenset({"id", "titulo"})


def _slug(prefixo: str, texto: str, id_fonte: str) -> str:
    base = unicodedata.normalize("NFKD", texto or "")
    base = base.encode("ascii", "ignore").decode("ascii").lower()
    limpo = "-".join(p for p in "".join(
        c if c.isalnum() else "-" for c in base).split("-") if p)
    corpo = f"{limpo}-{id_fonte}" if limpo else id_fonte
    return f"{prefixo}-{corpo}"


def _proximo_link(corpo: Any) -> str | None:
    for link in (corpo or {}).get("links", []) or []:
        if link.get("rel") == "next" and link.get("href"):
            return link["href"]
    return None


def _coletar_paginado(
    cliente: ClienteHttp, url: str, params: dict[str, Any], fonte: str,
    politica: PoliticaRetry, limite_paginas: int,
) -> list[RegistroBronze]:
    bronze: list[RegistroBronze] = []
    pagina = 1
    proximo: str | None = None
    while pagina <= limite_paginas:
        corpo = obter_com_retry(
            cliente, proximo or url,
            params=None if proximo else params, politica=politica,
        )
        for item in (corpo or {}).get("dados", []):
            bronze.append(RegistroBronze.de(fonte, url, item))
        proximo = _proximo_link(corpo)
        if proximo is None:
            break
        pagina += 1
    return bronze


# -----------------------------------------------------------------------------
# Comissões (permanentes)
# -----------------------------------------------------------------------------

def coletar_bronze_comissoes(
    cliente: ClienteHttp, *, politica: PoliticaRetry = PoliticaRetry(),
    itens_por_pagina: int = 100, limite_paginas: int = 20,
) -> list[RegistroBronze]:
    return _coletar_paginado(
        cliente, f"{BASE}/orgaos",
        {"codTipoOrgao": COD_COMISSAO_PERMANENTE, "itens": itens_por_pagina,
         "ordem": "ASC", "ordenarPor": "sigla"},
        FONTE_COMISSOES, politica, limite_paginas,
    )


def transformar_comissao(payload: dict) -> dict:
    id_fonte = str(payload["id"])
    sigla = payload.get("sigla")
    nome = payload.get("nome")
    return {
        "id_fonte": id_fonte,
        "tipo": "comissao",
        "nome": nome,
        "sigla": sigla,
        "slug": _slug("comissao", sigla or nome, id_fonte) if (sigla or nome) else None,
        "ativo": True,
    }


VERIFICADORES_COMISSAO = [
    campo_obrigatorio("id_fonte"),
    campo_obrigatorio("nome"),
    campo_obrigatorio("sigla"),
    campo_obrigatorio("slug"),
]


def processar_comissoes_para_prata(bronze: list[RegistroBronze]) -> ResultadoPortao:
    return portao_bronze_prata(
        bronze, transformar=transformar_comissao, verificadores=VERIFICADORES_COMISSAO)


# -----------------------------------------------------------------------------
# Frentes
# -----------------------------------------------------------------------------

def coletar_bronze_frentes(
    cliente: ClienteHttp, *, id_legislatura: int | None = None,
    politica: PoliticaRetry = PoliticaRetry(),
    itens_por_pagina: int = 100, limite_paginas: int = 50,
) -> list[RegistroBronze]:
    params: dict[str, Any] = {"itens": itens_por_pagina}
    if id_legislatura is not None:
        params["idLegislatura"] = id_legislatura
    return _coletar_paginado(
        cliente, f"{BASE}/frentes", params, FONTE_FRENTES, politica, limite_paginas)


def transformar_frente(payload: dict) -> dict:
    id_fonte = str(payload["id"])
    titulo = payload.get("titulo")
    return {
        "id_fonte": id_fonte,
        "tipo": "frente",
        "nome": titulo,
        "sigla": None,  # frentes não têm sigla estável
        "slug": _slug("frente", titulo or "", id_fonte) if titulo else None,
        "ativo": True,
    }


VERIFICADORES_FRENTE = [
    campo_obrigatorio("id_fonte"),
    campo_obrigatorio("nome"),
    campo_obrigatorio("slug"),
]


def processar_frentes_para_prata(bronze: list[RegistroBronze]) -> ResultadoPortao:
    return portao_bronze_prata(
        bronze, transformar=transformar_frente, verificadores=VERIFICADORES_FRENTE)


# -----------------------------------------------------------------------------
# Rodadas
# -----------------------------------------------------------------------------

@dataclass
class ResultadoRodadaColetivos:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    prata: ResultadoPortao | None = None


def _rodada(
    cliente, coletar, processar, criticos, *,
    canario_validado, linha_base, politica,
) -> ResultadoRodadaColetivos:
    erro_falha = erro_instabilidade = None
    bronze: list[RegistroBronze] = []
    try:
        bronze = coletar(cliente, politica=politica)
    except ErroFalha as e:
        erro_falha = str(e)
    except ErroInstabilidade as e:
        erro_instabilidade = str(e)

    amostra = bronze[0].payload if bronze else None
    contrato = avaliar(
        canario_validado=canario_validado,
        resposta=[amostra] if amostra is not None else None,
        erro_falha=erro_falha, erro_instabilidade=erro_instabilidade,
        linha_base=linha_base, criticos=criticos,
    )
    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaColetivos(contrato.estado, contrato.detalhe, bronze)
    prata = processar(bronze)
    return ResultadoRodadaColetivos(contrato.estado, contrato.detalhe, bronze, prata)


def rodada_comissoes(cliente, *, canario_validado, linha_base,
                     politica: PoliticaRetry = PoliticaRetry()):
    return _rodada(cliente, coletar_bronze_comissoes, processar_comissoes_para_prata,
                   CAMPOS_CRITICOS_COMISSAO, canario_validado=canario_validado,
                   linha_base=linha_base, politica=politica)


def rodada_frentes(cliente, *, canario_validado, linha_base,
                   politica: PoliticaRetry = PoliticaRetry()):
    return _rodada(cliente, coletar_bronze_frentes, processar_frentes_para_prata,
                   CAMPOS_CRITICOS_FRENTE, canario_validado=canario_validado,
                   linha_base=linha_base, politica=politica)
