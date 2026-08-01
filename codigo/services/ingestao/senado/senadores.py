"""Coletor do Senado — senadores em exercício (perfis parlamentares, Área I).

Fonte: Dados Abertos do Senado Federal
    https://legis.senado.leg.br/dadosabertos/senador/lista/atual   (lista)
    https://legis.senado.leg.br/dadosabertos/senador/{codigo}      (detalhe)
A API entrega XML por padrão; o header `Accept: application/json` devolve JSON
(verificado ao vivo em 2026-07-31: lista com 81 senadores em exercício).

DIFERENÇA CENTRAL EM RELAÇÃO À CÂMARA (§13, Resolução de Entidade):
  - O Senado NÃO expõe CPF. A ligação de UM senador ao SEU código do Senado é
    direta (a fonte declara `CodigoParlamentar`), mas dizer que este senador é a
    MESMA PESSOA que um ex-deputado é match probabilístico (Tier 2): nome civil +
    nascimento + naturalidade. Isso NÃO é feito aqui — é a junção bicameral (§17),
    no `resolucao/bicameral.py`, aplicada na persistência.
  - A lista já traz o nome civil (`NomeCompletoParlamentar`); nascimento e
    naturalidade vêm no DETALHE (`DadosBasicosParlamentar`), sinais §5.3.

Estrutura verificada da fonte viva:
  lista:    ListaParlamentarEmExercicio.Parlamentares.Parlamentar[]
              cada um: {IdentificacaoParlamentar{...}, Mandato{...}}
  detalhe:  DetalheParlamentar.Parlamentar.DadosBasicosParlamentar{DataNascimento,
              Naturalidade, UfNaturalidade}
"""

from __future__ import annotations

import unicodedata
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

FONTE = "senado.senadores"
BASE = "https://legis.senado.leg.br/dadosabertos"

# Campos críticos da IdentificacaoParlamentar (§19). Verificado ao vivo em
# 2026-07-31: todos presentes. Se algum sumir, é QUEBRA.
CAMPOS_CRITICOS_SENADOR = frozenset({
    "CodigoParlamentar", "NomeParlamentar", "SiglaPartidoParlamentar",
    "UfParlamentar",
})


# -----------------------------------------------------------------------------
# Coleta — bronze
# -----------------------------------------------------------------------------

def _como_lista(v: Any) -> list:
    """XML→JSON entrega um único filho como objeto, vários como lista. Normaliza
    para lista sempre (defesa contra o Senado com um só parlamentar num nó)."""
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def coletar_bronze_senadores(
    cliente: ClienteHttp,
    *,
    politica: PoliticaRetry = PoliticaRetry(),
) -> list[RegistroBronze]:
    """Lista os senadores em exercício. Um bronze por `Parlamentar` (dict CRU da
    fonte: preserva `IdentificacaoParlamentar` + `Mandato` sem achatar, §3.1).

    Sem paginação: a fonte devolve todos os em exercício numa resposta.
    """
    url = f"{BASE}/senador/lista/atual"
    corpo = obter_com_retry(cliente, url, politica=politica)
    lista = (((corpo or {}).get("ListaParlamentarEmExercicio") or {})
             .get("Parlamentares") or {})
    bronze: list[RegistroBronze] = []
    for item in _como_lista(lista.get("Parlamentar")):
        bronze.append(RegistroBronze.de(FONTE, url, item))
    return bronze


def coletar_detalhe_senador(
    cliente: ClienteHttp,
    codigo: str,
    *,
    politica: PoliticaRetry = PoliticaRetry(),
) -> RegistroBronze:
    """Detalhe de UM senador (GET /senador/{codigo}).

    Traz `DadosBasicosParlamentar` (nascimento, naturalidade) — os sinais §5.3
    que a lista não tem e que a junção bicameral (§17) exige. O `dados` é objeto.
    """
    url = f"{BASE}/senador/{codigo}"
    corpo = obter_com_retry(cliente, url, politica=politica)
    dado = (((corpo or {}).get("DetalheParlamentar") or {})
            .get("Parlamentar") or {})
    return RegistroBronze.de(FONTE, url, dado)


# -----------------------------------------------------------------------------
# Transformação — bronze → prata (perfil + vínculo id_externo + mandato_hint)
# -----------------------------------------------------------------------------

def _slug(nome: str, id_fonte: str) -> str:
    """Slug estável e único. Nome sozinho colide (homonímia, §6.2); o código do
    Senado desambigua — mesmo papel do sufixo geracional."""
    base = unicodedata.normalize("NFKD", nome or "")
    base = base.encode("ascii", "ignore").decode("ascii").lower()
    limpo = "".join(c if c.isalnum() else "-" for c in base)
    limpo = "-".join(p for p in limpo.split("-") if p)
    return f"{limpo}-sen-{id_fonte}" if limpo else f"sen-{id_fonte}"


def _data(valor: Any) -> str | None:
    """Trunca para DATE (YYYY-MM-DD). O Senado já entrega assim, mas defende."""
    if not valor:
        return None
    return str(valor)[:10]


def _ocupacao(descricao: str | None) -> str:
    """Mapeia a `DescricaoParticipacao` do Senado para o enum `ocupacao_cadeira`.
    A lista é de quem está EM EXERCÍCIO, então suplente aqui é em exercício."""
    d = (descricao or "").lower()
    if "suplente" in d:
        return "suplente_em_exercicio"
    return "titular"


def transformar_senador(item: dict, detalhe: dict | None = None) -> dict:
    """Normaliza um `Parlamentar` da lista (+ detalhe opcional) para a prata.

    Produz a identidade ESTÁVEL do perfil + o vínculo direto para `id_externo`
    (sistema='senado': a fonte declarou o código) + `mandato_hint` com o mandato
    vigente (partido/UF/legislatura/vigência), que é TEMPORAL e vai para
    `vinculo_temporal`, jamais como atributo atemporal do perfil (§4/§12).

    Sem `detalhe`, nascimento e naturalidade ficam None — passe só-lista, honesto.
    """
    ident = item.get("IdentificacaoParlamentar") or {}
    mand = item.get("Mandato") or {}
    det = detalhe or {}
    basicos = det.get("DadosBasicosParlamentar") or {}

    id_fonte = str(ident.get("CodigoParlamentar") or "") or None
    nome = ident.get("NomeParlamentar")

    prim = mand.get("PrimeiraLegislaturaDoMandato") or {}
    seg = mand.get("SegundaLegislaturaDoMandato") or {}
    # A vigência do mandato de 8 anos cobre as duas legislaturas quando há a
    # segunda; o fim vem da segunda, senão da primeira.
    vig_fim = seg.get("DataFim") or prim.get("DataFim")
    legislatura = prim.get("NumeroLegislatura")

    return {
        "id_fonte": id_fonte,
        "tipo": "parlamentar",
        "nome": nome,
        "slug": _slug(nome, id_fonte) if nome and id_fonte else None,
        "foto_url": ident.get("UrlFotoParlamentar"),
        "ativo": True,
        # Pessoa natural (do detalhe) — PII restrita à resolução (§3.5), §5.3.
        "nome_civil": ident.get("NomeCompletoParlamentar"),
        "data_nascimento": _data(basicos.get("DataNascimento")),
        "naturalidade_municipio": basicos.get("Naturalidade"),
        "naturalidade_uf": basicos.get("UfNaturalidade"),
        # Vínculo → id_externo (§6): a fonte declarou o código, ligação direta.
        "sistema_externo": "senado",
        "identificador_externo": id_fonte,
        "metodo_ligacao": "fonte_direta",
        "grau": "direto",
        # Pista temporal — mandato vigente. Vai para vinculo_temporal (casa=senado).
        "mandato_hint": {
            "casa": "senado",
            "uf": ident.get("UfParlamentar"),
            "partido": ident.get("SiglaPartidoParlamentar"),
            "legislatura": int(legislatura) if legislatura else None,
            "vigencia_inicio": prim.get("DataInicio"),
            "vigencia_fim": vig_fim,
            "ocupacao": _ocupacao(mand.get("DescricaoParticipacao")),
        },
    }


def _ligacao_coerente(registro: dict) -> Violacao | None:
    """Mesma regra do portão de deputados: grau 'direto' declarado pela fonte
    exige método 'fonte_direta'. (A junção bicameral, quando reusa um perfil
    existente, grava método 'convergencia' com ≥2 sinais — isso é na persistência,
    não neste registro, que descreve só o vínculo senado→código próprio.)"""
    if registro.get("grau") == "direto" and \
            registro.get("metodo_ligacao") not in ("fonte_direta", "conferencia_humana"):
        return Violacao(
            "integridade_referencial",
            "grau 'direto' exige método 'fonte_direta' ou 'conferencia_humana'",
        )
    return None


VERIFICADORES_SENADOR = [
    campo_obrigatorio("id_fonte"),
    campo_obrigatorio("nome"),
    campo_obrigatorio("slug"),
    campo_obrigatorio("identificador_externo"),
    _ligacao_coerente,
]


def processar_senadores_para_prata(
    bronze: list[RegistroBronze],
    detalhes: dict[str, dict] | None = None,
) -> ResultadoPortao:
    """Portão bronze → prata. `detalhes` mapeia código do Senado → payload do
    detalhe, para o enriquecimento §5.3. Sem detalhe, entra sem nascimento."""
    det = detalhes or {}

    def _transformar(item: dict) -> dict:
        ident = item.get("IdentificacaoParlamentar") or {}
        cod = str(ident.get("CodigoParlamentar") or "")
        return transformar_senador(item, det.get(cod))

    return portao_bronze_prata(
        bronze, transformar=_transformar, verificadores=VERIFICADORES_SENADOR)


# -----------------------------------------------------------------------------
# Rodada completa com teste de contrato
# -----------------------------------------------------------------------------

@dataclass
class ResultadoRodadaSenadores:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    prata: ResultadoPortao | None = None


def rodada_senadores(
    cliente: ClienteHttp,
    *,
    canario_validado: bool,
    linha_base: frozenset[str] | None,
    enriquecer: bool = True,
    politica: PoliticaRetry = PoliticaRetry(),
) -> ResultadoRodadaSenadores:
    """Uma rodada: lista, avalia o contrato (sobre a IdentificacaoParlamentar da
    amostra), enriquece com o detalhe e passa o portão.

    Em FALHA/QUEBRA a prata é pulada (§19). Falha pontual do detalhe de um
    senador não derruba a rodada — aquele entra sem nascimento.
    """
    erro_falha: str | None = None
    erro_instabilidade: str | None = None
    bronze: list[RegistroBronze] = []

    try:
        bronze = coletar_bronze_senadores(cliente, politica=politica)
    except ErroFalha as e:
        erro_falha = str(e)
    except ErroInstabilidade as e:
        erro_instabilidade = str(e)

    # O contrato mede a IdentificacaoParlamentar (onde vivem os campos críticos),
    # não o Parlamentar cru (cujas chaves de topo seriam só dois contêineres).
    amostra = None
    if bronze:
        amostra = bronze[0].payload.get("IdentificacaoParlamentar")
    contrato = avaliar(
        canario_validado=canario_validado,
        resposta=[amostra] if amostra is not None else None,
        erro_falha=erro_falha,
        erro_instabilidade=erro_instabilidade,
        linha_base=linha_base,
        criticos=CAMPOS_CRITICOS_SENADOR,
    )

    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaSenadores(contrato.estado, contrato.detalhe, bronze)

    if not bronze:
        return ResultadoRodadaSenadores(
            contrato.estado, contrato.detalhe, bronze, ResultadoPortao())

    detalhes: dict[str, dict] = {}
    if enriquecer:
        for reg in bronze:
            ident = reg.payload.get("IdentificacaoParlamentar") or {}
            cod = str(ident.get("CodigoParlamentar") or "")
            if not cod:
                continue
            try:
                det = coletar_detalhe_senador(cliente, cod, politica=politica)
                detalhes[cod] = det.payload
            except (ErroFalha, ErroInstabilidade):
                continue  # falha pontual do detalhe — segue sem PII

    prata = processar_senadores_para_prata(bronze, detalhes)
    return ResultadoRodadaSenadores(contrato.estado, contrato.detalhe, bronze, prata)
