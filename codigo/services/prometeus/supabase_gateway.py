"""Gateway real: lê a camada ouro do Supabase via PostgREST.

Só é exercido em execução real (Etapas 2.2/2.4) — a suíte usa o FakeGateway. Por
isso o `httpx` é importado preguiçosamente: importar este módulo não exige a
dependência, e a suíte nem toca aqui.

Lê SÓ as views ouro (`*_publico`/`*_publica`), que têm GRANT SELECT para a chave
anon. Nunca escreve, nunca lê tabela de prata.
"""
from __future__ import annotations

import os

from gateway import Consulta, Filtro


class SupabaseGateway:
    def __init__(self, url: str | None = None, chave: str | None = None) -> None:
        base = (url or os.environ["SUPABASE_URL"]).rstrip("/")
        self.base = f"{base}/rest/v1"
        self.chave = chave or os.environ["SUPABASE_ANON_KEY"]

    def buscar(self, consulta: Consulta) -> list[dict]:
        import httpx  # dependência só de runtime

        # Lista de tuplas (não dict): permite dois filtros na MESMA coluna,
        # como o intervalo de data da agenda (gte + lte em data_hora_inicio).
        params: list[tuple[str, str]] = [("select", consulta.select)]
        for f in consulta.filtros:
            params.append((f.coluna, _para_postgrest(f)))
        if consulta.ordem:
            params.append(("order", consulta.ordem))
        if consulta.limite:
            params.append(("limit", str(consulta.limite)))

        headers = {"apikey": self.chave, "Authorization": f"Bearer {self.chave}"}
        resp = httpx.get(
            f"{self.base}/{consulta.view}", params=params, headers=headers, timeout=20.0
        )
        resp.raise_for_status()
        return resp.json()


def _para_postgrest(f: Filtro) -> str:
    if f.op == "ilike":
        return f"ilike.*{f.valor}*"
    if f.op == "in":
        return "in.(" + ",".join(str(v) for v in f.valor) + ")"
    return f"{f.op}.{f.valor}"
