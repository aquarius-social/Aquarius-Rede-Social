"""O formato de retorno de toda ferramenta — desenhado para o contrato de §20.

Cada resultado carrega os dados, a proveniência (fonte/URL/frescor — regra 1), a
completude (janela + último registro — regra 3), ressalvas (base de atribuição,
estágio, atributo resolvido no presente — regras 2/5) e, quando é o caso, uma
recusa honesta (regra 7). Nada é servido sem proveniência.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Proveniencia:
    source: str | None
    source_url: str | None
    synced_at: str | None


@dataclass
class Completude:
    janela_inicio: str | None = None
    janela_fim: str | None = None
    ultimo_registro_em: str | None = None
    exclusoes_estruturais: list[str] = field(default_factory=list)


@dataclass
class Resultado:
    dados: Any = None
    proveniencia: list[Proveniencia] = field(default_factory=list)
    completude: Completude | None = None
    ressalvas: list[str] = field(default_factory=list)
    recusa: str | None = None  # regra 7: motivo da recusa (evita precisão falsa)

    @property
    def recusado(self) -> bool:
        return self.recusa is not None

    def to_dict(self) -> dict[str, Any]:
        """Forma que o modelo lê (via MCP). A recusa vem primeiro, de propósito."""
        return {
            "recusa": self.recusa,
            "dados": self.dados,
            "proveniencia": [asdict(p) for p in self.proveniencia],
            "completude": asdict(self.completude) if self.completude else None,
            "ressalvas": self.ressalvas,
        }


def recusar(motivo: str) -> Resultado:
    """Recusa honesta (regra 7). O motivo é sempre explícito."""
    return Resultado(recusa=motivo)


def proveniencia_das_linhas(linhas: list[dict]) -> list[Proveniencia]:
    """Extrai a proveniência DISTINTA das linhas (regra 1). Nada sem fonte."""
    vistas: dict[tuple, Proveniencia] = {}
    for linha in linhas:
        p = Proveniencia(
            linha.get("source"), linha.get("source_url"), linha.get("synced_at")
        )
        vistas[(p.source, p.source_url, p.synced_at)] = p
    return list(vistas.values())
