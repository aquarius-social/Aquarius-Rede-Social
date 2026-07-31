"""Coletor de emendas parlamentares — execução orçamentária (Área F, §13).

Fonte: API de Emendas do Portal da Transparência
    https://api.portaldatransparencia.gov.br/api-de-dados/emendas
EXIGE chave pessoal no header `chave-api-dados` (cadastro grátis; só o dono da
conta pode obter — GUIA_Ingestao_Emendas.md). Sem a chave, a área é pulada no
orquestrador. Campos verificados contra o dado real baixado (emendas_2024.json,
6990 registros).

DISCIPLINAS (§13):
  - Estágios orçamentários NUNCA se somam: empenhado, liquidado, pago (e restos).
    Identidade de ordem (§5.2): empenhado ≥ liquidado ≥ pago; restos pago+cancelado
    ≤ inscrito — verificada no portão.
  - Valores vêm em formato BR ("10.000,00"); parseados para número.
  - Autoria pelo identificador embutido no `codigoEmenda` (§6.3): extrai-se
    `autor_codigo` (o meio do código). A resolução ao perfil é curadoria própria
    (mapa de autores → id_externo 'autor_orcamentario'); aqui fica só o código.
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

FONTE = "transparencia.emendas"
BASE = "https://api.portaldatransparencia.gov.br/api-de-dados"

CAMPOS_CRITICOS_EMENDA = frozenset({
    "codigoEmenda", "ano", "valorEmpenhado", "valorLiquidado", "valorPago"
})

# Tolerância de centavos na comparação de estágios (valores têm 2 casas).
_EPS = 0.005


# -----------------------------------------------------------------------------
# Coleta — bronze (paginada por `pagina`)
# -----------------------------------------------------------------------------

def coletar_bronze_emendas(
    cliente: ClienteHttp,
    ano: int,
    *,
    politica: PoliticaRetry = PoliticaRetry(),
    limite_paginas: int = 2000,
) -> list[RegistroBronze]:
    """Emendas de um exercício. Pagina por `pagina` até a fonte devolver vazio.

    A API do Portal da Transparência não devolve `links` de paginação: a parada
    é a página vazia. `limite_paginas` é backstop contra laço infinito.
    """
    url = f"{BASE}/emendas"
    bronze: list[RegistroBronze] = []
    pagina = 1
    while pagina <= limite_paginas:
        corpo = obter_com_retry(
            cliente, url, params={"ano": ano, "pagina": pagina}, politica=politica)
        itens = corpo if isinstance(corpo, list) else (corpo or {}).get("dados", [])
        if not itens:
            break
        for item in itens:
            bronze.append(RegistroBronze.de(FONTE, url, item))
        pagina += 1
    return bronze


def _proximo_link(corpo: Any) -> str | None:  # a API não pagina por link
    return None


# -----------------------------------------------------------------------------
# Transformação
# -----------------------------------------------------------------------------

def _valor(v: Any) -> float | None:
    """Parse do formato BR ('10.000,00' → 10000.0). Vazio → None."""
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _int(v: Any) -> int | None:
    try:
        return int(v) if v is not None and str(v) != "" else None
    except (TypeError, ValueError):
        return None


def _autor_codigo(codigo: str | None, numero: Any) -> str | None:
    """Código do autor embutido no codigoEmenda (§6.3): ano(4) + AUTOR + numero.
    Ex.: '202440340007' com numero '0007' → '4034'."""
    if not codigo:
        return None
    num = str(numero or "")
    fim = len(codigo) - len(num) if num and len(codigo) > 4 + len(num) else len(codigo)
    meio = codigo[4:fim]
    return meio or None


def transformar_emenda(payload: dict) -> dict:
    codigo = str(payload.get("codigoEmenda") or "") or None
    numero = payload.get("numeroEmenda")
    return {
        "codigo_emenda": codigo,
        "ano": _int(payload.get("ano")),
        "tipo": payload.get("tipoEmenda"),
        "numero": numero,
        "autor_nome": payload.get("autor") or payload.get("nomeAutor"),
        "autor_codigo": _autor_codigo(codigo, numero),
        "localidade_gasto": payload.get("localidadeDoGasto"),
        "funcao": payload.get("funcao"),
        "subfuncao": payload.get("subfuncao"),
        "valor_empenhado": _valor(payload.get("valorEmpenhado")),
        "valor_liquidado": _valor(payload.get("valorLiquidado")),
        "valor_pago": _valor(payload.get("valorPago")),
        "valor_resto_inscrito": _valor(payload.get("valorRestoInscrito")),
        "valor_resto_cancelado": _valor(payload.get("valorRestoCancelado")),
        "valor_resto_pago": _valor(payload.get("valorRestoPago")),
    }


def _estagios_coerentes(reg: dict) -> Violacao | None:
    """Identidade de ordem (§5.2): empenhado ≥ liquidado ≥ pago; e restos pago +
    cancelado ≤ inscrito. Só checável quando os valores existem."""
    emp, liq, pago = (reg.get("valor_empenhado"),
                      reg.get("valor_liquidado"), reg.get("valor_pago"))
    if emp is not None and liq is not None and liq - emp > _EPS:
        return Violacao("consistencia", f"liquidado {liq} > empenhado {emp}")
    if liq is not None and pago is not None and pago - liq > _EPS:
        return Violacao("consistencia", f"pago {pago} > liquidado {liq}")
    ins, rp, rc = (reg.get("valor_resto_inscrito"),
                   reg.get("valor_resto_pago"), reg.get("valor_resto_cancelado"))
    if ins is not None and rp is not None and rc is not None and (rp + rc) - ins > _EPS:
        return Violacao("consistencia",
                        f"restos pago+cancelado {rp + rc} > inscrito {ins}")
    return None


VERIFICADORES_EMENDA = [
    campo_obrigatorio("codigo_emenda"),
    _estagios_coerentes,
]


def processar_emendas_para_prata(bronze: list[RegistroBronze]) -> ResultadoPortao:
    return portao_bronze_prata(
        bronze, transformar=transformar_emenda, verificadores=VERIFICADORES_EMENDA)


# -----------------------------------------------------------------------------
# Rodada — por exercício
# -----------------------------------------------------------------------------

@dataclass
class ResultadoRodadaEmendas:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    prata: ResultadoPortao | None = None


def rodada_emendas(
    cliente: ClienteHttp,
    ano: int,
    *,
    canario_validado: bool,
    linha_base: frozenset[str] | None,
    politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodadaEmendas:
    erro_falha = erro_instabilidade = None
    bronze: list[RegistroBronze] = []
    try:
        bronze = coletar_bronze_emendas(cliente, ano, politica=politica)
    except ErroFalha as e:
        erro_falha = str(e)
    except ErroInstabilidade as e:
        erro_instabilidade = str(e)

    amostra = bronze[0].payload if bronze else None
    contrato = avaliar(
        canario_validado=canario_validado,
        resposta=[amostra] if amostra is not None else None,
        erro_falha=erro_falha, erro_instabilidade=erro_instabilidade,
        linha_base=linha_base, criticos=CAMPOS_CRITICOS_EMENDA,
    )
    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaEmendas(contrato.estado, contrato.detalhe, bronze)
    prata = processar_emendas_para_prata(bronze)
    return ResultadoRodadaEmendas(contrato.estado, contrato.detalhe, bronze, prata)
