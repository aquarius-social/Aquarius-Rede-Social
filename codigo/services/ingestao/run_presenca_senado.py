"""Backfill de PRESENÇA do SENADO (Área E, bicameral) — comparecimento em sessões.

Deriva a presença do `comparecimento` das votações nominais do Plenário
(`/votacao?dataInicio&dataFim`), agrupado por sessão (ver `senado/presenca.py`).
Reusa as tabelas `sessao`/`presenca` (casa='senado') — a mesma migration 0019.

FATIÁVEL por ano (`AQUARIUS_PRESENCA_ANO`), IDEMPOTENTE (upsert). Um fetch por
ano traz todas as votações; salva sessão + presença. Leve.

PRÉ-REQUISITO: migration 0019 aplicada.
"""

from __future__ import annotations

import os
import traceback

from env_local import carregar_env
from senado.presenca import rodada_presenca_senado
from persistencia.repositorio import (
    lookup_id_externo, salvar_presencas, salvar_sessoes)
from persistencia.supabase_adapter import BancoSupabase
from pipeline.coletor import PoliticaRetry
from pipeline.http import ClienteHttpUrllib


def _rodar_ano(banco, http, politica, lookup, ano: int) -> None:
    r = rodada_presenca_senado(
        http, data_inicio=f"{ano}-01-01", data_fim=f"{ano}-12-31",
        canario_validado=True, linha_base=None, politica=politica)
    print(f">>> {ano}: votações={len(r.bronze)} sessões={len(r.sessoes)} "
          f"(estado={r.estado})", flush=True)
    if not r.sessoes:
        return
    salvar_sessoes(banco, r.sessoes)
    presencas = falhas = 0
    for s in r.sessoes:
        sid = s["id_fonte"]
        try:
            presencas += salvar_presencas(
                banco, sid, r.presencas.get(sid, []), lookup,
                casa="senado", source="senado.presenca")
        except Exception:  # noqa: BLE001 — uma sessão não derruba o ano
            falhas += 1
            traceback.print_exc()
    print(f"    {ano} OK: sessoes={len(r.sessoes)} presencas={presencas} "
          f"falhas={falhas}", flush=True)


def main() -> None:
    carregar_env()
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    ano_env = os.environ.get("AQUARIUS_PRESENCA_ANO")
    anos = [int(ano_env)] if ano_env else list(range(2018, 2027))

    from supabase import create_client
    raw = create_client(url, key)
    banco = BancoSupabase(raw)
    http = ClienteHttpUrllib()
    politica = PoliticaRetry()
    lookup = lookup_id_externo(banco)

    print(f"=== PRESENÇA SENADO (anos {anos[0]}–{anos[-1]}) — comparecimento em "
          f"votações do Plenário ===", flush=True)
    for ano in anos:
        try:
            _rodar_ano(banco, http, politica, lookup, ano)
        except Exception:  # noqa: BLE001 — um ano que falha não derruba os outros
            print(f"    ERRO no ano {ano} — pulando:", flush=True)
            traceback.print_exc()
    print("=== FIM ===", flush=True)


if __name__ == "__main__":
    main()
