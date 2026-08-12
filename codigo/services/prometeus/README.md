# Prometeus — serviço (Etapa 2.1 da Onda 2)

Camada de **acesso ao dado** do agente de IA. Expõe consultas **seguras e
parametrizadas** à camada ouro do Supabase (views `*_publico`/`*_publica`) como
**ferramentas MCP**. O modelo (Etapa 2.2) escolhe qual ferramenta e os parâmetros;
a redação da consulta é fixa aqui (Metodologia §21). **Aqui não há IA.**

Cada ferramenta devolve dado **+ proveniência** (`source`/`source_url`/`synced_at`),
**completude** (janela + último registro) e **ressalvas**, honrando o contrato de
resposta da Metodologia (§20). Nada é servido sem fonte.

## Estrutura

**Etapa 2.1 — acesso ao dado (as ferramentas):**
- `gateway.py` — `Consulta`/`Filtro` + protocolo `Gateway`.
- `resultado.py` — `Resultado`/`Proveniencia`/`Completude` + `recusar()`.
- `consultas.py` — as consultas seguras (puras, testáveis sem rede).
- `supabase_gateway.py` — gateway real (PostgREST; `httpx` só em runtime).
- `servidor_mcp.py` — expõe as consultas como ferramentas MCP (requer `mcp`).

**Etapa 2.2 — o cérebro (o agente ReAct):**
- `contrato.py` — as 7 regras do contrato de resposta (§20) como system prompt.
- `ferramentas.py` — registro das ferramentas (esquema p/ o modelo + despacho).
- `modelo.py` — `Modelo` (porto) + `ModeloClaude` (Sonnet 5 + fall-back Opus 4.8).
- `agente.py` — o loop ReAct: escolhe/chama ferramentas e acumula fontes/ressalvas.
- `api.py` — endpoint HTTP (`POST /perguntar`) sobre o agente.

- `tests/` — suíte sem rede (modelo fake + FakeGateway).

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

## Rodar ao vivo (execução real — Etapas 2.2/2.4)

Variáveis de ambiente: `SUPABASE_URL`, `SUPABASE_ANON_KEY` (lê só as views ouro,
via RLS/GRANT) e `ANTHROPIC_API_KEY` (com teto de gasto no painel Anthropic).

**Endpoint de chat (a face conversacional):**
```
pip install fastapi uvicorn anthropic httpx
uvicorn api:app --reload
# POST http://localhost:8000/perguntar  {"pergunta": "quanto o deputado X gastou em 2024?"}
```

**Servidor MCP (interface reutilizável das ferramentas):**
```
pip install "mcp[cli]" httpx
py servidor_mcp.py
```

> Nota de arquitetura: as ferramentas vivem em `consultas.py` e são a fonte única.
> `servidor_mcp.py` as expõe como **servidor MCP** (interface reutilizável — outros
> consumidores, DaaS futuro). O agente de chat, por ser co-localizado, usa o mesmo
> registro **em processo** (via `ferramentas.py`) — sem pagar um ida-e-volta MCP a
> si mesmo. Trocar o agente para consumir via cliente MCP é um adaptador fino, se
> um dia o agente e as ferramentas forem separados.
