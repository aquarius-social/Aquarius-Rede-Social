"""Backfill STANDALONE de tramitações (Área D, §11) — a cauda cara.

Roda DESACOPLADO da coleta de proposições: lê os ids das proposições da Câmara
já no banco (camada prata) e busca a tramitação de CADA uma
(`/proposicoes/{id}/tramitacoes`, 1 chamada por proposição). É a "passada
própria" que o `AQUARIUS_TRAMITACOES=0` adiou no backfill de atividade — pesada
demais (~41 mil chamadas) para caber junto do resto num job de nuvem.

Disciplinas:
  • FATIÁVEL por ano — `AQUARIUS_TRAM_ANO=2021` processa só as proposições de 2021
    (para rodar em MATRIZ na nuvem, cada ano um job < 6h). Sem a var, faz todas.
  • RESUMÍVEL — pula proposições que JÁ têm tramitação (checagem em lote via
    `in_`), então re-rodar preenche só o que faltou (throttle deixa buracos).
  • ISOLADO por proposição — uma proposição que falha (throttle/500) cai em
    contrato FALHA dentro de `rodada_tramitacoes`, é pulada, e a próxima segue.
    Nada de um erro derrubar o lote (lição do backfill de votações).
  • IDEMPOTENTE — `salvar_tramitacoes` faz upsert por (proposicao_id, sequencia).

Uso:
    $env:SUPABASE_URL=...; $env:SUPABASE_SERVICE_KEY=...
    $env:AQUARIUS_TRAM_ANO="2021"   # opcional (fatia por ano)
    py run_tramitacoes.py
"""

from __future__ import annotations

import os
import time
import traceback

from env_local import carregar_env
from camara.tramitacoes import rodada_tramitacoes
from contrato.canario import EstadoContrato
from persistencia.repositorio import salvar_tramitacoes
from persistencia.supabase_adapter import BancoSupabase
from pipeline.coletor import PoliticaRetry
from pipeline.http import ClienteHttpUrllib

LOTE_LEITURA = 500   # proposições por página de leitura + checagem de "já feito"


def _proposicoes_camara(raw, ano: int | None, tam: int = 1000) -> list[dict]:
    """Lê (id, id_na_fonte) das proposições da Câmara, paginado. Filtra por ano
    quando dado (fatiamento de nuvem)."""
    out: list[dict] = []
    inicio = 0
    while True:
        q = (raw.table("proposicao").select("id,id_na_fonte,ano")
             .eq("casa_origem", "camara"))
        if ano is not None:
            q = q.eq("ano", ano)
        linhas = q.order("id_na_fonte").range(inicio, inicio + tam - 1).execute().data
        out.extend(linhas)
        if len(linhas) < tam:
            return out
        inicio += tam


def _ids_com_tramitacao(raw, uuids: list[str]) -> set[str]:
    """Dos `uuids` dados, quais JÁ têm ao menos uma tramitação (checagem em lote).

    GOTCHA: o PostgREST corta a resposta em 1000 linhas. Como cada proposição tem
    ~14 tramitações, um `in_` de 500 uuids casa milhares de linhas → a resposta
    truncada subconta os feitos (re-processa quem já estava pronto). Por isso
    PAGINAMOS por keyset em `proposicao_id` até esgotar."""
    if not uuids:
        return set()
    done: set[str] = set()
    ultimo: str | None = None
    while True:
        q = (raw.table("tramitacao").select("proposicao_id")
             .in_("proposicao_id", uuids).order("proposicao_id").limit(1000))
        if ultimo is not None:
            q = q.gt("proposicao_id", ultimo)
        linhas = q.execute().data
        if not linhas:
            break
        for l in linhas:
            done.add(l["proposicao_id"])
        ultimo = linhas[-1]["proposicao_id"]
        if len(linhas) < 1000:
            break
    return done


def main() -> None:
    carregar_env()
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    ano_env = os.environ.get("AQUARIUS_TRAM_ANO")
    ano = int(ano_env) if ano_env else None
    limite_env = os.environ.get("AQUARIUS_TRAM_LIMITE")   # p/ smoke test
    limite = int(limite_env) if limite_env else None

    from supabase import create_client
    raw = create_client(url, key)
    banco = BancoSupabase(raw)
    http = ClienteHttpUrllib()
    politica = PoliticaRetry()

    props = _proposicoes_camara(raw, ano)
    alvo = f"ano {ano}" if ano else "TODAS"
    print(f"=== TRAMITAÇÕES ({alvo}) — {len(props)} proposições da Câmara ===",
          flush=True)

    feitas = puladas = vazias = falhas = linhas_salvas = 0
    inicio = time.time()

    for i in range(0, len(props), LOTE_LEITURA):
        lote = props[i:i + LOTE_LEITURA]
        ja = _ids_com_tramitacao(raw, [p["id"] for p in lote])
        for p in lote:
            if limite is not None and (feitas + puladas + vazias + falhas) >= limite:
                break
            if p["id"] in ja:
                puladas += 1
                continue
            try:
                rt = rodada_tramitacoes(
                    http, p["id_na_fonte"],
                    canario_validado=True, linha_base=None, politica=politica,
                )
                if rt.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA) \
                        or rt.prata is None:
                    # sem tramitação coletável agora (vazio real ou throttle) —
                    # não inventa; re-rodar tenta de novo.
                    vazias += 1
                    continue
                n = salvar_tramitacoes(banco, rt.prata.aprovados)
                linhas_salvas += n
                feitas += 1
            except Exception:  # noqa: BLE001 — uma proposição não derruba o lote
                falhas += 1
                traceback.print_exc()
        vistos = feitas + puladas + vazias + falhas
        dt = time.time() - inicio
        print(f"  progresso: {vistos}/{len(props)}  feitas={feitas} "
              f"puladas={puladas} vazias={vazias} falhas={falhas} "
              f"linhas={linhas_salvas}  ({dt/60:.1f} min)", flush=True)
        if limite is not None and vistos >= limite:
            break

    print(f"=== FIM ({alvo}): feitas={feitas} puladas={puladas} vazias={vazias} "
          f"falhas={falhas} linhas_salvas={linhas_salvas} ===", flush=True)


if __name__ == "__main__":
    main()
