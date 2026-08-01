"""Coletor do Senado — votações + votos nominais (Área C, §10/§5.2, bicameral).

Fonte: https://legis.senado.leg.br/dadosabertos/votacao?dataInicio&dataFim
ATENÇÃO (§19): o endpoint antigo `/materia/votacoes/{codigo}` foi DESCONTINUADO
(desativação 2026-02-01) e a fonte aponta `/votacao` como substituto — usamos o
substituto. Verificado ao vivo em 2026-08-01 (jan/dez 2024: 27 votações).

Diferença em relação à Câmara: aqui o placar (`totalVotosSim/Nao/Abstencao`) e
os votos nominais (`votos[]`) vêm INLINE e estruturados — não é preciso parsear
o texto da descrição (a reforma V1–V4 da Câmara foi por causa disso). O trabalho
é mapear a sigla de voto do Senado para o enum `voto_tipo` e resolver o perfil.

Disciplinas honradas:
  - §10 voto secreto NÃO tem nominal: quando `votacaoSecreta='S'` a posição de
    cada um vem como 'Votou' (oculta) — a votação é gravada com `secreta=true` e
    NENHUM voto_nominal é inserido (o schema exige isso).
  - §5.2 reconciliação: para votação aberta, a contagem dos nominais por posição
    é conferida contra o placar oficial; divergência é reportada (não fabrica).
  - Presidência (art. 51 RISF) não é posição de voto — não entra (como o
    'Artigo 17' da Câmara).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

# Reusa o alvo de persistência de voto (mesma tabela voto_nominal).
from camara.votacoes import VotoNominalResolvido
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

FONTE = "senado.votacoes"
BASE = "https://legis.senado.leg.br/dadosabertos"

CAMPOS_CRITICOS_VOTACAO_SENADO = frozenset({
    "codigoSessaoVotacao", "dataSessao", "descricaoVotacao", "resultadoVotacao",
})

# Sigla de voto do Senado → enum `voto_tipo`. Posições concretas + ausências.
_POSICOES = {
    "sim": "sim", "não": "nao", "nao": "nao",
    "abstenção": "abstencao", "abstencao": "abstencao",
    "obstrução": "obstrucao", "obstrucao": "obstrucao",
}
# Modalidades de ausência/afastamento — todas viram 'ausente' (não votaram).
_AUSENCIAS = {
    "ap",      # Atividade parlamentar
    "ls",      # Licença saúde
    "la",      # Licença
    "lp",      # Licença particular
    "ncom",    # Não compareceu
    "mis",     # Missão
    "p-nrv",   # Presente, não registrou voto
    "lg",      # Licença gestante/paternidade
    "lsp",
}
# NÃO são posição: 'Votou' (secreto, oculto) e a presidência.
_NAO_POSICAO_PREFIXOS = ("presidente",)
_SECRETO_LABEL = "votou"

_RESULTADO = {"A": "Aprovada", "R": "Rejeitada", "P": "Prejudicada",
              "RQV": "Requerimento", "T": "Retirada"}


def _como_lista(v: Any) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _aaaa_mm_dd(iso: str) -> str:
    """A fonte /votacao aceita YYYY-MM-DD (com hífen, diferente de /processo)."""
    return str(iso)


def coletar_bronze_votacoes_senado(
    cliente: ClienteHttp,
    *,
    data_inicio: str,
    data_fim: str,
    politica: PoliticaRetry = PoliticaRetry(),
) -> list[RegistroBronze]:
    """Votações na janela [data_inicio, data_fim] (YYYY-MM-DD). A fonte devolve
    uma LISTA de votações, cada uma com placar e votos inline."""
    url = f"{BASE}/votacao"
    corpo = obter_com_retry(
        cliente, url,
        params={"dataInicio": _aaaa_mm_dd(data_inicio), "dataFim": _aaaa_mm_dd(data_fim)},
        politica=politica)
    lista = corpo if isinstance(corpo, list) else _como_lista(corpo)
    return [RegistroBronze.de(FONTE, url, v) for v in lista]


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


def _mapear_voto(sigla: Any) -> str | None:
    """Sigla do Senado → enum. None quando NÃO é posição (secreto 'Votou',
    presidência) ou sigla desconhecida — nesses casos não se grava nominal."""
    s = (str(sigla or "")).strip()
    sl = s.lower()
    if sl in _POSICOES:
        return _POSICOES[sl]
    if sl in _AUSENCIAS:
        return "ausente"
    return None


def _resultado(codigo: Any) -> str | None:
    if codigo is None:
        return None
    return _RESULTADO.get(str(codigo).strip(), str(codigo).strip()) or None


def transformar_votacao_senado(payload: dict) -> dict:
    secreta = str(payload.get("votacaoSecreta") or "").upper() == "S"
    return {
        "casa": "senado",
        "id_fonte": str(payload.get("codigoSessaoVotacao") or "") or None,
        "proposicao_id_fonte": str(payload.get("codigoMateria") or "") or None,
        "titulo": _texto(payload.get("descricaoVotacao")) or payload.get("identificacao"),
        "data_hora": payload.get("dataSessao"),
        "resultado": _resultado(payload.get("resultadoVotacao")),
        "sim": _int(payload.get("totalVotosSim")),
        "nao": _int(payload.get("totalVotosNao")),
        "abstencao": _int(payload.get("totalVotosAbstencao")),
        "secreta": secreta,
        "nominal": (not secreta) and bool(payload.get("votos")),
    }


VERIFICADORES_VOTACAO_SENADO = [
    campo_obrigatorio("id_fonte"),
    campo_obrigatorio("titulo"),
    campo_obrigatorio("data_hora"),
    campo_obrigatorio("resultado"),
]


def processar_votacoes_senado_para_prata(bronze: list[RegistroBronze]) -> ResultadoPortao:
    return portao_bronze_prata(
        bronze, transformar=transformar_votacao_senado,
        verificadores=VERIFICADORES_VOTACAO_SENADO)


def _reconciliar_placar(payload: dict) -> str | None:
    """§5.2: a contagem dos nominais por posição bate com o placar oficial?
    Só para votação ABERTA (a secreta não expõe posições)."""
    contagem = {"sim": 0, "nao": 0, "abstencao": 0}
    for voto in _como_lista(payload.get("votos")):
        t = _mapear_voto(voto.get("siglaVotoParlamentar"))
        if t in contagem:
            contagem[t] += 1
    alvo = {"sim": _int(payload.get("totalVotosSim")),
            "nao": _int(payload.get("totalVotosNao")),
            "abstencao": _int(payload.get("totalVotosAbstencao"))}
    difs = [f"{k}: nominais {contagem[k]} != placar {alvo[k]}"
            for k in contagem if alvo[k] is not None and contagem[k] != alvo[k]]
    return "; ".join(difs) or None


def _resolver_nominais(
    payload: dict, lookup: Callable[[str, str], str | None]
) -> list[VotoNominalResolvido]:
    """Resolve os votos nominais de UMA votação aberta a perfis (por id_externo
    sistema='senado'). Secreto/presidência/ausência-de-perfil não entram."""
    idf = str(payload.get("codigoSessaoVotacao") or "")
    resolvidos: list[VotoNominalResolvido] = []
    for voto in _como_lista(payload.get("votos")):
        tipo = _mapear_voto(voto.get("siglaVotoParlamentar"))
        if tipo is None:
            continue
        cod = str(voto.get("codigoParlamentar") or "")
        perfil_id = lookup("senado", cod)
        if perfil_id is None:
            continue  # senador não ingerido — não inventa (§6)
        resolvidos.append(VotoNominalResolvido(
            votacao_id_fonte=idf,
            perfil_id=perfil_id,
            voto=tipo,
            modalidade_fonte=str(voto.get("siglaVotoParlamentar") or ""),
            partido_sigla_na_epoca=voto.get("siglaPartidoParlamentar"),
        ))
    return resolvidos


@dataclass
class ResultadoRodadaVotacoesSenado:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    votacoes_prata: ResultadoPortao | None = None
    nominais: dict[str, list[VotoNominalResolvido]] = field(default_factory=dict)
    placar_violacoes: dict[str, str] = field(default_factory=dict)


def rodada_votacoes_senado(
    cliente: ClienteHttp,
    *,
    data_inicio: str,
    data_fim: str,
    canario_validado: bool,
    linha_base: frozenset[str] | None,
    lookup: Callable[[str, str], str | None],
    politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodadaVotacoesSenado:
    erro_falha: str | None = None
    erro_instabilidade: str | None = None
    bronze: list[RegistroBronze] = []
    try:
        bronze = coletar_bronze_votacoes_senado(
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
        linha_base=linha_base, criticos=CAMPOS_CRITICOS_VOTACAO_SENADO,
    )
    # Janela sem votação (recesso) é vazio legítimo.
    if not bronze and erro_falha is None and erro_instabilidade is None:
        return ResultadoRodadaVotacoesSenado(
            EstadoContrato.OK, "sem votações na janela", bronze, ResultadoPortao())
    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaVotacoesSenado(contrato.estado, contrato.detalhe, bronze)

    votacoes_prata = processar_votacoes_senado_para_prata(bronze)
    nominais: dict[str, list[VotoNominalResolvido]] = {}
    placar_violacoes: dict[str, str] = {}
    for b in bronze:
        p = b.payload
        idf = str(p.get("codigoSessaoVotacao") or "")
        if str(p.get("votacaoSecreta") or "").upper() == "S":
            nominais[idf] = []       # §10: secreta não tem nominal
            continue
        nominais[idf] = _resolver_nominais(p, lookup)
        viol = _reconciliar_placar(p)
        if viol:
            placar_violacoes[idf] = viol
    return ResultadoRodadaVotacoesSenado(
        contrato.estado, contrato.detalhe, bronze,
        votacoes_prata, nominais, placar_violacoes)
