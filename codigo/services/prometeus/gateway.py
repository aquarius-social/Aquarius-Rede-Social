"""Contrato de acesso ao banco: uma Consulta declarativa + o protocolo Gateway.

Duas implementações falam este contrato: SupabaseGateway (PostgREST real, em
`supabase_gateway.py`) e FakeGateway (em memória, nos testes). As ferramentas de
`consultas.py` só conhecem este contrato — por isso a suíte roda sem rede.

Etapa 2.1 da Onda 2 (Prometeus). Ver PLANO.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

# Operadores neutros; cada gateway traduz para o seu dialeto (PostgREST / memória).
Operador = str  # 'eq' | 'gte' | 'lte' | 'ilike' | 'in'


@dataclass(frozen=True)
class Filtro:
    coluna: str
    op: Operador
    valor: Any


@dataclass
class Consulta:
    """Descreve UMA leitura da camada ouro. A redação é fixa (Metodologia §21):
    o modelo escolhe a ferramenta e os parâmetros, nunca monta SQL livre aqui."""

    view: str
    filtros: list[Filtro] = field(default_factory=list)
    select: str = "*"
    ordem: str | None = None   # ex.: "data_documento.desc"
    limite: int | None = None


class Gateway(Protocol):
    def buscar(self, consulta: Consulta) -> list[dict[str, Any]]:
        """Executa a consulta na camada ouro e devolve as linhas como dicts."""
        ...
