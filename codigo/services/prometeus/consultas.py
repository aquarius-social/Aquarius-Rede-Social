"""As ferramentas do Prometeus: consultas seguras e parametrizadas à camada ouro.

O modelo (Etapa 2.2) escolhe QUAL ferramenta e os PARÂMETROS; a redação da
consulta é fixa aqui (Metodologia §21). Cada ferramenta honra o contrato de
resposta (§20) e foi desenhada para evitar os 12 modos de falha catalogados.

Todas recebem um Gateway injetado — por isso são puras e testáveis sem rede.
Aqui NÃO há IA.
"""
from __future__ import annotations

from typing import Any

from gateway import Consulta, Filtro, Gateway
from resultado import (
    Completude,
    Resultado,
    proveniencia_das_linhas,
    recusar,
)

# --------------------------------------------------------------------------- #
# Ressalvas reutilizadas (texto que o modelo é obrigado a repassar ao usuário)
# --------------------------------------------------------------------------- #

RESSALVA_PARTIDO_HOJE = (
    "Partido, UF e casa retornados são os ATUAIS (vínculo vigente hoje), não "
    "necessariamente os da data de um fato passado — não atribua um voto ou gasto "
    "antigo ao partido de agora (regra 2)."
)

RESSALVA_AUSENCIA = (
    "Ausência de registro no período consultado NÃO significa que o fato não "
    "ocorreu — pode ser defasagem de publicação da fonte (regra 3)."
)

RESSALVA_ESTAGIOS = (
    "Os valores são ESTÁGIOS orçamentários distintos (empenhado, liquidado, pago, "
    "restos). Some apenas dentro de um mesmo estágio; NUNCA some estágios entre si "
    "(regra 5)."
)

RESSALVA_AUTOR_CHAVE = (
    "Atribuição por CHAVE VERIFICADA (autor_profile_id, resolvido na curadoria de "
    "identidade). Autorias de bancada, comissão e relator não têm autor único e "
    "ficam fora desta busca (regra 2)."
)

RESSALVA_AUTOR_NOME = (
    "Atribuição por NOME, não por chave verificada: pode trazer homônimos. A busca "
    "é insensível a acento/caixa, mas grafias divergentes ainda podem escapar. "
    "Quando houver perfil_id, prefira emendas_por_autor_perfil (buscar_parlamentar "
    "resolve o perfil). Grau: com ressalva (regra 2)."
)

RESSALVA_EVENTOS = (
    "Horários em hora de Brasília (sem fuso). O campo 'situacao' distingue "
    "Agendada / Realizada / Cancelada — não confunda agenda com realização (regra 3)."
)

ESTAGIOS = (
    "valor_empenhado",
    "valor_liquidado",
    "valor_pago",
    "valor_resto_inscrito",
    "valor_resto_cancelado",
    "valor_resto_pago",
)


# --------------------------------------------------------------------------- #
# Identidade
# --------------------------------------------------------------------------- #

def buscar_parlamentar(gw: Gateway, *, termo: str) -> Resultado:
    """Encontra parlamentar(es) por nome (ou parte). Perfil resolvido para HOJE."""
    termo = (termo or "").strip()
    if not termo:
        return recusar("Informe um nome (ou parte) de parlamentar para buscar.")
    linhas = gw.buscar(
        Consulta(
            view="parlamentar_publico",
            filtros=[Filtro("nome", "ilike", termo)],
            ordem="nome.asc",
            limite=20,
        )
    )
    return Resultado(
        dados=linhas,
        proveniencia=proveniencia_das_linhas(linhas),
        ressalvas=[RESSALVA_PARTIDO_HOJE] if linhas else [],
    )


def buscar_partido(gw: Gateway, *, termo: str) -> Resultado:
    """Encontra partido(s) por sigla ou nome."""
    termo = (termo or "").strip()
    if not termo:
        return recusar("Informe a sigla ou o nome do partido.")
    linhas = gw.buscar(
        Consulta(
            view="partido_publico",
            filtros=[Filtro("nome", "ilike", termo)],
            ordem="sigla_atual.asc",
            limite=20,
        )
    )
    return Resultado(dados=linhas, proveniencia=proveniencia_das_linhas(linhas))


# --------------------------------------------------------------------------- #
# Despesas (cota parlamentar — CEAP Câmara + CEAPS Senado, mesma view)
# --------------------------------------------------------------------------- #

def despesas_parlamentar(
    gw: Gateway, *, perfil_id: str, ano: int, mes: int | None = None, tipo: str | None = None
) -> Resultado:
    """Lançamentos de cota de um parlamentar num ano (mês/tipo opcionais).

    Exige `ano`: sem janela temporal, a busca devolveria vazio enganoso ou volume
    gigante (modos de falha 1 e 2 da Metodologia).
    """
    if not perfil_id:
        return recusar("Preciso do perfil_id (use buscar_parlamentar antes).")
    if not ano:
        return recusar(
            "Preciso de um ANO (e opcionalmente mês). Despesa sem janela temporal "
            "devolve resultado enganoso — não conclua nada sem o recorte."
        )
    filtros = [Filtro("perfil_id", "eq", perfil_id), Filtro("ano", "eq", int(ano))]
    if mes:
        filtros.append(Filtro("mes", "eq", int(mes)))
    if tipo:
        filtros.append(Filtro("tipo_despesa", "ilike", tipo))
    linhas = gw.buscar(
        Consulta(view="despesa_publica", filtros=filtros, ordem="data_documento.desc")
    )
    ressalvas: list[str] = []
    if not linhas:
        ressalvas.append(RESSALVA_AUSENCIA)
    return Resultado(
        dados=linhas,
        proveniencia=proveniencia_das_linhas(linhas),
        completude=Completude(
            janela_inicio=_inicio_janela(ano, mes),
            janela_fim=_fim_janela(ano, mes),
            ultimo_registro_em=_max_valor(linhas, "data_documento"),
        ),
        ressalvas=ressalvas,
    )


def total_despesas(
    gw: Gateway, *, perfil_id: str, ano: int, mes: int | None = None, por: str | None = None
) -> Resultado:
    """Total de cota (soma de valor_liquido). `por`='categoria'|'fornecedor' agrupa.

    Conta ENTIDADES distintas (fornecedores), não linhas (modo de falha 3).
    """
    base = despesas_parlamentar(gw, perfil_id=perfil_id, ano=ano, mes=mes)
    if base.recusado:
        return base
    linhas: list[dict] = base.dados
    agregado: dict[str, Any] = {
        "total_liquido": round(sum(_num(l.get("valor_liquido")) for l in linhas), 2),
        "n_lancamentos": len(linhas),
        "n_fornecedores_distintos": len(
            {l.get("fornecedor_cnpj_cpf") for l in linhas if l.get("fornecedor_cnpj_cpf")}
        ),
    }
    if por == "categoria":
        agregado["por_categoria"] = _agrupar_soma(linhas, "tipo_despesa", "valor_liquido")
    elif por == "fornecedor":
        agregado["por_fornecedor"] = _agrupar_soma(linhas, "fornecedor_nome", "valor_liquido")
    return Resultado(
        dados=agregado,
        proveniencia=base.proveniencia,
        completude=base.completude,
        ressalvas=base.ressalvas,
    )


# --------------------------------------------------------------------------- #
# Emendas (execução orçamentária — Portal da Transparência)
# --------------------------------------------------------------------------- #

def emendas_por_municipio(
    gw: Gateway, *, municipio: str, uf: str | None = None, ano: int | None = None
) -> Resultado:
    """Emendas destinadas a um município. Totais POR ESTÁGIO (nunca somados entre si)."""
    if not (municipio or "").strip():
        return recusar("Informe o município (e opcionalmente a UF).")
    filtros = [Filtro("localidade_gasto", "ilike", municipio.strip())]
    if uf:
        filtros.append(Filtro("localidade_gasto", "ilike", uf.strip()))
    if ano:
        filtros.append(Filtro("ano", "eq", int(ano)))
    linhas = gw.buscar(Consulta(view="emenda_publica", filtros=filtros, ordem="ano.desc"))
    ressalvas = [RESSALVA_ESTAGIOS] + ([RESSALVA_AUSENCIA] if not linhas else [])
    return Resultado(
        dados={"emendas": linhas, "totais_por_estagio": _totais_estagios(linhas)},
        proveniencia=proveniencia_das_linhas(linhas),
        completude=Completude(
            janela_inicio=(f"{int(ano):04d}-01-01" if ano else None),
            janela_fim=(f"{int(ano):04d}-12-31" if ano else None),
        ),
        ressalvas=ressalvas,
    )


def emendas_por_autor_perfil(
    gw: Gateway, *, perfil_id: str, ano: int | None = None
) -> Resultado:
    """Emendas de um autor por CHAVE VERIFICADA (autor_profile_id). Use o perfil_id
    vindo de buscar_parlamentar — atribuição sem ambiguidade de nome."""
    if not (perfil_id or "").strip():
        return recusar("Informe o perfil_id do autor (use buscar_parlamentar antes).")
    filtros = [Filtro("autor_profile_id", "eq", perfil_id.strip())]
    if ano:
        filtros.append(Filtro("ano", "eq", int(ano)))
    linhas = gw.buscar(Consulta(view="emenda_publica", filtros=filtros, ordem="ano.desc"))
    ressalvas = [RESSALVA_AUTOR_CHAVE, RESSALVA_ESTAGIOS]
    if not linhas:
        ressalvas.append(RESSALVA_AUSENCIA)
    return Resultado(
        dados={"emendas": linhas, "totais_por_estagio": _totais_estagios(linhas)},
        proveniencia=proveniencia_das_linhas(linhas),
        ressalvas=ressalvas,
    )


def emendas_por_autor_nome(
    gw: Gateway, *, nome: str, ano: int | None = None
) -> Resultado:
    """Emendas de um autor casadas por NOME (fallback, com ressalva). Insensível a
    acento/caixa (casa sobre `autor_nome_norm`). Prefira emendas_por_autor_perfil
    quando houver perfil_id."""
    if not (nome or "").strip():
        return recusar("Informe o nome do autor da emenda.")
    filtros = [Filtro("autor_nome_norm", "ilike", _sem_acento(nome.strip()))]
    if ano:
        filtros.append(Filtro("ano", "eq", int(ano)))
    linhas = gw.buscar(Consulta(view="emenda_publica", filtros=filtros, ordem="ano.desc"))
    ressalvas = [RESSALVA_AUTOR_NOME, RESSALVA_ESTAGIOS]
    if not linhas:
        ressalvas.append(RESSALVA_AUSENCIA)
    return Resultado(
        dados={"emendas": linhas, "totais_por_estagio": _totais_estagios(linhas)},
        proveniencia=proveniencia_das_linhas(linhas),
        ressalvas=ressalvas,
    )


# --------------------------------------------------------------------------- #
# Eventos (agenda legislativa bicameral)
# --------------------------------------------------------------------------- #

def agenda_eventos(
    gw: Gateway,
    *,
    data_inicio: str,
    data_fim: str,
    casa: str | None = None,
    situacao: str | None = None,
) -> Resultado:
    """Agenda legislativa num intervalo (AAAA-MM-DD). casa='camara'|'senado'."""
    if not data_inicio or not data_fim:
        return recusar("Informe data_inicio e data_fim (AAAA-MM-DD) para a agenda.")
    filtros = [
        Filtro("data_hora_inicio", "gte", data_inicio),
        Filtro("data_hora_inicio", "lte", f"{data_fim}T23:59:59"),
    ]
    if casa:
        filtros.append(Filtro("casa", "eq", casa))
    if situacao:
        filtros.append(Filtro("situacao", "eq", situacao))
    linhas = gw.buscar(
        Consulta(view="evento_publico", filtros=filtros, ordem="data_hora_inicio.asc")
    )
    return Resultado(
        dados=linhas,
        proveniencia=proveniencia_das_linhas(linhas),
        completude=Completude(janela_inicio=data_inicio, janela_fim=data_fim),
        ressalvas=[RESSALVA_EVENTOS],
    )


# --------------------------------------------------------------------------- #
# Auxiliares
# --------------------------------------------------------------------------- #

def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


# Espelha `autor_nome_norm` da view (migration 0016): minúsculas + sem acento via
# translate. Manter as duas pontas idênticas — senão a busca por nome fura.
_ACENTOS_DE = "áàâãäéèêëíìîïóòôõöúùûüç"
_ACENTOS_PARA = "aaaaaeeeeiiiiooooouuuuc"
_TABELA_ACENTOS = str.maketrans(_ACENTOS_DE, _ACENTOS_PARA)


def _sem_acento(s: Any) -> str:
    return str(s or "").lower().translate(_TABELA_ACENTOS)


def _max_valor(linhas: list[dict], coluna: str) -> str | None:
    valores = [l.get(coluna) for l in linhas if l.get(coluna)]
    return max(valores) if valores else None


def _agrupar_soma(linhas: list[dict], chave: str, valor: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for l in linhas:
        k = l.get(chave) or "(sem)"
        out[k] = round(out.get(k, 0.0) + _num(l.get(valor)), 2)
    return dict(sorted(out.items(), key=lambda kv: kv[1], reverse=True))


def _totais_estagios(linhas: list[dict]) -> dict[str, float]:
    # Cada estágio somado SÓ dentro de si mesmo. Não existe "total" único (§13).
    return {e: round(sum(_num(l.get(e)) for l in linhas), 2) for e in ESTAGIOS}


def _inicio_janela(ano: int, mes: int | None = None) -> str:
    return f"{int(ano):04d}-{int(mes):02d}-01" if mes else f"{int(ano):04d}-01-01"


def _fim_janela(ano: int, mes: int | None = None) -> str:
    # Limite grosseiro (dia 31) — suficiente como rótulo de janela.
    return f"{int(ano):04d}-{int(mes):02d}-31" if mes else f"{int(ano):04d}-12-31"
