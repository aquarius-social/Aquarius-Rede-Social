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

import time
from typing import Any, Callable, Sequence

# Chave de conflito do bronze (constraint `bronze_unico_por_coleta`). O único
# uso de `inserir_ignorando_conflito` é a persistência de bronze.
BRONZE_CONFLITO = "fonte,id_na_fonte,hash_conteudo"

# Tamanho do lote de upsert. O PostgREST aceita muitas linhas por requisição;
# lotear corta drasticamente o nº de requisições (uma ingestão histórica faz
# milhares de linhas por área) — o que evita esgotar a conexão HTTP/2.
LOTE_UPSERT = 500

# Erros de TRANSPORTE (não de dados): a conexão HTTP/2 do supabase-py é encerrada
# pelo servidor após muitos streams; a próxima chamada reabre. Retry só para
# estes — erro de constraint (dado) sobe na hora para quem chama tratar.
_ERROS_CONEXAO = frozenset({
    "RemoteProtocolError", "ConnectError", "ConnectTimeout", "ReadError",
    "ReadTimeout", "WriteError", "PoolTimeout", "ConnectionTerminated",
})


def _e_erro_conexao(e: Exception) -> bool:
    if type(e).__name__ in _ERROS_CONEXAO:
        return True
    txt = str(e)
    return "ConnectionTerminated" in txt or "Server disconnected" in txt


# Erros TRANSITÓRIOS de gateway/proxy: o Cloudflare na frente do Supabase às vezes
# devolve 502/503/504 (HTML de erro), que o postgrest converte em APIError. NÃO é
# erro de dado — a re-tentativa resolve. Sem isto, UM único 502 no meio de dezenas
# de milhares de reads derrubava o ano inteiro (visto no backfill de atividade:
# um read de id_externo por voto → o ano de 2023 abortou num 502 avulso).
_TEXTO_GATEWAY = (
    "bad gateway", "gateway time-out", "gateway timeout",
    "service unavailable", "temporarily unavailable",
)
_CODIGOS_GATEWAY = ("502", "503", "504")


def _e_gateway_transitorio(e: Exception) -> bool:
    txt = str(e).lower()
    if any(t in txt for t in _TEXTO_GATEWAY):
        return True
    codigo = getattr(e, "code", None)
    if str(codigo) in _CODIGOS_GATEWAY:
        return True
    # postgrest.APIError carrega o código dentro do texto do dict ({'code': 502}).
    return any(f"'code': {c}" in txt or f'"code": {c}' in txt for c in _CODIGOS_GATEWAY)


def _e_transitorio(e: Exception) -> bool:
    return _e_erro_conexao(e) or _e_gateway_transitorio(e)


def _com_retry(fn: Callable[[], Any], *, tentativas: int = 5, espera: float = 1.0) -> Any:
    """Executa `fn`, repetindo só em erro TRANSITÓRIO — conexão HTTP/2 encerrada
    ou gateway 5xx do proxy (com backoff). Erros de dado (constraint, etc.) sobem
    imediatamente para quem chama tratar."""
    ultima: Exception | None = None
    for i in range(tentativas):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            if not _e_transitorio(e):
                raise
            ultima = e
            time.sleep(espera * (i + 1))
    assert ultima is not None
    raise ultima


class BancoSupabase:
    """Implementa `ClienteBanco` sobre um cliente supabase-py injetado."""

    def __init__(self, client: Any, *, lote: int = LOTE_UPSERT):
        self._c = client
        self._lote = lote

    def upsert(
        self, tabela: str, linhas: list[dict], *, conflito: str
    ) -> list[dict]:
        linhas = list(linhas)
        if not linhas:
            return []
        out: list[dict] = []
        for i in range(0, len(linhas), self._lote):
            lote = linhas[i:i + self._lote]
            resp = _com_retry(lambda l=lote: (
                self._c.table(tabela).upsert(l, on_conflict=conflito).execute()))
            out.extend(list(getattr(resp, "data", None) or []))
        return out

    def inserir_ignorando_conflito(
        self, tabela: str, linhas: Sequence[dict]
    ) -> int:
        linhas = list(linhas)
        if not linhas:
            return 0
        total = 0
        for i in range(0, len(linhas), self._lote):
            lote = linhas[i:i + self._lote]
            resp = _com_retry(lambda l=lote: (
                self._c.table(tabela)
                .upsert(l, on_conflict=BRONZE_CONFLITO, ignore_duplicates=True)
                .execute()))
            # Com ignore-duplicates, a resposta traz só as linhas inseridas.
            total += len(getattr(resp, "data", None) or [])
        return total

    def selecionar_um(self, tabela: str, onde: dict) -> dict | None:
        resp = _com_retry(lambda: (
            self._c.table(tabela).select("*").match(dict(onde)).limit(1).execute()))
        dados = list(getattr(resp, "data", None) or [])
        return dados[0] if dados else None

    def selecionar_muitos(
        self, tabela: str, onde: dict | None = None, colunas: str = "*",
        *, ordem: str | None = None,
    ) -> list[dict]:
        """Lê todas as linhas paginando de `lote` em `lote` (o PostgREST limita a
        página; sem paginar, tabelas grandes vêm truncadas em silêncio). `onde`
        None/{} = tabela inteira; `ordem` estabiliza a paginação."""
        filtro = dict(onde or {})
        tam = self._lote
        inicio = 0
        saida: list[dict] = []
        while True:
            def _pag(ini=inicio):
                q = self._c.table(tabela).select(colunas)
                if filtro:
                    q = q.match(filtro)
                if ordem:
                    q = q.order(ordem)
                return q.range(ini, ini + tam - 1).execute()
            pagina = list(getattr(_com_retry(_pag), "data", None) or [])
            saida.extend(pagina)
            if len(pagina) < tam:
                break
            inicio += tam
        return saida


def criar_banco_supabase(url: str, key: str) -> BancoSupabase:
    """Cria o adaptador com o cliente Supabase real.

    Import TARDIO de `supabase`: só é exigido aqui, no deploy. `key` deve ser a
    service role key. Requer as variáveis de ambiente `SUPABASE_URL` e
    `SUPABASE_SERVICE_KEY` (ver .env.example) resolvidas pelo chamador.
    """
    from supabase import create_client  # import tardio — ver docstring do módulo

    return BancoSupabase(create_client(url, key))
