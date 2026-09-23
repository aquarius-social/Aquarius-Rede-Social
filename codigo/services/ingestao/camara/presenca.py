"""Coletor da Câmara — presença em sessões do Plenário (Área E, §11/§4).

Fontes (verificadas ao vivo 2026-09-22):
    /eventos?codTipoEvento=110&codTipoEvento=204   → sessões deliberativas
    /eventos/{id}/deputados                        → PRESENTES na sessão

`codTipoEvento` 110 e 204 = "Sessão Deliberativa". Filtra-se `orgao='PLEN'`
(plenário) — reunião de comissão também é evento, mas não é a presença-frequência
que o produto mostra. A lista de deputados de uma sessão do plenário varia (465..
489 de 513) → é presença REAL. AUSENTE = fora da lista.

A tramitação de identidade é a mesma dos votos: a lista traz o `id` do deputado
na Câmara; o perfil (a PESSOA) resolve-se por id_externo no momento de salvar
(`salvar_presencas`), na data da sessão (§4). Deputado não resolvido → quarentena
por integridade referencial, nunca perfil fantasma.

Duas etapas separadas (como votações): a LISTA de sessões é barata; a presença de
cada uma é uma requisição por sessão. Separar deixa o contrato rodar sobre a
lista antes das chamadas por-sessão.
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

FONTE_SESSAO = "camara.sessoes"
FONTE_PRESENCA = "camara.presenca"
BASE = "https://dadosabertos.camara.leg.br/api/v2"

# "Sessão Deliberativa" (verificado em /referencias/tiposEvento, 2026-09-22).
CODS_SESSAO_DELIBERATIVA = ("110", "204")
ORGAO_PLENARIO = "PLEN"

# Campos críticos. Verificados ao vivo (2026-09-22).
CAMPOS_CRITICOS_SESSAO = frozenset({"id", "dataHoraInicio", "descricaoTipo"})
CAMPOS_CRITICOS_PRESENCA = frozenset({"id"})   # id do deputado na Câmara


def _proximo_link(corpo: Any) -> str | None:
    for link in (corpo or {}).get("links", []) or []:
        if link.get("rel") == "next" and link.get("href"):
            return link["href"]
    return None


def _orgao_sigla(payload: dict) -> str | None:
    orgaos = payload.get("orgaos") or []
    return orgaos[0].get("sigla") if orgaos else None


# -----------------------------------------------------------------------------
# Coleta — bronze
# -----------------------------------------------------------------------------

def coletar_bronze_sessoes(
    cliente: ClienteHttp,
    *,
    data_inicio: str,
    data_fim: str,
    politica: PoliticaRetry = PoliticaRetry(),
    itens_por_pagina: int = 100,
    limite_paginas: int = 50,
) -> list[RegistroBronze]:
    """Sessões deliberativas do Plenário na janela [data_inicio, data_fim].

    Só as do PLENÁRIO entram (`orgao='PLEN'`); reuniões de comissão são evento,
    não presença-frequência. Uma sessão = um bronze (o payload do evento).

    Uma chamada POR código de tipo (110 e 204): o cliente HTTP compartilhado não
    codifica parâmetro multivalorado (`urlencode` sem `doseq`), então evita-se a
    lista na querystring; cada sessão tem UM tipo, então basta juntar (dedup por
    id por garantia)."""
    url = f"{BASE}/eventos"
    bronze: list[RegistroBronze] = []
    vistos: set[str] = set()
    for cod in CODS_SESSAO_DELIBERATIVA:
        params: dict[str, Any] = {
            "dataInicio": data_inicio,
            "dataFim": data_fim,
            "codTipoEvento": cod,
            "itens": itens_por_pagina,
            "ordem": "ASC",
            "ordenarPor": "dataHoraInicio",
        }
        pagina = 1
        proximo: str | None = None
        while pagina <= limite_paginas:
            corpo = obter_com_retry(
                cliente, proximo or url,
                params=None if proximo else params, politica=politica)
            for item in (corpo or {}).get("dados", []):
                idf = str(item.get("id"))
                if _orgao_sigla(item) == ORGAO_PLENARIO and idf not in vistos:
                    vistos.add(idf)
                    bronze.append(RegistroBronze.de(FONTE_SESSAO, url, item))
            proximo = _proximo_link(corpo)
            if proximo is None:
                break
            pagina += 1
    return bronze


def coletar_bronze_presencas(
    cliente: ClienteHttp,
    sessao_id_fonte: str,
    *,
    politica: PoliticaRetry = PoliticaRetry(),
) -> list[RegistroBronze]:
    """Deputados PRESENTES numa sessão. Um bronze por deputado presente."""
    url = f"{BASE}/eventos/{sessao_id_fonte}/deputados"
    corpo = obter_com_retry(cliente, url, politica=politica)
    return [
        RegistroBronze.de(FONTE_PRESENCA, url, item)
        for item in (corpo or {}).get("dados", [])
    ]


# -----------------------------------------------------------------------------
# Transformação — bronze → prata
# -----------------------------------------------------------------------------

def transformar_sessao(payload: dict) -> dict:
    return {
        "id_fonte": str(payload.get("id") or "") or None,
        "casa": "camara",
        "tipo": payload.get("descricaoTipo"),
        "data_hora": payload.get("dataHoraInicio"),
        "orgao_sigla": _orgao_sigla(payload),
    }


def transformar_presenca(payload: dict, sessao_id_fonte: str) -> dict:
    id_dep = payload.get("id")
    return {
        "sessao_id_fonte": str(sessao_id_fonte),
        "casa": "camara",
        # id do parlamentar na fonte (casa-neutro): resolve o perfil no save.
        "id_parlamentar": str(id_dep) if id_dep is not None else None,
        "presente": True,
    }


VERIFICADORES_SESSAO = [
    campo_obrigatorio("id_fonte"),
    campo_obrigatorio("data_hora"),
]


def _id_parlamentar_presente(registro: dict) -> Violacao | None:
    if not registro.get("id_parlamentar"):
        return Violacao("integridade_referencial",
                        "presença sem id de parlamentar — não é resolvível")
    return None


VERIFICADORES_PRESENCA = [_id_parlamentar_presente]


def processar_sessoes_para_prata(bronze: list[RegistroBronze]) -> ResultadoPortao:
    return portao_bronze_prata(
        bronze, transformar=transformar_sessao, verificadores=VERIFICADORES_SESSAO)


def processar_presencas_para_prata(
    bronze: list[RegistroBronze], sessao_id_fonte: str,
) -> ResultadoPortao:
    def _transformar(payload: dict) -> dict:
        return transformar_presenca(payload, sessao_id_fonte)
    return portao_bronze_prata(
        bronze, transformar=_transformar, verificadores=VERIFICADORES_PRESENCA)


# -----------------------------------------------------------------------------
# Rodadas com teste de contrato
# -----------------------------------------------------------------------------

@dataclass
class ResultadoRodadaSessoes:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    prata: ResultadoPortao | None = None


def rodada_sessoes(
    cliente: ClienteHttp,
    *,
    data_inicio: str,
    data_fim: str,
    canario_validado: bool,
    linha_base: frozenset[str] | None,
    politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodadaSessoes:
    erro_falha: str | None = None
    erro_instabilidade: str | None = None
    bronze: list[RegistroBronze] = []
    try:
        bronze = coletar_bronze_sessoes(
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
        linha_base=linha_base, criticos=CAMPOS_CRITICOS_SESSAO)
    # Janela sem sessão (recesso) é vazio legítimo, não FALHA.
    if not bronze and erro_falha is None and erro_instabilidade is None:
        return ResultadoRodadaSessoes(
            EstadoContrato.OK, "sem sessões na janela", bronze, ResultadoPortao())
    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaSessoes(contrato.estado, contrato.detalhe, bronze)
    prata = processar_sessoes_para_prata(bronze)
    return ResultadoRodadaSessoes(contrato.estado, contrato.detalhe, bronze, prata)


@dataclass
class ResultadoRodadaPresencas:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    prata: ResultadoPortao | None = None


def rodada_presencas(
    cliente: ClienteHttp,
    sessao_id_fonte: str,
    *,
    canario_validado: bool,
    linha_base: frozenset[str] | None,
    politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodadaPresencas:
    erro_falha: str | None = None
    erro_instabilidade: str | None = None
    bronze: list[RegistroBronze] = []
    try:
        bronze = coletar_bronze_presencas(cliente, sessao_id_fonte, politica=politica)
    except ErroFalha as e:
        erro_falha = str(e)
    except ErroInstabilidade as e:
        erro_instabilidade = str(e)

    amostra = bronze[0].payload if bronze else None
    contrato = avaliar(
        canario_validado=canario_validado,
        resposta=[amostra] if amostra is not None else None,
        erro_falha=erro_falha, erro_instabilidade=erro_instabilidade,
        linha_base=linha_base, criticos=CAMPOS_CRITICOS_PRESENCA)
    # Sessão sem lista de presença publicada é vazio legítimo, não FALHA.
    if not bronze and erro_falha is None and erro_instabilidade is None:
        return ResultadoRodadaPresencas(
            EstadoContrato.OK, "sem presença publicada", bronze, ResultadoPortao())
    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaPresencas(contrato.estado, contrato.detalhe, bronze)
    prata = processar_presencas_para_prata(bronze, sessao_id_fonte)
    return ResultadoRodadaPresencas(contrato.estado, contrato.detalhe, bronze, prata)
