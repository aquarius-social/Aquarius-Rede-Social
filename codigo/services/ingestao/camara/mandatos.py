"""Coletor da Câmara — histórico de mandatos → `vinculo_temporal` (§12 D4, §4).

Fonte: `https://dadosabertos.camara.leg.br/api/v2/deputados/{id}/historico`.

É a camada TEMPORAL do parlamentar: versiona partido, UF e ocupação da cadeira
por período. Existe para resolver todo atributo NA DATA DO FATO — um voto de
2021 resolve o partido de 2021, não o atual (§4, Tabela 9). Sem isto, a camada
ouro e o contrato de resposta do Prometeus atribuem voto antigo ao partido de
hoje.

FORMATO DA FONTE (verificado ao vivo, 2026-07-29). O histórico é uma lista de
SNAPSHOTS pontuais (cada um com `dataHora`), não de intervalos: posse, alteração
de partido, licença, fim de mandato, convocação de suplente. A transformação
pareia snapshots consecutivos em períodos `[início, próximo_início)` — a
`vigencia` (daterange) que `vinculo_temporal` exige.

DISCIPLINAS (§12, §5.2, §4):

  - Toda transição com data (§12 D3): snapshot sem `dataHora` não é posicionável
    no tempo — vai à quarentena, não é chutado.
  - Intervalos de duração nula descartados (§12 D5): os marcadores de borda
    ("Nome no início da legislatura" e a posse no mesmo instante) produzem
    período vazio, que não é mandato.
  - Mandatos sem sobreposição (§5.2): garantido por construção (períodos
    consecutivos de snapshots ordenados); `conferir_sem_sobreposicao` prova.
  - `partido_id` canônico fica None neste passe; preserva-se `partido_sigla_fonte`
    (a verdade da fonte). Resolver o partido canônico é o coletor de `/partidos`
    + linhagem por curadoria (§4), etapa própria.
  - Suplente em exercício vai à QUARENTENA: `vinculo_temporal` exige o titular da
    cadeira (constraint `vinculo_suplente_coerente`), e descobrir de quem é a
    cadeira é cross-referência da §6.4 — etapa própria. Dado ausente é melhor
    que dado errado (§1).

INSTABILIDADE (§12 D2): este é o endpoint menos disponível da Câmara — alterna
resposta e falha, com falha convergindo por ~15s. A coleta usa o mesmo retry dos
demais (é 'instabilidade', não 'falha', §19) e é feita em lote, persistida, nunca
consultada ao vivo. Se falhar, a versão anterior segue válida com a data declarada.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from contrato.canario import EstadoContrato, avaliar
from pipeline.camadas import RegistroBronze, Violacao
from pipeline.coletor import (
    ClienteHttp,
    ErroFalha,
    ErroInstabilidade,
    PoliticaRetry,
    obter_com_retry,
)

FONTE = "camara.historico"
BASE = "https://dadosabertos.camara.leg.br/api/v2"

CAMPOS_CRITICOS_HISTORICO = frozenset({
    "dataHora", "siglaPartido", "siglaUf", "situacao"
})


# -----------------------------------------------------------------------------
# Coleta — bronze
# -----------------------------------------------------------------------------

def coletar_bronze_historico(
    cliente: ClienteHttp,
    deputado_id_fonte: str,
    *,
    politica: PoliticaRetry = PoliticaRetry(),
) -> list[RegistroBronze]:
    """Snapshots do histórico de UM deputado. Endpoint instável (§12 D2) — o
    retry de `obter_com_retry` trata a instabilidade; o chamador coleta em lote."""
    url = f"{BASE}/deputados/{deputado_id_fonte}/historico"
    corpo = obter_com_retry(cliente, url, politica=politica)
    return [
        RegistroBronze.de(FONTE, url, item)
        for item in (corpo or {}).get("dados", [])
    ]


# -----------------------------------------------------------------------------
# Transformação — snapshots → intervalos (vinculo_temporal)
# -----------------------------------------------------------------------------

def _ocupacao(condicao: Any, situacao: Any) -> str | None:
    """Ocupação da cadeira a partir de (condicaoEleitoral, situacao). None quando
    o snapshot NÃO é um período de ocupação (borda, fim de mandato, suplência sem
    convocação) — esses fecham o período anterior, não abrem um novo."""
    if situacao == "Exercício":
        if condicao in ("Titular", "Efetivado"):
            return "titular"
        if condicao == "Suplente":
            return "suplente_em_exercicio"
    if situacao == "Convocado":
        return "suplente_em_exercicio"
    if situacao in ("Licenciado", "Afastado"):
        return "licenciado"
    return None


@dataclass
class ResultadoVinculos:
    aprovados: list[dict] = field(default_factory=list)
    quarentena: list[tuple[dict, Violacao]] = field(default_factory=list)


def construir_vinculos(
    historico: list[dict], deputado_id_fonte: str, *, casa: str = "camara",
) -> ResultadoVinculos:
    """Converte os snapshots do histórico em vínculos temporais com vigência.

    Cada snapshot de ocupação vale de sua `dataHora` até a `dataHora` do próximo
    snapshot; o último fica em aberto. Períodos idênticos consecutivos em
    (uf, partido, ocupação) são fundidos. Zero-duração é descartado.
    """
    resultado = ResultadoVinculos()

    datados: list[dict] = []
    for h in historico:
        if not h.get("dataHora"):
            resultado.quarentena.append((
                h, Violacao("completude",
                            "transição sem dataHora — não é posicionável no tempo"),
            ))
            continue
        datados.append(h)
    datados.sort(key=lambda h: h["dataHora"])

    # Monta períodos crus: cada snapshot [inicio, inicio_do_proximo).
    crus: list[dict] = []
    for i, s in enumerate(datados):
        ocup = _ocupacao(s.get("condicaoEleitoral"), s.get("situacao"))
        if ocup is None:
            continue  # borda / fim de mandato — não é ocupação
        inicio = s["dataHora"][:10]
        fim = datados[i + 1]["dataHora"][:10] if i + 1 < len(datados) else None
        if fim is not None and fim <= inicio:
            continue  # duração nula/negativa (§12 D5)
        crus.append({
            "id_fonte": str(deputado_id_fonte),
            "casa": casa,
            "legislatura": s.get("idLegislatura"),
            "uf": s.get("siglaUf"),
            "partido_sigla_fonte": s.get("siglaPartido"),
            "partido_id": None,  # canônico resolvido depois (§4)
            "ocupacao": ocup,
            "vigencia_inicio": inicio,
            "vigencia_fim": fim,
        })

    # Funde períodos consecutivos idênticos em (uf, partido, ocupacao).
    fundidos = _fundir_consecutivos(crus)

    for v in fundidos:
        if v["ocupacao"] == "suplente_em_exercicio":
            resultado.quarentena.append((
                v, Violacao(
                    "integridade_referencial",
                    "suplente em exercício exige resolver o titular da cadeira "
                    "(§6.4) — etapa própria; sem ele a constraint recusaria",
                ),
            ))
            continue
        resultado.aprovados.append(v)
    return resultado


def _fundir_consecutivos(periodos: list[dict]) -> list[dict]:
    """Funde períodos adjacentes com mesmo (uf, partido, ocupacao). A vigência
    resultante vai do início do primeiro ao fim do último."""
    fundidos: list[dict] = []
    for p in periodos:
        ult = fundidos[-1] if fundidos else None
        mesma_chave = ult is not None and (
            ult["uf"] == p["uf"]
            and ult["partido_sigla_fonte"] == p["partido_sigla_fonte"]
            and ult["ocupacao"] == p["ocupacao"]
            and ult["vigencia_fim"] == p["vigencia_inicio"]  # adjacentes
        )
        if mesma_chave:
            ult["vigencia_fim"] = p["vigencia_fim"]
        else:
            fundidos.append(dict(p))
    return fundidos


def conferir_sem_sobreposicao(vinculos: list[dict]) -> list[Violacao]:
    """Identidade §5.2: mandatos de uma pessoa/casa não se sobrepõem. Por
    construção não deveriam; esta prova protege contra regressão."""
    violacoes: list[Violacao] = []
    ordenados = sorted(vinculos, key=lambda v: v["vigencia_inicio"])
    anterior: dict | None = None
    for v in ordenados:
        if anterior is not None:
            fim_ant = anterior["vigencia_fim"]
            if fim_ant is None or v["vigencia_inicio"] < fim_ant:
                violacoes.append(Violacao(
                    "consistencia",
                    f"vigências sobrepostas: {anterior['vigencia_inicio']}.."
                    f"{fim_ant} e {v['vigencia_inicio']}..{v['vigencia_fim']}",
                ))
        anterior = v
    return violacoes


# -----------------------------------------------------------------------------
# Rodada — para UM deputado
# -----------------------------------------------------------------------------

@dataclass
class ResultadoRodadaHistorico:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    vinculos: ResultadoVinculos | None = None
    sobreposicao_violacoes: list[Violacao] = field(default_factory=list)


def rodada_historico(
    cliente: ClienteHttp,
    deputado_id_fonte: str,
    *,
    canario_validado: bool,
    linha_base: frozenset[str] | None,
    politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodadaHistorico:
    """Coleta o histórico de um deputado, avalia o contrato e constrói os
    vínculos temporais. Em FALHA/QUEBRA, a construção é pulada (§19)."""
    erro_falha: str | None = None
    erro_instabilidade: str | None = None
    bronze: list[RegistroBronze] = []

    try:
        bronze = coletar_bronze_historico(cliente, deputado_id_fonte, politica=politica)
    except ErroFalha as e:
        erro_falha = str(e)
    except ErroInstabilidade as e:
        erro_instabilidade = str(e)

    amostra = bronze[0].payload if bronze else None
    contrato = avaliar(
        canario_validado=canario_validado,
        resposta=[amostra] if amostra is not None else None,
        erro_falha=erro_falha,
        erro_instabilidade=erro_instabilidade,
        linha_base=linha_base,
        criticos=CAMPOS_CRITICOS_HISTORICO,
    )

    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaHistorico(
            estado=contrato.estado, detalhe=contrato.detalhe, bronze=bronze,
        )

    vinculos = construir_vinculos([r.payload for r in bronze], deputado_id_fonte)
    sobrep = conferir_sem_sobreposicao(vinculos.aprovados)
    return ResultadoRodadaHistorico(
        estado=contrato.estado, detalhe=contrato.detalhe,
        bronze=bronze, vinculos=vinculos, sobreposicao_violacoes=sobrep,
    )
