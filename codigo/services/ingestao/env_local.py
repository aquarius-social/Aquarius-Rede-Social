"""Carregador de `.env` local — o jeito PADRÃO de passar segredos à ingestão.

Padrão fixo (ver `RUNBOOK-BACKFILL.md` e a memória `metodo-padrao-ingestao`): os
segredos vivem num arquivo `.env` ao lado dos entrypoints
(`codigo/services/ingestao/.env`, já no `.gitignore`) — NUNCA colados à mão no
terminal nem no chat. `run_ingestao.py` e `run_backfill.py` chamam `carregar_env()`
no início de `main()`, antes de ler `os.environ`.

Regras (compatíveis com o CI, que injeta segredos por variável de ambiente):
- `NOME=valor` por linha; linhas em branco e as iniciadas por `#` são ignoradas.
- Aspas simples/duplas ao redor do valor são removidas.
- Uma variável JÁ presente no ambiente do processo NÃO é sobrescrita — o ambiente
  real manda; o `.env` é só o default local. Assim o CI (sem `.env`, com variáveis
  de ambiente) continua idêntico.
- Arquivo ausente: no-op silencioso.

Só stdlib — nenhuma dependência nova (a única não-stdlib do serviço é `supabase`).
"""
from __future__ import annotations

import os
from pathlib import Path


def carregar_env(caminho: str | os.PathLike[str] | None = None) -> dict[str, str]:
    """Popula `os.environ` a partir do `.env` (sem sobrescrever o que já existe).

    Devolve o dict `{nome: valor}` lido do arquivo (para log/teste). NÃO imprime
    valores — quem chama decide o que logar.
    """
    caminho = Path(caminho) if caminho is not None else Path(__file__).with_name(".env")
    lidos: dict[str, str] = {}
    try:
        conteudo = caminho.read_text(encoding="utf-8")
    except FileNotFoundError:
        return lidos
    for linha in conteudo.splitlines():
        crua = linha.strip()
        if not crua or crua.startswith("#") or "=" not in crua:
            continue
        nome, _, valor = crua.partition("=")
        nome = nome.strip()
        if not nome:
            continue
        valor = valor.strip().strip('"').strip("'")
        lidos[nome] = valor
        os.environ.setdefault(nome, valor)  # ambiente real tem prioridade
    return lidos
