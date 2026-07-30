"""Entrypoint de produção da ingestão da Câmara.

Amarra o cliente HTTP real (urllib, stdlib) e o banco Supabase concreto ao
orquestrador. É o artefato de DEPLOY: aqui a lógica testada com fakes passa a
falar com a fonte viva e o banco real.

Rodar (no deploy, com o pacote `supabase` instalado e as variáveis definidas —
ver .env.example):

    pip install supabase
    export SUPABASE_URL=... SUPABASE_SERVICE_KEY=...
    python run_ingestao.py

Neste ambiente de desenvolvimento NÃO roda: o pacote `supabase` não está
instalado (a lógica inteira é coberta por 170+ testes sem rede). O import de
`supabase` é tardio (dentro de `criar_banco_supabase`), então este módulo é
importável sem o pacote.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from orquestracao.orquestrador import ingerir
from persistencia.supabase_adapter import criar_banco_supabase
from pipeline.coletor import JanelaMovel
from pipeline.http import ClienteHttpUrllib


def main() -> None:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    janela_dias = int(os.environ.get("AQUARIUS_JANELA_DIAS", "30"))
    id_legislatura = os.environ.get("AQUARIUS_LEGISLATURA")

    http = ClienteHttpUrllib()
    banco = criar_banco_supabase(url, key)

    r = ingerir(
        http, banco,
        ate=datetime.now(timezone.utc).date(),
        janela=JanelaMovel(dias=janela_dias),
        id_legislatura=int(id_legislatura) if id_legislatura else None,
    )

    print(
        "ingestão concluída — "
        f"partidos={r.partidos_salvos} perfis={r.perfis_salvos} "
        f"vinculos={r.vinculos_salvos} proposicoes={r.proposicoes_salvas} "
        f"tramitacoes={r.tramitacoes_salvas} votacoes={r.votacoes_salvas} "
        f"votos={r.votos_salvos} bronze={r.bronze_salvo}"
    )
    if r.placar_violacoes:
        print(f"ATENÇÃO: {len(r.placar_violacoes)} votação(ões) com "
              "divergência entre placar declarado e nominais (§5.2)")


if __name__ == "__main__":
    main()
