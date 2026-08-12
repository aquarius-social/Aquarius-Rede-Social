"""Servidor MCP: expõe as consultas de `consultas.py` como ferramentas MCP.

Requer o pacote `mcp` (pip install "mcp[cli]") e, em execução, as variáveis
SUPABASE_URL / SUPABASE_ANON_KEY. NÃO é importado pela suíte — as consultas são
testadas direto, sem rede e sem esta dependência.

Cada ferramenta é uma consulta segura: o modelo escolhe qual chamar e com quais
parâmetros, nunca a redação (Metodologia §21). O retorno já vem com proveniência,
completude e ressalvas para o contrato de resposta (§20).
"""
from __future__ import annotations

import consultas
from supabase_gateway import SupabaseGateway


def construir_servidor(gateway=None):
    from mcp.server.fastmcp import FastMCP  # dependência só de runtime

    gw = gateway or SupabaseGateway()
    mcp = FastMCP("prometeus-congresso")

    @mcp.tool()
    def buscar_parlamentar(termo: str) -> dict:
        """Encontra parlamentar por nome (ou parte). Perfil ATUAL (partido/UF/casa de hoje) + fonte."""
        return consultas.buscar_parlamentar(gw, termo=termo).to_dict()

    @mcp.tool()
    def buscar_partido(termo: str) -> dict:
        """Encontra partido por sigla ou nome + fonte."""
        return consultas.buscar_partido(gw, termo=termo).to_dict()

    @mcp.tool()
    def despesas_parlamentar(perfil_id: str, ano: int, mes: int | None = None, tipo: str | None = None) -> dict:
        """Lançamentos de cota (CEAP/CEAPS) de um parlamentar num ano (mês/tipo opcionais). Exige ano."""
        return consultas.despesas_parlamentar(gw, perfil_id=perfil_id, ano=ano, mes=mes, tipo=tipo).to_dict()

    @mcp.tool()
    def total_despesas(perfil_id: str, ano: int, mes: int | None = None, por: str | None = None) -> dict:
        """Total de cota de um parlamentar (soma de valor_liquido). por='categoria'|'fornecedor' agrupa."""
        return consultas.total_despesas(gw, perfil_id=perfil_id, ano=ano, mes=mes, por=por).to_dict()

    @mcp.tool()
    def emendas_por_municipio(municipio: str, uf: str | None = None, ano: int | None = None) -> dict:
        """Emendas destinadas a um município. Valores por estágio (nunca somados entre si) + fonte."""
        return consultas.emendas_por_municipio(gw, municipio=municipio, uf=uf, ano=ano).to_dict()

    @mcp.tool()
    def emendas_por_autor_nome(nome: str, ano: int | None = None) -> dict:
        """Emendas de um autor por NOME (com ressalva — chave autor↔perfil ainda não carregada)."""
        return consultas.emendas_por_autor_nome(gw, nome=nome, ano=ano).to_dict()

    @mcp.tool()
    def agenda_eventos(data_inicio: str, data_fim: str, casa: str | None = None, situacao: str | None = None) -> dict:
        """Agenda legislativa num intervalo AAAA-MM-DD. casa='camara'|'senado'; situacao opcional."""
        return consultas.agenda_eventos(gw, data_inicio=data_inicio, data_fim=data_fim, casa=casa, situacao=situacao).to_dict()

    return mcp


if __name__ == "__main__":
    construir_servidor().run()
