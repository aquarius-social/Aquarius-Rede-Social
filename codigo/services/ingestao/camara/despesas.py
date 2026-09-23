"""Coletor da Câmara — despesas da Cota Parlamentar (CEAP), Área A (§8).

Fonte: `https://dadosabertos.camara.leg.br/api/v2/deputados/{id}/despesas?ano=Y`.
Cada linha é um documento de ressarcimento de um parlamentar. Dado público de
transparência — a fonte publica fornecedor e valor abertamente; não há PII do
parlamentar aqui.

IDENTIDADE INTERNA (§5.2), verificada ao vivo: valor do documento menos a glosa
é igual ao líquido. É verificável linha a linha, sem fonte externa — o portão a
aplica e quarentena quem viola. "Verificação que sempre passa é indistinguível
de verificação desligada": o teste tem um caso que aceita e um que recusa.

VOLUME (§8): a CEAP é volumosa (milhares de linhas por parlamentar por ano). O
coletor é POR parlamentar e POR ano; o orquestrador decide a janela. `cod_documento`
= 0 na fonte significa "sem documento" e é gravado como None (não colide na
unicidade).
"""

from __future__ import annotations

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

FONTE = "camara.despesas"
BASE = "https://dadosabertos.camara.leg.br/api/v2"

CAMPOS_CRITICOS_DESPESA = frozenset({
    "ano", "mes", "tipoDespesa", "valorLiquido"
})


# -----------------------------------------------------------------------------
# Coleta — bronze
# -----------------------------------------------------------------------------

def coletar_bronze_despesas(
    cliente: ClienteHttp,
    deputado_id_fonte: str,
    *,
    ano: int,
    id_legislatura: int | None = None,
    politica: PoliticaRetry = PoliticaRetry(),
    itens_por_pagina: int = 100,
    limite_paginas: int = 200,
) -> list[RegistroBronze]:
    """Despesas de UM parlamentar num ano. Paginado."""
    url = f"{BASE}/deputados/{deputado_id_fonte}/despesas"
    params: dict[str, Any] = {"ano": ano, "itens": itens_por_pagina,
                              "ordem": "DESC", "ordenarPor": "dataDocumento"}
    # A API passou a EXIGIR idLegislatura: sem ele o endpoint devolve 200 com lista
    # VAZIA (sucesso enganoso, §21 modo 1) — verificado ao vivo 2026-09. Com ele,
    # despesas (inclusive históricas) voltam normalmente.
    if id_legislatura is not None:
        params["idLegislatura"] = id_legislatura
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


def _proximo_link(corpo: Any) -> str | None:
    for link in (corpo or {}).get("links", []) or []:
        if link.get("rel") == "next" and link.get("href"):
            return link["href"]
    return None


# -----------------------------------------------------------------------------
# Transformação
# -----------------------------------------------------------------------------

def _int(v: Any) -> int | None:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _num(v: Any) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def transformar_despesa(payload: dict, deputado_id_fonte: str) -> dict:
    cod = _int(payload.get("codDocumento"))
    return {
        "deputado_id_fonte": str(deputado_id_fonte),
        "ano": _int(payload.get("ano")),
        "mes": _int(payload.get("mes")),
        "tipo_despesa": payload.get("tipoDespesa"),
        "tipo_documento": payload.get("tipoDocumento"),
        "cod_documento": cod or None,   # 0 = sem documento → None
        "cod_lote": _int(payload.get("codLote")),
        "num_documento": payload.get("numDocumento"),
        "num_ressarcimento": payload.get("numRessarcimento"),
        "parcela": _int(payload.get("parcela")),
        "data_documento": payload.get("dataDocumento") or None,
        "valor_documento": _num(payload.get("valorDocumento")),
        "valor_glosa": _num(payload.get("valorGlosa")),
        "valor_liquido": _num(payload.get("valorLiquido")),
        "fornecedor_nome": payload.get("nomeFornecedor"),
        "fornecedor_cnpj_cpf": payload.get("cnpjCpfFornecedor"),
        "url_documento": payload.get("urlDocumento"),
    }


def _identidade_valor(registro: dict) -> Violacao | None:
    """§5.2: documento - glosa = líquido. None quando algum valor falta (não dá
    para checar). Comparação arredondada a 2 casas (a fonte entrega float)."""
    doc = registro.get("valor_documento")
    glosa = registro.get("valor_glosa")
    liq = registro.get("valor_liquido")
    if doc is None or glosa is None or liq is None:
        return None
    if round(doc - glosa, 2) != round(liq, 2):
        return Violacao(
            "precisao",
            f"identidade violada: documento {doc} - glosa {glosa} ≠ líquido {liq}")
    return None


# NB: valor NEGATIVO é legítimo — é ESTORNO (reembolso de despesa anterior, ex.:
# "PASSAGEM AÉREA - SIGEPA" cancelada). Descoberto contra a fonte viva: 4 de 100
# linhas eram estornos, e todas satisfazem a identidade (doc - glosa = líquido).
# Não se recusa por sinal; a identidade aritmética é a verificação que importa.

VERIFICADORES_DESPESA = [
    campo_obrigatorio("ano"),
    campo_obrigatorio("mes"),
    _identidade_valor,
]


def processar_despesas_para_prata(
    bronze: list[RegistroBronze], deputado_id_fonte: str,
) -> ResultadoPortao:
    def _transformar(payload: dict) -> dict:
        return transformar_despesa(payload, deputado_id_fonte)

    return portao_bronze_prata(
        bronze, transformar=_transformar, verificadores=VERIFICADORES_DESPESA)


# -----------------------------------------------------------------------------
# Rodada — por parlamentar
# -----------------------------------------------------------------------------

@dataclass
class ResultadoRodadaDespesas:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    prata: ResultadoPortao | None = None


def rodada_despesas(
    cliente: ClienteHttp,
    deputado_id_fonte: str,
    *,
    ano: int,
    id_legislatura: int | None = None,
    canario_validado: bool,
    linha_base: frozenset[str] | None,
    politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodadaDespesas:
    erro_falha = erro_instabilidade = None
    bronze: list[RegistroBronze] = []
    try:
        bronze = coletar_bronze_despesas(cliente, deputado_id_fonte, ano=ano,
                                         id_legislatura=id_legislatura,
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
        linha_base=linha_base, criticos=CAMPOS_CRITICOS_DESPESA)

    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaDespesas(contrato.estado, contrato.detalhe, bronze)

    prata = processar_despesas_para_prata(bronze, deputado_id_fonte)
    return ResultadoRodadaDespesas(contrato.estado, contrato.detalhe, bronze, prata)
