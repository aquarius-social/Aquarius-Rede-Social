"""Gateway em memória para a suíte — aplica os filtros da Consulta sobre amostras.

Faz o que o PostgREST faria, para que os testes exercitem a lógica REAL das
consultas (quais filtros, como o resultado é moldado) sem tocar a rede.
"""
from __future__ import annotations

from gateway import Consulta, Filtro


class FakeGateway:
    def __init__(self, tabelas: dict[str, list[dict]]) -> None:
        self.tabelas = tabelas

    def buscar(self, consulta: Consulta) -> list[dict]:
        linhas = list(self.tabelas.get(consulta.view, []))
        for f in consulta.filtros:
            linhas = [l for l in linhas if _casa(l, f)]
        if consulta.ordem:
            col, _, direc = consulta.ordem.partition(".")
            linhas.sort(
                key=lambda l: (l.get(col) is None, l.get(col)),
                reverse=(direc == "desc"),
            )
        if consulta.limite:
            linhas = linhas[: consulta.limite]
        return [dict(l) for l in linhas]


def _casa(linha: dict, f: Filtro) -> bool:
    v = linha.get(f.coluna)
    if f.op == "eq":
        return str(v) == str(f.valor)
    if f.op == "gte":
        return v is not None and str(v) >= str(f.valor)
    if f.op == "lte":
        return v is not None and str(v) <= str(f.valor)
    if f.op == "ilike":
        return v is not None and str(f.valor).lower() in str(v).lower()
    if f.op == "in":
        return v in f.valor
    return False
