"""Diagnóstico pontual do 'tramitacoes=0'. Roda no CI com os secrets.
Lê a tabela `proposicao` direto (service_role ignora RLS) e reproduz a
resolução da FK que `salvar_tramitacoes` faz. Descartável depois do fix."""

import os

from camara.tramitacoes import (
    coletar_bronze_tramitacoes,
    processar_tramitacoes_para_prata,
)
from persistencia.repositorio import salvar_tramitacoes
from persistencia.supabase_adapter import criar_banco_supabase
from pipeline.http import ClienteHttpUrllib


def main() -> None:
    banco = criar_banco_supabase(
        os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    http = ClienteHttpUrllib()
    pid = "2637279"  # PL 3481/2026 — sabidamente na base (votação resolveu)

    print("=== [1] resolução da FK (o que salvar_tramitacoes faz) ===")
    prop = banco.selecionar_um(
        "proposicao", {"casa_origem": "camara", "id_na_fonte": pid})
    print(f"  casa=camara + id_na_fonte={pid!r} -> achou? {prop is not None}"
          f"  (id={(prop or {}).get('id')})")

    prop_so_id = banco.selecionar_um("proposicao", {"id_na_fonte": pid})
    print(f"  só id_na_fonte={pid!r} -> achou? {prop_so_id is not None}")

    prop_int = banco.selecionar_um("proposicao", {"id_na_fonte": int(pid)})
    print(f"  id_na_fonte={int(pid)} (int) -> achou? {prop_int is not None}")

    print("=== [1c] o que está REALMENTE gravado numa proposição ===")
    qualquer = banco.selecionar_um("proposicao", {"casa_origem": "camara"}) or {}
    print(f"  casa_origem={qualquer.get('casa_origem')!r} "
          f"id_na_fonte={qualquer.get('id_na_fonte')!r} "
          f"(tipo id_na_fonte: {type(qualquer.get('id_na_fonte')).__name__})")

    print("=== [2] coleta + portão + salvar (fluxo real, uma proposição) ===")
    bronze = coletar_bronze_tramitacoes(http, pid)
    prata = processar_tramitacoes_para_prata(bronze, pid)
    print(f"  tramitações coletadas={len(bronze)} | aprovados={len(prata.aprovados)}"
          f" | quarentena={len(prata.quarentena)}")
    if prata.quarentena:
        _, viol = prata.quarentena[0]
        print(f"  1ª quarentena: dim={viol.dimensao} motivo={viol.motivo!r}")
    if prata.aprovados:
        t = prata.aprovados[0]
        print(f"  amostra prata: casa={t['casa']!r} "
              f"proposicao_id_fonte={t['proposicao_id_fonte']!r} "
              f"(tipo: {type(t['proposicao_id_fonte']).__name__}) "
              f"seq={t['sequencia']!r} data_hora={t['data_hora']!r} "
              f"descricao={(t['descricao'] or '')[:30]!r}")
    n = salvar_tramitacoes(banco, prata.aprovados)
    print(f"  >>> salvar_tramitacoes -> {n} persistidas <<<")


if __name__ == "__main__":
    main()
