"""Coletor do Senado — mandato histórico → vinculo_temporal (Área, §4/§17).

Fonte: https://legis.senado.leg.br/dadosabertos/senador/{codigo}/mandatos
Verificado ao vivo em 2026-08-01 (senador 5672).

Análogo de `camara/mandatos.py`: converte o histórico de mandatos em vigências
partidárias NÃO sobrepostas (partido/UF/ocupação por período), o alvo do §4
("resolver o partido na data do fato, não no presente").

Por que isto importa (bug de correção que corrige): o coletor de senadores
gravava o partido ATUAL sobre o mandato inteiro — exatamente o modo de falha §4.
Aqui, cada `Mandato` traz `Partidos` com `DataFiliacao`/`DataDesfiliacao`, então
um senador que trocou de partido no meio do mandato (Alan Rick: UNIÃO até
2025-11-10, depois REPUBLICANOS) rende DOIS vínculos, cada um com sua vigência.

Estrutura da fonte:
    MandatoParlamentar.Parlamentar.Mandatos.Mandato[]
      cada um: UfParlamentar, DescricaoParticipacao, PrimeiraLegislaturaDoMandato
      {NumeroLegislatura, DataInicio, DataFim}, SegundaLegislaturaDoMandato,
      Partidos.Partido[]{Sigla, DataFiliacao, DataDesfiliacao}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from contrato.canario import EstadoContrato, avaliar
from pipeline.camadas import RegistroBronze
from pipeline.coletor import (
    ClienteHttp,
    ErroFalha,
    ErroInstabilidade,
    PoliticaRetry,
    obter_com_retry,
)

FONTE = "senado.mandatos"
BASE = "https://legis.senado.leg.br/dadosabertos"

CAMPOS_CRITICOS_MANDATO = frozenset({
    "CodigoMandato", "UfParlamentar", "PrimeiraLegislaturaDoMandato",
})


def _como_lista(v: Any) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _ocupacao(descricao: Any) -> str:
    return "suplente_em_exercicio" if "suplente" in str(descricao or "").lower() else "titular"


def coletar_bronze_mandatos_senado(
    cliente: ClienteHttp, codigo: str, *, politica: PoliticaRetry = PoliticaRetry(),
) -> list[RegistroBronze]:
    """Mandatos (histórico) de UM senador. Um bronze por mandato."""
    url = f"{BASE}/senador/{codigo}/mandatos"
    corpo = obter_com_retry(cliente, url, politica=politica)
    par = (((corpo or {}).get("MandatoParlamentar") or {}).get("Parlamentar") or {})
    mandatos = (par.get("Mandatos") or {}).get("Mandato")
    return [RegistroBronze.de(FONTE, url, m) for m in _como_lista(mandatos)]


def _mais_tarde(a: str | None, b: str | None) -> str | None:
    """Data ISO posterior (lexicográfico = cronológico). Ignora None."""
    if a is None:
        return b
    if b is None:
        return a
    return a if a >= b else b


def _mais_cedo(a: str | None, b: str | None) -> str | None:
    if a is None:
        return b
    if b is None:
        return a
    return a if a <= b else b


def construir_vinculos_senado(
    mandatos: list[dict], codigo: str, *, casa: str = "senado",
) -> list[dict]:
    """Cruza cada mandato (legislatura + UF + ocupação) com seus períodos
    partidários, clipando cada filiação à janela do mandato. Sem `Partidos`,
    rende um vínculo do mandato inteiro com `partido_sigla_fonte` None."""
    vinculos: list[dict] = []
    for m in mandatos:
        uf = m.get("UfParlamentar")
        ocup = _ocupacao(m.get("DescricaoParticipacao"))
        prim = m.get("PrimeiraLegislaturaDoMandato") or {}
        seg = m.get("SegundaLegislaturaDoMandato") or {}
        m_ini = prim.get("DataInicio")
        m_fim = seg.get("DataFim") or prim.get("DataFim")
        leg = prim.get("NumeroLegislatura")
        if not m_ini or not uf:
            continue

        partidos = _como_lista((m.get("Partidos") or {}).get("Partido"))
        periodos: list[tuple[str, str | None, str | None]] = []
        for pt in partidos:
            inicio = _mais_tarde(pt.get("DataFiliacao"), m_ini)   # clip início
            fim = pt.get("DataDesfiliacao")
            if m_fim:
                fim = _mais_cedo(fim, m_fim)                       # clip fim
            # filiação inteiramente fora da janela do mandato → descarta
            if fim is not None and inicio >= fim:
                continue
            periodos.append((inicio, fim, pt.get("Sigla")))
        if not partidos:
            periodos.append((m_ini, m_fim, None))

        periodos.sort(key=lambda p: p[0])
        for inicio, fim, sigla in periodos:
            vinculos.append({
                "id_fonte": str(codigo),
                "casa": casa,
                "legislatura": int(leg) if leg else None,
                "uf": uf,
                "partido_sigla_fonte": sigla,
                "ocupacao": ocup,
                "vigencia_inicio": inicio,
                "vigencia_fim": fim,
            })
    return vinculos


@dataclass
class ResultadoRodadaMandatosSenado:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    vinculos: list[dict] = field(default_factory=list)


def rodada_mandatos_senado(
    cliente: ClienteHttp, codigo: str, *,
    canario_validado: bool, linha_base: frozenset[str] | None,
    politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodadaMandatosSenado:
    erro_falha: str | None = None
    erro_instabilidade: str | None = None
    bronze: list[RegistroBronze] = []
    try:
        bronze = coletar_bronze_mandatos_senado(cliente, codigo, politica=politica)
    except ErroFalha as e:
        erro_falha = str(e)
    except ErroInstabilidade as e:
        erro_instabilidade = str(e)

    amostra = bronze[0].payload if bronze else None
    contrato = avaliar(
        canario_validado=canario_validado,
        resposta=[amostra] if amostra is not None else None,
        erro_falha=erro_falha, erro_instabilidade=erro_instabilidade,
        linha_base=linha_base, criticos=CAMPOS_CRITICOS_MANDATO,
    )
    if not bronze and erro_falha is None and erro_instabilidade is None:
        return ResultadoRodadaMandatosSenado(EstadoContrato.OK, "sem mandatos", bronze)
    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaMandatosSenado(contrato.estado, contrato.detalhe, bronze)
    vinculos = construir_vinculos_senado([b.payload for b in bronze], codigo)
    return ResultadoRodadaMandatosSenado(contrato.estado, contrato.detalhe, bronze, vinculos)
