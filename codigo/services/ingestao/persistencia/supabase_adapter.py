"""Adaptador concreto de `ClienteBanco` sobre o cliente supabase-py.

Fecha o último elo entre "lógica pronta" e "ingestão rodando": os coletores e o
repositório falam com a porta `ClienteBanco` (persistencia/repositorio.py); esta
classe implementa essa porta sobre o cliente Supabase real.

DUAS DISCIPLINAS deliberadas:

  1. O cliente é INJETADO no construtor — a classe `BancoSupabase` NÃO importa
     `supabase`. Assim ela é testável contra um duble (test_supabase_adapter.py)
     sem o pacote instalado nem rede, e a suíte inteira importa este módulo sem
     exigir `supabase`.

  2. `supabase` só é importado dentro de `criar_banco_supabase` (import tardio),
     que é o ponto de deploy. Neste ambiente o pacote não existe (verificado);
     lá, `pip install supabase` e as credenciais o resolvem. Não escrevemos
     código que exija a dependência no topo do módulo (CLAUDE.md, regra 4).

CREDENCIAIS: usar a SERVICE ROLE key (ignora RLS) — a ingestão é processo de
servidor privilegiado, não leitura de cliente. Nunca a anon key aqui.

Mapeamento para a API do PostgREST/supabase-py v2:
  - upsert(on_conflict=...)                  → resolução por chave de conflito.
  - upsert(ignore_duplicates=True)           → INSERT que ignora duplicata (a
    resposta traz só as linhas de fato inseridas → conta = len(data)). É o
    comportamento append-only que o bronze exige (coleta é evento, não estado).
  - select('*').match(onde).limit(1)         → seleção pontual.
"""

from __future__ import annotations

from typing import Any, Sequence

# Chave de conflito do bronze (constraint `bronze_unico_por_coleta`). O único
# uso de `inserir_ignorando_conflito` é a persistência de bronze.
BRONZE_CONFLITO = "fonte,id_na_fonte,hash_conteudo"


class BancoSupabase:
    """Implementa `ClienteBanco` sobre um cliente supabase-py injetado."""

    def __init__(self, client: Any):
        self._c = client

    def upsert(
        self, tabela: str, linhas: list[dict], *, conflito: str
    ) -> list[dict]:
        resp = (
            self._c.table(tabela)
            .upsert(list(linhas), on_conflict=conflito)
            .execute()
        )
        return list(getattr(resp, "data", None) or [])

    def inserir_ignorando_conflito(
        self, tabela: str, linhas: Sequence[dict]
    ) -> int:
        linhas = list(linhas)
        if not linhas:
            return 0
        resp = (
            self._c.table(tabela)
            .upsert(linhas, on_conflict=BRONZE_CONFLITO, ignore_duplicates=True)
            .execute()
        )
        # Com ignore-duplicates, a resposta traz apenas as linhas inseridas —
        # as ignoradas ficam de fora. len = quantas de fato entraram.
        return len(getattr(resp, "data", None) or [])

    def selecionar_um(self, tabela: str, onde: dict) -> dict | None:
        resp = (
            self._c.table(tabela)
            .select("*")
            .match(dict(onde))
            .limit(1)
            .execute()
        )
        dados = list(getattr(resp, "data", None) or [])
        return dados[0] if dados else None


def criar_banco_supabase(url: str, key: str) -> BancoSupabase:
    """Cria o adaptador com o cliente Supabase real.

    Import TARDIO de `supabase`: só é exigido aqui, no deploy. `key` deve ser a
    service role key. Requer as variáveis de ambiente `SUPABASE_URL` e
    `SUPABASE_SERVICE_KEY` (ver .env.example) resolvidas pelo chamador.
    """
    from supabase import create_client  # import tardio — ver docstring do módulo

    return BancoSupabase(create_client(url, key))
