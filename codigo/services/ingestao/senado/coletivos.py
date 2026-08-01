"""Coletor do Senado — perfis coletivos: comissões + blocos (bicameral).

Fontes (redirecionam 301 → JSON estático; urllib segue):
    /comissao/lista/colegiados   → ListaColegiados.Colegiados.Colegiado[]
    /composicao/lista/blocos     → ListaBlocoParlamentar.Blocos.Bloco[]
Verificado ao vivo em 2026-08-01 (222 colegiados; 6 blocos).

Popula a tabela polimórfica `profiles` nos tipos `comissao` e `bloco` — os dois
que faltavam dos seis tipos (parlamentar/partido/comissão/frente já vinham da
Câmara; agora bloco entra pela primeira vez). Reusa `salvar_perfis_coletivos`.

Escopo de comissões: o colegiado do Senado mistura 17 tipos (permanentes, CPIs,
frentes, grupos, conselhos, mesa…). Filtra-se ao que É comissão
(`DescricaoTipoColegiado` começa com "Comiss") — o análogo das permanentes da
Câmara. Frentes/grupos parlamentares do Senado são refinamento futuro (honesto,
não silencioso).

O slug leva o marcador `-sf` para não colidir com comissões homônimas da Câmara
(CCJ existe nas duas casas).
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

FONTE_COMISSOES_SENADO = "senado.colegiados"
FONTE_BLOCOS_SENADO = "senado.blocos"
BASE = "https://legis.senado.leg.br/dadosabertos"

CAMPOS_CRITICOS_COLEGIADO = frozenset({"Codigo", "Nome", "DescricaoTipoColegiado"})
CAMPOS_CRITICOS_BLOCO = frozenset({"CodigoBloco", "NomeBloco"})


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


def _e_comissao(colegiado: dict) -> bool:
    return str(colegiado.get("DescricaoTipoColegiado") or "").lower().startswith("comiss")


# -----------------------------------------------------------------------------
# Comissões (colegiados do tipo comissão)
# -----------------------------------------------------------------------------

def coletar_bronze_comissoes_senado(
    cliente: ClienteHttp, *, politica: PoliticaRetry = PoliticaRetry(),
) -> list[RegistroBronze]:
    """Colegiados que SÃO comissão. A fonte devolve todos os 17 tipos numa
    resposta; filtra-se ao que é comissão (o resto é escopo próprio)."""
    url = f"{BASE}/comissao/lista/colegiados"
    corpo = obter_com_retry(cliente, url, politica=politica)
    lc = (corpo or {}).get("ListaColegiados") or {}
    cols = (lc.get("Colegiados") or {}).get("Colegiado")
    return [RegistroBronze.de(FONTE_COMISSOES_SENADO, url, c)
            for c in _como_lista(cols) if _e_comissao(c)]


def transformar_comissao_senado(payload: dict) -> dict:
    id_fonte = str(payload.get("Codigo") or "") or None
    sigla = payload.get("Sigla")
    nome = payload.get("Nome")
    rotulo = sigla or nome
    return {
        "id_fonte": id_fonte,
        "tipo": "comissao",
        "nome": nome,
        "sigla": sigla,
        "slug": _slug("comissao-sf", rotulo, id_fonte) if rotulo and id_fonte else None,
        "ativo": True,
    }


VERIFICADORES_COMISSAO_SENADO = [
    campo_obrigatorio("id_fonte"),
    campo_obrigatorio("nome"),
    campo_obrigatorio("slug"),
]


# -----------------------------------------------------------------------------
# Blocos parlamentares
# -----------------------------------------------------------------------------

def coletar_bronze_blocos_senado(
    cliente: ClienteHttp, *, politica: PoliticaRetry = PoliticaRetry(),
) -> list[RegistroBronze]:
    url = f"{BASE}/composicao/lista/blocos"
    corpo = obter_com_retry(cliente, url, politica=politica)
    lb = (corpo or {}).get("ListaBlocoParlamentar") or {}
    blocos = (lb.get("Blocos") or {}).get("Bloco")
    return [RegistroBronze.de(FONTE_BLOCOS_SENADO, url, b)
            for b in _como_lista(blocos)]


def transformar_bloco_senado(payload: dict) -> dict:
    id_fonte = str(payload.get("CodigoBloco") or "") or None
    nome = payload.get("NomeBloco")
    apelido = payload.get("NomeApelido")
    rotulo = apelido or nome
    return {
        "id_fonte": id_fonte,
        "tipo": "bloco",
        "nome": nome,
        "sigla": apelido,
        "slug": _slug("bloco", rotulo, id_fonte) if rotulo and id_fonte else None,
        "ativo": True,
    }


VERIFICADORES_BLOCO_SENADO = [
    campo_obrigatorio("id_fonte"),
    campo_obrigatorio("nome"),
    campo_obrigatorio("slug"),
]


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
    cliente: ClienteHttp, *, coletar, transformar, verificadores, criticos,
    canario_validado: bool, linha_base: frozenset[str] | None,
    politica: PoliticaRetry,
) -> ResultadoRodadaColetivos:
    erro_falha: str | None = None
    erro_instabilidade: str | None = None
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
    if not bronze and erro_falha is None and erro_instabilidade is None:
        return ResultadoRodadaColetivos(
            EstadoContrato.OK, "lista vazia", bronze, ResultadoPortao())
    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaColetivos(contrato.estado, contrato.detalhe, bronze)
    prata = portao_bronze_prata(
        bronze, transformar=transformar, verificadores=verificadores)
    return ResultadoRodadaColetivos(contrato.estado, contrato.detalhe, bronze, prata)


def rodada_comissoes_senado(
    cliente: ClienteHttp, *, canario_validado: bool,
    linha_base: frozenset[str] | None, politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodadaColetivos:
    return _rodada(
        cliente, coletar=coletar_bronze_comissoes_senado,
        transformar=transformar_comissao_senado,
        verificadores=VERIFICADORES_COMISSAO_SENADO,
        criticos=CAMPOS_CRITICOS_COLEGIADO,
        canario_validado=canario_validado, linha_base=linha_base, politica=politica)


def rodada_blocos_senado(
    cliente: ClienteHttp, *, canario_validado: bool,
    linha_base: frozenset[str] | None, politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodadaColetivos:
    return _rodada(
        cliente, coletar=coletar_bronze_blocos_senado,
        transformar=transformar_bloco_senado,
        verificadores=VERIFICADORES_BLOCO_SENADO,
        criticos=CAMPOS_CRITICOS_BLOCO,
        canario_validado=canario_validado, linha_base=linha_base, politica=politica)
