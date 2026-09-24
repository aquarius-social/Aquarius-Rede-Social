"""Coletor do Senado — matérias legislativas (proposições, Área B, bicameral).

Fonte: https://legis.senado.leg.br/dadosabertos/materia/pesquisa/lista
Aceita janela de apresentação (`dataInicioApresentacao`/`dataFimApresentacao`,
YYYYMMDD) + `sigla` — a MESMA janela móvel (§3.3) do coletor de proposições da
Câmara. Verificado ao vivo em 2026-07-31 (PL 2024 = 901 matérias; janela de 10
dias de jun/2024 = 12 PLs).

Produz a MESMA prata que `camara/proposicoes.py` (com `casa_origem='senado'`),
então reusa `salvar_proposicoes` sem alteração — a tabela `proposicao` já é
bicameral (`casa_origem`, migration 0002, §17).

Escopo de tipos: só os tipos que o produto já modela (enum `proposicao_tipo`:
PL/PEC/PLP/PDL). O Senado publica muitos outros (RQS, MSF, OFS — procedurais);
ampliar o enum é decisão de escopo (não ausência técnica), então esses ficam de
fora por ora, honestamente — não entram como lixo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contrato.canario import EstadoContrato, avaliar
from pipeline.camadas import (
    RegistroBronze,
    ResultadoPortao,
    Violacao,
    campo_em,
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

FONTE = "senado.materias"
BASE = "https://legis.senado.leg.br/dadosabertos"

# Tipos que o modelo suporta (enum proposicao_tipo). Subconjunto legislativo
# compartilhado entre as casas; MP (MPV no Senado) é origem do Executivo e fica
# fora deste passe. Ampliar exige decisão de produto (mesma regra da Câmara).
TIPOS_SUPORTADOS = ("PL", "PEC", "PLP", "PDL")

CAMPOS_CRITICOS_MATERIA = frozenset({
    "Codigo", "Sigla", "Numero", "Ano", "Ementa", "Data",
})


def _como_lista(v: Any) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _aaaammdd(iso: str) -> str:
    """A fonte quer YYYYMMDD (sem hífens). Aceita ISO ou já-compacto."""
    return str(iso).replace("-", "")


def coletar_bronze_materias(
    cliente: ClienteHttp,
    *,
    data_inicio: str,
    data_fim: str,
    siglas: tuple[str, ...] = TIPOS_SUPORTADOS,
    politica: PoliticaRetry = PoliticaRetry(),
) -> list[RegistroBronze]:
    """Matérias apresentadas na janela [data_inicio, data_fim], uma consulta por
    sigla suportada. A fonte devolve tudo numa resposta por sigla (sem link)."""
    url = f"{BASE}/materia/pesquisa/lista"
    bronze: list[RegistroBronze] = []
    for sigla in siglas:
        corpo = obter_com_retry(
            cliente, url,
            params={
                "dataInicioApresentacao": _aaaammdd(data_inicio),
                "dataFimApresentacao": _aaaammdd(data_fim),
                "sigla": sigla,
            },
            politica=politica)
        pb = (corpo or {}).get("PesquisaBasicaMateria") or {}
        mats = (pb.get("Materias") or {})
        for item in _como_lista(mats.get("Materia")):
            bronze.append(RegistroBronze.de(FONTE, url, item))
    return bronze


def _int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _limpar_texto_livre(v: Any) -> str | None:
    """Remove separadores CSV e quebras internas (a ementa da fonte traz `;`,
    `\\n`, `\\r`). Não altera caso nem acento (§3.2). Mesmo tratamento da Câmara."""
    if v is None:
        return None
    texto = str(v).replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    texto = texto.replace(";", ",")
    texto = " ".join(texto.split())
    return texto or None


def _achar_primeiro(obj: Any, chave: str) -> str | None:
    """Primeiro valor string de `chave` em qualquer nível — robusto à estrutura
    aninhada (Situacao pode vir lista ou dict conforme a matéria)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == chave and isinstance(v, str) and v.strip():
                return v
            achado = _achar_primeiro(v, chave)
            if achado is not None:
                return achado
    elif isinstance(obj, list):
        for x in obj:
            achado = _achar_primeiro(x, chave)
            if achado is not None:
                return achado
    return None


def extrair_enriquecimento_materia(detalhe: dict, situacao_atual: dict) -> dict:
    """Do DETALHE (`/materia/{codigo}`) e da SITUAÇÃO ATUAL
    (`/materia/situacaoatual/{codigo}`), os campos que a pesquisa-lista não traz:
    `situacao` (`DescricaoSituacao`) e `tema` (`IndexacaoMateria`). Ausente vira
    None (§1). Espelha o enriquecimento de proposição da Câmara, `casa='senado'`."""
    mat = (detalhe.get("DetalheMateria") or {}).get("Materia") or {}
    db = mat.get("DadosBasicosMateria") or {}
    return {
        "situacao": _achar_primeiro(situacao_atual, "DescricaoSituacao"),
        "tema": _limpar_texto_livre(db.get("IndexacaoMateria")),
    }


def transformar_materia(payload: dict) -> dict:
    sigla = payload.get("Sigla")
    numero = _int(payload.get("Numero"))
    ano = _int(payload.get("Ano"))
    ident = payload.get("DescricaoIdentificacao")
    if not ident and sigla and numero is not None and ano is not None:
        ident = f"{sigla} {numero}/{ano}"
    return {
        "id_fonte": str(payload.get("Codigo") or "") or None,
        "tipo": sigla,
        "numero": numero,
        "ano": ano,
        "identificador": ident,
        "ementa": _limpar_texto_livre(payload.get("Ementa")),
        "data_apresentacao": payload.get("Data"),
        # situação vem no DETALHE da matéria (passe futuro); ausente aqui.
        "situacao": None,
        "uri_autores": None,
        "casa_origem": "senado",
        # Id do PROCESSO (≠ Codigo da matéria) — chave do endpoint /processo/{id}
        # que traz a tramitação. NÃO é persistido (salvar_proposicoes ignora); o
        # orquestrador o usa para o passo de tramitações do Senado.
        "id_processo": str(payload.get("IdentificacaoProcesso") or "") or None,
    }


def _numero_ano_positivos(registro: dict) -> Violacao | None:
    for campo in ("numero", "ano"):
        v = registro.get(campo)
        if v is None or (isinstance(v, int) and v <= 0):
            return Violacao("precisao", f"{campo} inválido: {v!r}")
    return None


VERIFICADORES_MATERIA = [
    campo_obrigatorio("id_fonte"),
    campo_obrigatorio("tipo"),
    campo_em("tipo", set(TIPOS_SUPORTADOS)),
    campo_obrigatorio("ementa"),
    campo_obrigatorio("data_apresentacao"),
    _numero_ano_positivos,
]


def processar_materias_para_prata(bronze: list[RegistroBronze]) -> ResultadoPortao:
    return portao_bronze_prata(
        bronze, transformar=transformar_materia, verificadores=VERIFICADORES_MATERIA)


@dataclass
class ResultadoRodadaMaterias:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    prata: ResultadoPortao | None = None


def rodada_materias(
    cliente: ClienteHttp,
    *,
    data_inicio: str,
    data_fim: str,
    canario_validado: bool,
    linha_base: frozenset[str] | None,
    siglas: tuple[str, ...] = TIPOS_SUPORTADOS,
    politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodadaMaterias:
    erro_falha: str | None = None
    erro_instabilidade: str | None = None
    bronze: list[RegistroBronze] = []
    try:
        bronze = coletar_bronze_materias(
            cliente, data_inicio=data_inicio, data_fim=data_fim,
            siglas=siglas, politica=politica)
    except ErroFalha as e:
        erro_falha = str(e)
    except ErroInstabilidade as e:
        erro_instabilidade = str(e)

    amostra = bronze[0].payload if bronze else None
    contrato = avaliar(
        canario_validado=canario_validado,
        resposta=[amostra] if amostra is not None else None,
        erro_falha=erro_falha, erro_instabilidade=erro_instabilidade,
        linha_base=linha_base, criticos=CAMPOS_CRITICOS_MATERIA,
    )
    # Janela sem matéria nova (recesso) é vazio legítimo, não FALHA de contrato.
    if not bronze and erro_falha is None and erro_instabilidade is None:
        return ResultadoRodadaMaterias(
            EstadoContrato.OK, "sem matérias na janela", bronze, ResultadoPortao())
    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaMaterias(contrato.estado, contrato.detalhe, bronze)
    prata = processar_materias_para_prata(bronze)
    return ResultadoRodadaMaterias(contrato.estado, contrato.detalhe, bronze, prata)
