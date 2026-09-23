"""Backfill de PRESENÇA (Área E) — frequência em sessões do Plenário da Câmara.

Coleta as sessões deliberativas do Plenário de um ano e, para cada uma, a lista
de presentes (`/eventos/{id}/deputados`). Salva `sessao` + `presenca`; a view
ouro `presenca_publica` agrega presenças/convocadas/% por parlamentar.

FATIÁVEL por ano (`AQUARIUS_PRESENCA_ANO`), RESUMÍVEL (pula sessão que já tem
presença), ISOLADO por sessão (uma que falha é pulada) e IDEMPOTENTE. Identidade
resolvida na coleta por id_externo (a PESSOA, na data da sessão §4).

PRÉ-REQUISITO: migration 0019_presenca (tabelas `sessao`/`presenca` + view).

Uso:
    $env:SUPABASE_URL=...; $env:SUPABASE_SERVICE_KEY=...
    $env:AQUARIUS_PRESENCA_ANO="2024"   # opcional (default 2018–2026)
    py run_presenca.py
"""

from __future__ import annotations

import os
import time
import traceback

from env_local import carregar_env
from camara.presenca import rodada_sessoes, rodada_presencas
from persistencia.repositorio import (
    lookup_id_externo, salvar_presencas, salvar_sessoes)
from persistencia.supabase_adapter import BancoSupabase
from pipeline.coletor import PoliticaRetry
from pipeline.http import ClienteHttpUrllib


def _sessoes_com_presenca(raw, uuids: list[str]) -> set[str]:
    """Quais sessões (uuid) já têm presença. Pagina por keyset (teto de 1000)."""
    if not uuids:
        return set()
    done: set[str] = set()
    ultimo: str | None = None
    while True:
        q = (raw.table("presenca").select("sessao_id")
             .in_("sessao_id", uuids).order("sessao_id").limit(1000))
        if ultimo is not None:
            q = q.gt("sessao_id", ultimo)
        linhas = q.execute().data
        if not linhas:
            break
        for l in linhas:
            done.add(l["sessao_id"])
        ultimo = linhas[-1]["sessao_id"]
        if len(linhas) < 1000:
            break
    return done


def _uuid_por_id_fonte(raw, id_fontes: list[str]) -> dict[str, str]:
    """Mapa id_fonte -> uuid das sessões da Câmara (em lotes de 200)."""
    mapa: dict[str, str] = {}
    for i in range(0, len(id_fontes), 200):
        lote = id_fontes[i:i + 200]
        linhas = (raw.table("sessao").select("id,id_fonte")
                  .eq("casa", "camara").in_("id_fonte", lote).execute().data)
        for l in linhas:
            mapa[l["id_fonte"]] = l["id"]
    return mapa


def _rodar_ano(raw, banco, http, politica, lookup, ano: int) -> None:
    rs = rodada_sessoes(
        http, data_inicio=f"{ano}-01-01", data_fim=f"{ano}-12-31",
        canario_validado=True, linha_base=None, politica=politica)
    sessoes = rs.prata.aprovados if rs.prata else []
    print(f">>> {ano}: {len(sessoes)} sessões deliberativas (estado={rs.estado})",
          flush=True)
    if not sessoes:
        return
    salvar_sessoes(banco, sessoes)

    id_fontes = [s["id_fonte"] for s in sessoes]
    uuid_de = _uuid_por_id_fonte(raw, id_fontes)
    ja = _sessoes_com_presenca(raw, list(uuid_de.values()))

    feitas = puladas = vazias = falhas = linhas = 0
    inicio = time.time()
    for s in sessoes:
        idf = s["id_fonte"]
        if uuid_de.get(idf) in ja:
            puladas += 1
            continue
        try:
            rp = rodada_presencas(http, idf, canario_validado=True, linha_base=None,
                                  politica=politica)
            if rp.prata is None or not rp.prata.aprovados:
                vazias += 1
                continue
            n = salvar_presencas(banco, idf, rp.prata.aprovados, lookup)
            linhas += n
            feitas += 1
        except Exception:  # noqa: BLE001 — uma sessão não derruba o ano
            falhas += 1
            traceback.print_exc()
    dt = time.time() - inicio
    print(f"    {ano} OK: sessoes={len(sessoes)} feitas={feitas} puladas={puladas} "
          f"vazias={vazias} falhas={falhas} presencas={linhas} ({dt/60:.1f} min)",
          flush=True)


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

    print(f"=== PRESENÇA (anos {anos[0]}–{anos[-1]}) — Plenário da Câmara ===",
          flush=True)
    for ano in anos:
        try:
            _rodar_ano(raw, banco, http, politica, lookup, ano)
        except Exception:  # noqa: BLE001 — um ano que falha não derruba os outros
            print(f"    ERRO no ano {ano} — pulando:", flush=True)
            traceback.print_exc()
    print("=== FIM ===", flush=True)


if __name__ == "__main__":
    main()
