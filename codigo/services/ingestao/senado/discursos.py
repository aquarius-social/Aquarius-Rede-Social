"""Coletor do Senado — pronunciamentos de senadores (Área G, §13, bicameral).

Fonte: https://legis.senado.leg.br/dadosabertos/senador/{codigo}/discursos
Por senador, janela de data em formato YYYYMMDD (a fonte usa esse layout, sem
hífens). Sem período, devolve os últimos 30 dias. Verificado ao vivo em
2026-07-31 (senador 5672, janela 2024).

Produz a MESMA prata que o coletor de discursos da Câmara — a tabela `discurso`
é bicameral. O pronunciamento do Senado TEM id próprio (`CodigoPronunciamento`),
diferente do discurso da Câmara (id composto). O `parlamentar_id_fonte` é o
código do Senado, resolvido a `profile_id` por id_externo (sistema='senado').

Navegação da fonte:
  DiscursosParlamentar.Parlamentar.Pronunciamentos.Pronunciamento[]
"""

from __future__ import annotations

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

FONTE = "senado.discursos"
BASE = "https://legis.senado.leg.br/dadosabertos"

CAMPOS_CRITICOS_DISCURSO_SENADO = frozenset({
    "CodigoPronunciamento", "DataPronunciamento",
})


def _como_lista(v: Any) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _aaaammdd(iso: str) -> str:
    """A fonte quer YYYYMMDD (sem hífens). Aceita ISO ou já-compacto."""
    return str(iso).replace("-", "")


def coletar_bronze_discursos_senado(
    cliente: ClienteHttp,
    codigo: str,
    *,
    data_inicio: str,
    data_fim: str,
    politica: PoliticaRetry = PoliticaRetry(),
) -> list[RegistroBronze]:
    """Pronunciamentos de UM senador na janela. A fonte devolve tudo numa
    resposta (sem paginação por link)."""
    url = f"{BASE}/senador/{codigo}/discursos"
    corpo = obter_com_retry(
        cliente, url,
        params={"dataInicio": _aaaammdd(data_inicio), "dataFim": _aaaammdd(data_fim)},
        politica=politica)
    par = (((corpo or {}).get("DiscursosParlamentar") or {}).get("Parlamentar") or {})
    pron = (par.get("Pronunciamentos") or {})
    bronze: list[RegistroBronze] = []
    for item in _como_lista(pron.get("Pronunciamento")):
        bronze.append(RegistroBronze.de(FONTE, url, item))
    return bronze


def _data(valor: Any) -> str | None:
    if not valor:
        return None
    return str(valor)[:10]


def transformar_discurso_senado(payload: dict, codigo: str) -> dict:
    return {
        "casa": "senado",
        "sistema": "senado",
        "parlamentar_id_fonte": str(codigo),
        "id_fonte": str(payload.get("CodigoPronunciamento") or "") or None,
        "data": _data(payload.get("DataPronunciamento")),
        "tipo": (payload.get("TipoUsoPalavra") or {}).get("Descricao"),
        "sumario": payload.get("TextoResumo"),
        "keywords": payload.get("Indexacao"),
        "url_texto": payload.get("UrlTexto"),
        "url_video": None,
        "url_audio": None,
        # O Senado dá a URL do texto binário (inteiro teor), não o texto inline.
        "tem_transcricao": bool(payload.get("UrlTextoBinario")),
    }


VERIFICADORES_DISCURSO_SENADO = [
    campo_obrigatorio("parlamentar_id_fonte"),
    campo_obrigatorio("id_fonte"),
    campo_obrigatorio("data"),
]


def processar_discursos_senado_para_prata(
    bronze: list[RegistroBronze], codigo: str
) -> ResultadoPortao:
    def _transformar(item: dict) -> dict:
        return transformar_discurso_senado(item, codigo)

    return portao_bronze_prata(
        bronze, transformar=_transformar, verificadores=VERIFICADORES_DISCURSO_SENADO)


@dataclass
class ResultadoRodadaDiscursosSenado:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    prata: ResultadoPortao | None = None


def rodada_discursos_senado(
    cliente: ClienteHttp,
    codigo: str,
    *,
    canario_validado: bool,
    linha_base: frozenset[str] | None,
    data_inicio: str,
    data_fim: str,
    politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodadaDiscursosSenado:
    erro_falha: str | None = None
    erro_instabilidade: str | None = None
    bronze: list[RegistroBronze] = []
    try:
        bronze = coletar_bronze_discursos_senado(
            cliente, codigo, data_inicio=data_inicio, data_fim=data_fim,
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
        linha_base=linha_base, criticos=CAMPOS_CRITICOS_DISCURSO_SENADO,
    )
    # Senador sem pronunciamento na janela é normal (vazio legítimo), não falha.
    if not bronze and erro_falha is None and erro_instabilidade is None:
        return ResultadoRodadaDiscursosSenado(
            EstadoContrato.OK, "sem discursos na janela", bronze, ResultadoPortao())
    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaDiscursosSenado(contrato.estado, contrato.detalhe, bronze)
    prata = processar_discursos_senado_para_prata(bronze, codigo)
    return ResultadoRodadaDiscursosSenado(contrato.estado, contrato.detalhe, bronze, prata)
