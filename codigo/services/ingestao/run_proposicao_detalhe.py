"""Enriquecimento de PROPOSIÇÃO pelo DETALHE (Câmara) — preenche os campos que a
LISTA não traz: `situacao`, `tema` (keywords) e `inteiro_teor_url`.

A coleta de proposições guardou só os campos da lista (ementa, data, tipo…); a
situação/tema/inteiro-teor vivem no `/proposicoes/{id}` (um GET por proposição).
Este runner fecha esse buraco (era 0%). Fatiável por ano (`AQUARIUS_PROP_ANO`),
RESUMÍVEL (pula proposição que já tem `situacao`), ISOLADO por proposição,
IDEMPOTENTE (update dos 3 campos). Só CÂMARA (o endpoint é da Câmara; Senado é
passe à parte pelo detalhe da matéria).
"""

from __future__ import annotations

import os
import time
import traceback

from env_local import carregar_env
from camara.proposicoes import extrair_enriquecimento_proposicao
from pipeline.coletor import PoliticaRetry, obter_com_retry
from pipeline.http import ClienteHttpUrllib

BASE = "https://dadosabertos.camara.leg.br/api/v2"


def _proposicoes(raw, ano: int | None) -> list[dict]:
    out: list[dict] = []
    inicio = 0
    while True:
        q = (raw.table("proposicao").select("id,id_na_fonte,situacao")
             .eq("casa_origem", "camara"))
        if ano is not None:
            q = q.eq("ano", ano)
        linhas = q.order("id_na_fonte").range(inicio, inicio + 999).execute().data
        out.extend(linhas)
        if len(linhas) < 1000:
            return out
        inicio += 1000


def main() -> None:
    carregar_env()
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    ano = int(os.environ["AQUARIUS_PROP_ANO"]) if os.environ.get("AQUARIUS_PROP_ANO") else None
    limite = int(os.environ["AQUARIUS_PROP_LIMITE"]) if os.environ.get("AQUARIUS_PROP_LIMITE") else None

    from supabase import create_client
    raw = create_client(url, key)
    http = ClienteHttpUrllib()
    politica = PoliticaRetry()

    props = _proposicoes(raw, ano)
    print(f"=== PROPOSIÇÃO DETALHE ({ano or 'TODAS'}) — {len(props)} proposições ===",
          flush=True)

    feitas = puladas = vazias = falhas = 0
    inicio = time.time()
    for i, p in enumerate(props):
        if limite is not None and (feitas + puladas + vazias + falhas) >= limite:
            break
        if p.get("situacao"):
            puladas += 1
            continue
        try:
            corpo = obter_com_retry(http, f"{BASE}/proposicoes/{p['id_na_fonte']}",
                                    politica=politica)
            det = (corpo or {}).get("dados") or {}
            enr = extrair_enriquecimento_proposicao(det)
            if not any(enr.values()):
                vazias += 1
                continue
            raw.table("proposicao").update(enr).eq("id", p["id"]).execute()
            feitas += 1
        except Exception:  # noqa: BLE001 — uma proposição não derruba o lote
            falhas += 1
            traceback.print_exc()
        if (i + 1) % 500 == 0:
            dt = time.time() - inicio
            print(f"  {i+1}/{len(props)} feitas={feitas} puladas={puladas} "
                  f"vazias={vazias} falhas={falhas} ({dt/60:.1f} min)", flush=True)

    print(f"=== FIM ({ano or 'TODAS'}): feitas={feitas} puladas={puladas} "
          f"vazias={vazias} falhas={falhas} ===", flush=True)


if __name__ == "__main__":
    main()
