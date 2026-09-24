"""Enriquecimento de MATÉRIA do Senado pelo DETALHE — preenche `situacao` e `tema`
(o par do enriquecimento de proposição da Câmara, para a mesma tabela `proposicao`
com `casa_origem='senado'`).

A pesquisa-lista de matérias não traz situação nem indexação; elas vivem em
`/materia/{codigo}` (tema = IndexacaoMateria) e `/materia/situacaoatual/{codigo}`
(situacao = DescricaoSituacao). Duas chamadas por matéria (a API do Senado não
sofre o throttle da Câmara). Fatiável por ano (`AQUARIUS_PROP_ANO`), RESUMÍVEL
(pula matéria que já tem `situacao`), ISOLADO por matéria, IDEMPOTENTE.
"""

from __future__ import annotations

import os
import time
import traceback

from env_local import carregar_env
from senado.materias import extrair_enriquecimento_materia
from pipeline.coletor import PoliticaRetry, obter_com_retry
from pipeline.http import ClienteHttpUrllib

BASE = "https://legis.senado.leg.br/dadosabertos"


def _materias(raw, ano: int | None) -> list[dict]:
    out: list[dict] = []
    inicio = 0
    while True:
        q = (raw.table("proposicao").select("id,id_na_fonte,situacao")
             .eq("casa_origem", "senado"))
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

    mats = _materias(raw, ano)
    print(f"=== MATÉRIA DETALHE SENADO ({ano or 'TODAS'}) — {len(mats)} matérias ===",
          flush=True)

    feitas = puladas = vazias = falhas = 0
    inicio = time.time()
    for i, m in enumerate(mats):
        if limite is not None and (feitas + puladas + vazias + falhas) >= limite:
            break
        if m.get("situacao"):
            puladas += 1
            continue
        cod = m["id_na_fonte"]
        try:
            det = obter_com_retry(http, f"{BASE}/materia/{cod}", politica=politica)
            sit = obter_com_retry(http, f"{BASE}/materia/situacaoatual/{cod}", politica=politica)
            enr = extrair_enriquecimento_materia(det or {}, sit or {})
            if not any(enr.values()):
                vazias += 1
                continue
            raw.table("proposicao").update(enr).eq("id", m["id"]).execute()
            feitas += 1
        except Exception:  # noqa: BLE001 — uma matéria não derruba o lote
            falhas += 1
            traceback.print_exc()
        if (i + 1) % 500 == 0:
            dt = time.time() - inicio
            print(f"  {i+1}/{len(mats)} feitas={feitas} puladas={puladas} "
                  f"vazias={vazias} falhas={falhas} ({dt/60:.1f} min)", flush=True)

    print(f"=== FIM ({ano or 'TODAS'}): feitas={feitas} puladas={puladas} "
          f"vazias={vazias} falhas={falhas} ===", flush=True)


if __name__ == "__main__":
    main()
