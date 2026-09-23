"""Coletor do Senado — presença em sessões do Plenário (Área E, §11/§4, bicameral).

O Senado NÃO expõe uma lista de presença por sessão (confirmado no catálogo de
dados abertos: comparecimento é registrado em VOTAÇÃO). A presença oficial vive
no `comparecimento` de cada votação nominal: `/votacao?dataInicio&dataFim` traz,
por votação, TODOS os 81 senadores com `siglaVotoParlamentar` — que é ou uma
posição (Sim/Não/Abstenção/Obstrução) ou um tipo de comparecimento (licença,
missão, ausência…). Presente = votou uma posição ou uma sigla de presença
explícita; o resto é ausência (com motivo — a própria sigla).

DERIVAÇÃO (documentada, honesta): a `sessao` do Senado = uma sessão com ≥1
votação nominal (`codigoSessao`); o senador está PRESENTE na sessão se esteve
presente em ≥1 votação dela. Difere do método da Câmara (lista de presença por
sessão) — a fonte do Senado só publica comparecimento em votação. `source` na
view distingue as duas (`camara.presenca` × `senado.presenca`).

Produz a MESMA prata de `camara/presenca.py` (sessão + presença, casa='senado'),
então reusa `salvar_sessoes`/`salvar_presencas` sem alteração.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from contrato.canario import EstadoContrato, avaliar
from pipeline.camadas import RegistroBronze
from pipeline.coletor import (
    ClienteHttp, ErroFalha, ErroInstabilidade, PoliticaRetry, obter_com_retry)

FONTE = "senado.presenca"
BASE = "https://legis.senado.leg.br/dadosabertos"

# Campos críticos de uma votação (o que a derivação precisa). Verificado ao vivo
# (2026-09-23): presentes.
CAMPOS_CRITICOS_VOTACAO_SENADO = frozenset({"codigoSessao", "dataSessao", "votos"})

# Siglas de `siglaVotoParlamentar` que indicam PRESENÇA física. Tudo o mais
# (licenças L*, AP, MIS, AUS, NCom, AFO, DJ, EP, GR, NR, NH, NA…) é ausência —
# a própria sigla é o motivo (comparecimento). Conservador: só conta presença
# clara. Ver /plenario/lista/tiposComparecimento.
_PRESENTE_SIGLAS = frozenset({
    "sim", "não", "nao", "abstenção", "abstencao", "obstrução", "obstrucao",
    "votou", "vo", "si", "pr", "ps", "psf", "sf", "p-nrv", "p-od", "ob",
})


def _esta_presente(sigla: Any) -> bool:
    s = str(sigla or "").strip().lower()
    if not s:
        return False
    if s in _PRESENTE_SIGLAS:
        return True
    return s.startswith("presid") or s.startswith("presente")


def _como_lista(v: Any) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def coletar_bronze_votacoes_presenca(
    cliente: ClienteHttp, *, data_inicio: str, data_fim: str,
    politica: PoliticaRetry = PoliticaRetry(),
) -> list[RegistroBronze]:
    """Votações nominais (com comparecimento) na janela [data_inicio, data_fim]
    (YYYY-MM-DD). Um bronze por votação."""
    url = f"{BASE}/votacao"
    corpo = obter_com_retry(
        cliente, url, params={"dataInicio": data_inicio, "dataFim": data_fim},
        politica=politica)
    if isinstance(corpo, list):
        lista = corpo
    else:
        lista = _como_lista((corpo or {}).get("Votacoes", {}).get("Votacao"))
    return [RegistroBronze.de(FONTE, url, v) for v in lista]


def _votos(payload: dict) -> list[dict]:
    v = payload.get("votos")
    if isinstance(v, dict):
        return _como_lista(v.get("VotoParlamentar"))
    return _como_lista(v)


@dataclass
class ResultadoRodadaPresencaSenado:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    sessoes: list[dict] = field(default_factory=list)
    # id_fonte da sessão -> lista de {id_parlamentar, presente} (só presentes)
    presencas: dict[str, list[dict]] = field(default_factory=dict)


def rodada_presenca_senado(
    cliente: ClienteHttp, *, data_inicio: str, data_fim: str,
    canario_validado: bool, linha_base: frozenset[str] | None,
    politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodadaPresencaSenado:
    erro_falha: str | None = None
    erro_instabilidade: str | None = None
    bronze: list[RegistroBronze] = []
    try:
        bronze = coletar_bronze_votacoes_presenca(
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
        linha_base=linha_base, criticos=CAMPOS_CRITICOS_VOTACAO_SENADO)
    if not bronze and erro_falha is None and erro_instabilidade is None:
        return ResultadoRodadaPresencaSenado(
            EstadoContrato.OK, "sem votações na janela", bronze)
    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaPresencaSenado(contrato.estado, contrato.detalhe, bronze)

    # Agrega por sessão: metadados + conjunto de presentes (presente em ≥1 votação).
    sessoes: dict[str, dict] = {}
    presentes: dict[str, set[str]] = {}
    for reg in bronze:
        p = reg.payload
        # só sessões do Senado Federal (exclui Congresso/CN)
        if str(p.get("casaSessao") or "SF").upper() not in ("SF", ""):
            continue
        sid = str(p.get("codigoSessao") or "") or None
        if not sid:
            continue
        if sid not in sessoes:
            sessoes[sid] = {
                "id_fonte": sid,
                "casa": "senado",
                "tipo": p.get("siglaTipoSessao"),
                "data_hora": p.get("dataSessao"),
                "orgao_sigla": "PLEN",
            }
            presentes[sid] = set()
        for vp in _votos(p):
            cod = vp.get("codigoParlamentar")
            if cod is not None and _esta_presente(vp.get("siglaVotoParlamentar")):
                presentes[sid].add(str(cod))

    presencas = {
        sid: [{"id_parlamentar": c, "presente": True} for c in sorted(cods)]
        for sid, cods in presentes.items()
    }
    return ResultadoRodadaPresencaSenado(
        contrato.estado, contrato.detalhe, bronze,
        sessoes=list(sessoes.values()), presencas=presencas)
