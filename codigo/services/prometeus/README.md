# Prometeus — serviço (Etapa 2.1 da Onda 2)

Camada de **acesso ao dado** do agente de IA. Expõe consultas **seguras e
parametrizadas** à camada ouro do Supabase (views `*_publico`/`*_publica`) como
**ferramentas MCP**. O modelo (Etapa 2.2) escolhe qual ferramenta e os parâmetros;
a redação da consulta é fixa aqui (Metodologia §21). **Aqui não há IA.**

Cada ferramenta devolve dado **+ proveniência** (`source`/`source_url`/`synced_at`),
**completude** (janela + último registro) e **ressalvas**, honrando o contrato de
resposta da Metodologia (§20). Nada é servido sem fonte.

## Estrutura

- `gateway.py` — `Consulta`/`Filtro` + protocolo `Gateway`.
- `resultado.py` — `Resultado`/`Proveniencia`/`Completude` + `recusar()`.
- `consultas.py` — as ferramentas (puras, testáveis sem rede).
- `supabase_gateway.py` — gateway real (PostgREST; `httpx` só em runtime).
- `servidor_mcp.py` — expõe as consultas como ferramentas MCP (requer `mcp`).
- `tests/` — suíte sem rede (FakeGateway).

## Ferramentas (primeira leva — o que já está servido no banco)

`buscar_parlamentar` · `buscar_partido` · `despesas_parlamentar` ·
`total_despesas` · `emendas_por_municipio` · `emendas_por_autor_nome` ·
`agenda_eventos`.

Ampliar cobertura = **adicionar uma ferramenta** (uma gaveta), sem trocar o agente.

## Rodar os testes (sem rede, sem dependências)

```
cd codigo/services/prometeus
py -m unittest discover -s . -t .
```

## Rodar o servidor MCP (execução real — Etapas 2.2/2.4)

```
pip install "mcp[cli]" httpx
export SUPABASE_URL=...            # projeto Supabase
export SUPABASE_ANON_KEY=...       # chave anon (lê só as views ouro, via RLS/GRANT)
py servidor_mcp.py
```
