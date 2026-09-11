"""Registro das ferramentas do agente: esquema (para o modelo) + executor.

É a mesma leva de consultas que o servidor MCP expõe — a lógica vive em
`consultas.py`. O agente (`agente.py`) lê os esquemas daqui e despacha as chamadas
por `executar()`. Fonte única de nome/descrição/parâmetros das ferramentas.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import consultas
from gateway import Gateway
from resultado import Resultado

Executor = Callable[[Gateway, dict], Resultado]


@dataclass(frozen=True)
class Ferramenta:
    nome: str
    descricao: str
    propriedades: dict[str, dict]
    obrigatorios: list[str]
    executor: Executor


def _s(tipo: str, descricao: str) -> dict:
    return {"type": tipo, "description": descricao}


FERRAMENTAS: list[Ferramenta] = [
    Ferramenta(
        "buscar_parlamentar",
        "Encontra parlamentar(es) por nome ou parte do nome. Devolve o perfil ATUAL "
        "(partido/UF/casa de hoje). Use antes de consultar despesas, para obter o perfil_id.",
        {"termo": _s("string", "Nome ou parte do nome do parlamentar.")},
        ["termo"],
        lambda gw, a: consultas.buscar_parlamentar(gw, termo=a.get("termo", "")),
    ),
    Ferramenta(
        "buscar_partido",
        "Encontra partido(s) por sigla ou nome.",
        {"termo": _s("string", "Sigla ou nome do partido.")},
        ["termo"],
        lambda gw, a: consultas.buscar_partido(gw, termo=a.get("termo", "")),
    ),
    Ferramenta(
        "despesas_parlamentar",
        "Lançamentos de cota parlamentar (CEAP Câmara / CEAPS Senado) de um parlamentar. "
        "EXIGE ano. Use o perfil_id vindo de buscar_parlamentar.",
        {
            "perfil_id": _s("string", "id do parlamentar (de buscar_parlamentar)."),
            "ano": _s("integer", "Ano (obrigatório)."),
            "mes": _s("integer", "Mês 1-12 (opcional)."),
            "tipo": _s("string", "Tipo de despesa (opcional)."),
        },
        ["perfil_id", "ano"],
        lambda gw, a: consultas.despesas_parlamentar(
            gw, perfil_id=a.get("perfil_id"), ano=a.get("ano"), mes=a.get("mes"), tipo=a.get("tipo")
        ),
    ),
    Ferramenta(
        "total_despesas",
        "Total de cota (soma de valor_liquido) de um parlamentar num ano. "
        "por='categoria'|'fornecedor' agrupa. EXIGE ano.",
        {
            "perfil_id": _s("string", "id do parlamentar."),
            "ano": _s("integer", "Ano (obrigatório)."),
            "mes": _s("integer", "Mês (opcional)."),
            "por": _s("string", "'categoria' ou 'fornecedor' (opcional)."),
        },
        ["perfil_id", "ano"],
        lambda gw, a: consultas.total_despesas(
            gw, perfil_id=a.get("perfil_id"), ano=a.get("ano"), mes=a.get("mes"), por=a.get("por")
        ),
    ),
    Ferramenta(
        "emendas_por_municipio",
        "Emendas parlamentares destinadas a um município. Valores por estágio "
        "orçamentário (empenhado/liquidado/pago/restos), nunca somados entre si.",
        {
            "municipio": _s("string", "Nome do município."),
            "uf": _s("string", "UF (opcional)."),
            "ano": _s("integer", "Ano (opcional)."),
        },
        ["municipio"],
        lambda gw, a: consultas.emendas_por_municipio(
            gw, municipio=a.get("municipio", ""), uf=a.get("uf"), ano=a.get("ano")
        ),
    ),
    Ferramenta(
        "emendas_por_autor_perfil",
        "Emendas de um autor por CHAVE VERIFICADA (autor_profile_id). Atribuição sem "
        "ambiguidade — PREFIRA esta: use buscar_parlamentar para obter o perfil_id e "
        "então consulte aqui. Bancada/comissão não têm autor único e ficam de fora.",
        {
            "perfil_id": _s("string", "id do parlamentar (de buscar_parlamentar)."),
            "ano": _s("integer", "Ano (opcional)."),
        },
        ["perfil_id"],
        lambda gw, a: consultas.emendas_por_autor_perfil(
            gw, perfil_id=a.get("perfil_id", ""), ano=a.get("ano")
        ),
    ),
    Ferramenta(
        "emendas_por_autor_nome",
        "Emendas de um autor casadas por NOME (fallback, com ressalva de homônimo). "
        "Insensível a acento/caixa. Use só quando não houver perfil_id; do contrário "
        "prefira emendas_por_autor_perfil (mais confiável).",
        {
            "nome": _s("string", "Nome do autor."),
            "ano": _s("integer", "Ano (opcional)."),
        },
        ["nome"],
        lambda gw, a: consultas.emendas_por_autor_nome(
            gw, nome=a.get("nome", ""), ano=a.get("ano")
        ),
    ),
    Ferramenta(
        "agenda_eventos",
        "Agenda legislativa (eventos) num intervalo de datas AAAA-MM-DD. "
        "casa='camara'|'senado'; situacao (Agendada/Realizada/Cancelada) opcional.",
        {
            "data_inicio": _s("string", "Data inicial AAAA-MM-DD."),
            "data_fim": _s("string", "Data final AAAA-MM-DD."),
            "casa": _s("string", "'camara' ou 'senado' (opcional)."),
            "situacao": _s("string", "Agendada/Realizada/Cancelada (opcional)."),
        },
        ["data_inicio", "data_fim"],
        lambda gw, a: consultas.agenda_eventos(
            gw,
            data_inicio=a.get("data_inicio", ""),
            data_fim=a.get("data_fim", ""),
            casa=a.get("casa"),
            situacao=a.get("situacao"),
        ),
    ),
]

POR_NOME = {f.nome: f for f in FERRAMENTAS}


def esquemas_anthropic() -> list[dict]:
    """Definições no formato de `tools` da Claude API."""
    return [
        {
            "name": f.nome,
            "description": f.descricao,
            "input_schema": {
                "type": "object",
                "properties": f.propriedades,
                "required": f.obrigatorios,
            },
        }
        for f in FERRAMENTAS
    ]


def executar(gw: Gateway, nome: str, args: dict) -> dict:
    """Despacha uma chamada de ferramenta e devolve o resultado (dict de §20)."""
    f = POR_NOME.get(nome)
    if f is None:
        return {
            "recusa": f"Ferramenta desconhecida: {nome}.",
            "dados": None,
            "proveniencia": [],
            "completude": None,
            "ressalvas": [],
        }
    return f.executor(gw, args or {}).to_dict()
