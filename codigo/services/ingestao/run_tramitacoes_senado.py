"""Backfill STANDALONE de tramitações do SENADO (Área D, §11, bicameral).

A perna do Senado da tramitação. O endpoint é `/processo/{idProcesso}`, e o
`idProcesso` (≠ código da matéria) NÃO é persistido — `salvar_proposicoes` o
ignora (ver `senado/materias.py`). Este runner recupera o `idProcesso` de CADA
matéria do banco pelo DETALHE da matéria
(`/materia/{codigo}` → `DetalheMateria.Materia.IdentificacaoMateria.IdentificacaoProcesso`),
depois busca a tramitação. Duas chamadas por matéria — robusto (o detalhe sempre
resolve, ao contrário da pesquisa por data, que tem lacunas de janela/cap).

Mesmas disciplinas do runner da Câmara: FATIÁVEL por ano (`AQUARIUS_TRAM_ANO`),
RESUMÍVEL (pula matéria que já tem tramitação), ISOLADO por matéria (uma que
falha é pulada) e IDEMPOTENTE (upsert por proposicao_id,sequencia). Reusa
`rodada_tramitacoes_senado` e `salvar_tramitacoes` (casa='senado').

Uso:
    $env:SUPABASE_URL=...; $env:SUPABASE_SERVICE_KEY=...
    $env:AQUARIUS_TRAM_ANO="2021"   # opcional (fatia por ano)
    py run_tramitacoes_senado.py
"""

from __future__ import annotations

import os
import time
import traceback

from env_local import carregar_env
from contrato.canario import EstadoContrato
from persistencia.repositorio import salvar_tramitacoes
from persistencia.supabase_adapter import BancoSupabase
from pipeline.coletor import PoliticaRetry, obter_com_retry
from pipeline.http import ClienteHttpUrllib
from senado.tramitacoes import BASE as BASE_SENADO, rodada_tramitacoes_senado

LOTE_LEITURA = 500


def _materias_senado(raw, ano: int | None, tam: int = 1000) -> list[dict]:
    out: list[dict] = []
    inicio = 0
    while True:
        q = (raw.table("proposicao").select("id,id_na_fonte,ano")
             .eq("casa_origem", "senado"))
        if ano is not None:
            q = q.eq("ano", ano)
        linhas = q.order("id_na_fonte").range(inicio, inicio + tam - 1).execute().data
        out.extend(linhas)
        if len(linhas) < tam:
            return out
        inicio += tam


def _ids_com_tramitacao(raw, uuids: list[str]) -> set[str]:
    """Quais dos `uuids` já têm tramitação. Pagina por keyset (o PostgREST corta
    a resposta em 1000 linhas; sem paginar, subconta os feitos)."""
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


def _id_processo(http, codigo: str, politica: PoliticaRetry) -> str | None:
    """Recupera o idProcesso do DETALHE da matéria (sempre resolve)."""
    corpo = obter_com_retry(http, f"{BASE_SENADO}/materia/{codigo}", politica=politica)
    dm = (corpo or {}).get("DetalheMateria") or {}
    mat = dm.get("Materia") or {}
    ident = mat.get("IdentificacaoMateria") or {}
    idp = ident.get("IdentificacaoProcesso")
    return str(idp) if idp else None


def main() -> None:
    carregar_env()
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    ano_env = os.environ.get("AQUARIUS_TRAM_ANO")
    ano = int(ano_env) if ano_env else None
    limite_env = os.environ.get("AQUARIUS_TRAM_LIMITE")
    limite = int(limite_env) if limite_env else None

    from supabase import create_client
    raw = create_client(url, key)
    banco = BancoSupabase(raw)
    http = ClienteHttpUrllib()
    politica = PoliticaRetry()

    mats = _materias_senado(raw, ano)
    alvo = f"ano {ano}" if ano else "TODAS"
    print(f"=== TRAMITAÇÕES SENADO ({alvo}) — {len(mats)} matérias ===", flush=True)

    feitas = puladas = vazias = sem_proc = falhas = linhas_salvas = 0
    inicio = time.time()

    for i in range(0, len(mats), LOTE_LEITURA):
        lote = mats[i:i + LOTE_LEITURA]
        ja = _ids_com_tramitacao(raw, [m["id"] for m in lote])
        for m in lote:
            if limite is not None and (feitas + puladas + vazias + sem_proc + falhas) >= limite:
                break
            if m["id"] in ja:
                puladas += 1
                continue
            try:
                idp = _id_processo(http, m["id_na_fonte"], politica)
                if not idp:
                    sem_proc += 1
                    continue
                rt = rodada_tramitacoes_senado(
                    http, idp, m["id_na_fonte"],
                    canario_validado=True, linha_base=None, politica=politica)
                if rt.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA) \
                        or rt.prata is None:
                    vazias += 1
                    continue
                n = salvar_tramitacoes(
                    banco, rt.prata.aprovados,
                    source="senado.tramitacoes", source_url=BASE_SENADO)
                linhas_salvas += n
                if n:
                    feitas += 1
                else:
                    vazias += 1   # matéria sem informe legislativo (recém-protocolada)
            except Exception:  # noqa: BLE001 — uma matéria não derruba o lote
                falhas += 1
                traceback.print_exc()
        vistos = feitas + puladas + vazias + sem_proc + falhas
        dt = time.time() - inicio
        print(f"  progresso: {vistos}/{len(mats)}  feitas={feitas} puladas={puladas} "
              f"vazias={vazias} sem_proc={sem_proc} falhas={falhas} "
              f"linhas={linhas_salvas}  ({dt/60:.1f} min)", flush=True)
        if limite is not None and vistos >= limite:
            break

    print(f"=== FIM ({alvo}): feitas={feitas} puladas={puladas} vazias={vazias} "
          f"sem_proc={sem_proc} falhas={falhas} linhas_salvas={linhas_salvas} ===",
          flush=True)


if __name__ == "__main__":
    main()
