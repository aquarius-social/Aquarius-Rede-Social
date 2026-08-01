"""Coletor do Senado — tramitações de matérias (Área D, §11, bicameral).

Fonte: https://legis.senado.leg.br/dadosabertos/processo/{idProcesso}
ATENÇÃO (§19, disciplina de descontinuação): o endpoint antigo
`/materia/movimentacoes/{codigo}` foi DESCONTINUADO (DataDesativacaoCompleta
2026-02-01) e a própria fonte aponta `/processo/{idProcesso}` como substituto —
usamos o substituto, não o endpoint morto. Verificado ao vivo em 2026-08-01
(processo 8614284 = PL 1/2024: 19 informes legislativos).

O `idProcesso` (≠ código da matéria) vem do campo `IdentificacaoProcesso` da
pesquisa de matérias e é carregado na prata da matéria (`id_processo`).

A tramitação vive em `autuacoes[].informesLegislativos[]` — os eventos datados
com colegiado e descrição, o análogo da tramitação da Câmara. As
`movimentacoes` (envelope físico entre secretarias) são logística de baixo
nível, não a narrativa legislativa; ficam de fora.

Produz a MESMA prata que `camara/tramitacoes.py` (com `casa='senado'`), então
reusa `salvar_tramitacoes` sem alteração e a checagem §5.2 de monotonicidade.

Sequência: os informes NÃO trazem um número de sequência; o Senado atribui `id`
em ordem de criação (cronológica). Ordena-se por `id` e atribui-se sequência
1..N — assim a checagem "a data não retrocede ao longo da sequência" (§5.2)
compara a ordem-de-criação da fonte contra a data, e é um teste REAL (não
tautológico).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Reusa a identidade §5.2 (monotonicidade) — house-agnóstica, opera na prata.
from camara.tramitacoes import conferir_sequencia_monotonica
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

FONTE = "senado.tramitacoes"
BASE = "https://legis.senado.leg.br/dadosabertos"

# Campos críticos de um informe legislativo. Verificado ao vivo (2026-08-01).
CAMPOS_CRITICOS_TRAMITACAO_SENADO = frozenset({"id", "data", "descricao"})


def _como_lista(v: Any) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def coletar_bronze_tramitacoes_senado(
    cliente: ClienteHttp,
    id_processo: str,
    *,
    politica: PoliticaRetry = PoliticaRetry(),
) -> list[RegistroBronze]:
    """Informes legislativos (tramitação) de UM processo. Um bronze por informe
    (payload cru do informe, §3.1)."""
    url = f"{BASE}/processo/{id_processo}"
    corpo = obter_com_retry(cliente, url, politica=politica)
    proc = corpo[0] if isinstance(corpo, list) else (corpo or {})
    bronze: list[RegistroBronze] = []
    for aut in _como_lista(proc.get("autuacoes")):
        for inf in _como_lista(aut.get("informesLegislativos")):
            bronze.append(RegistroBronze.de(FONTE, url, inf))
    return bronze


def _int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _texto(v: Any) -> str | None:
    if v is None:
        return None
    t = str(v).replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    t = " ".join(t.split())
    return t or None


def _iso(v: Any) -> str | None:
    """A fonte entrega 'YYYY-MM-DD HH:MM:SS' (espaço); vira ISO-8601 (T)."""
    if not v:
        return None
    return str(v).strip().replace(" ", "T")


def transformar_tramitacao_senado(
    informe: dict, proposicao_id_fonte: str, sequencia: int | None
) -> dict:
    colegiado = informe.get("colegiado") or {}
    ente = informe.get("enteAdministrativo") or {}
    return {
        "proposicao_id_fonte": str(proposicao_id_fonte),
        "casa": "senado",
        "sequencia": sequencia,
        "data_hora": _iso(informe.get("data")),
        "orgao_sigla": colegiado.get("sigla") or ente.get("sigla"),
        "descricao": _texto(informe.get("descricao")),
        # Os informes não trazem texto de despacho separado; o despacho a nível
        # de processo é outro campo, fora deste passe.
        "despacho": None,
    }


def _sequencia_valida(registro: dict) -> Violacao | None:
    seq = registro.get("sequencia")
    if seq is None or seq < 1:
        return Violacao("precisao", f"sequência inválida: {seq!r}")
    return None


VERIFICADORES_TRAMITACAO_SENADO = [
    campo_obrigatorio("data_hora"),
    campo_obrigatorio("descricao"),
    _sequencia_valida,
]


def processar_tramitacoes_senado_para_prata(
    bronze: list[RegistroBronze], proposicao_id_fonte: str,
) -> ResultadoPortao:
    """Ordena por `id` (ordem de criação da fonte), atribui sequência 1..N, e
    passa o portão. O rank por id preserva a ordem autoritativa da fonte para a
    checagem monotônica."""
    ordenados = sorted(
        (b.payload.get("id") for b in bronze), key=lambda x: _int(x) or 0)
    rank = {iid: i for i, iid in enumerate(ordenados, start=1)}

    def _transformar(informe: dict) -> dict:
        return transformar_tramitacao_senado(
            informe, proposicao_id_fonte, rank.get(informe.get("id")))

    return portao_bronze_prata(
        bronze, transformar=_transformar,
        verificadores=VERIFICADORES_TRAMITACAO_SENADO)


@dataclass
class ResultadoRodadaTramitacoesSenado:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    prata: ResultadoPortao | None = None
    sequencia_violacoes: list[Violacao] = field(default_factory=list)


def rodada_tramitacoes_senado(
    cliente: ClienteHttp,
    id_processo: str,
    proposicao_id_fonte: str,
    *,
    canario_validado: bool,
    linha_base: frozenset[str] | None,
    politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodadaTramitacoesSenado:
    erro_falha: str | None = None
    erro_instabilidade: str | None = None
    bronze: list[RegistroBronze] = []
    try:
        bronze = coletar_bronze_tramitacoes_senado(
            cliente, id_processo, politica=politica)
    except ErroFalha as e:
        erro_falha = str(e)
    except ErroInstabilidade as e:
        erro_instabilidade = str(e)

    amostra = bronze[0].payload if bronze else None
    contrato = avaliar(
        canario_validado=canario_validado,
        resposta=[amostra] if amostra is not None else None,
        erro_falha=erro_falha, erro_instabilidade=erro_instabilidade,
        linha_base=linha_base, criticos=CAMPOS_CRITICOS_TRAMITACAO_SENADO,
    )
    # Matéria sem informe é vazio legítimo (recém-protocolada), não FALHA.
    if not bronze and erro_falha is None and erro_instabilidade is None:
        return ResultadoRodadaTramitacoesSenado(
            EstadoContrato.OK, "sem tramitação", bronze, ResultadoPortao())
    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaTramitacoesSenado(contrato.estado, contrato.detalhe, bronze)
    prata = processar_tramitacoes_senado_para_prata(bronze, proposicao_id_fonte)
    seq_viol = conferir_sequencia_monotonica(prata.aprovados)
    return ResultadoRodadaTramitacoesSenado(
        contrato.estado, contrato.detalhe, bronze, prata, seq_viol)
