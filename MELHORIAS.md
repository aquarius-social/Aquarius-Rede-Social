# MELHORIAS.md — backlog de refinamento pós-MVP

Lista viva de **tarefas inacabadas ou que precisam de refinamento**. A ideia
(decisão do usuário): **primeiro fechar o MVP**, depois voltar aqui e refinar a
plataforma item a item. Não é ordem de execução — é o mapa do que ficou em aberto.

Marcação: 🔴 grande (onda própria) · 🟡 médio · 🟢 pequeno · ⛔ bloqueado por
(Pro/ingestão). Quando um item for feito, mover para o `ESTADO_ATUAL.md` como
concluído e riscar aqui.

---

## 1. Dados & Ingestão

- 🔴 ⛔Pro — **Convênios/transferências: o "objeto" real das emendas.** Para onde
  o dinheiro foi de fato (beneficiário, objeto, convênio). Escopo detalhado já no
  `ESTADO_ATUAL.md` (seção PLANEJADO). Fonte: `/convenios` e `/transferencias` do
  Portal (mesma chave). Volume alto → provável Supabase Pro. **É o item que fecha
  o "para onde foi o dinheiro" — alta prioridade pós-MVP.**
- 🔴 ⛔Pro — **Áreas legislativas no app** (Proposições, Votações, Presença,
  Discursos, Órgãos, Agenda). Hoje são **placeholder** nas abas do perfil. Já
  foram ingeridas antes, mas saíram da base de dinheiro por espaço. Reingerir
  (precisa de folga/Pro) e ligar as abas ao dado real.
- 🟡 ⛔Pro — **Senado CEAPS 2026** — o único ano que ficou de fora (espaço). Incluir
  quando houver folga.
- 🔴 ⛔Pro — **Bicameral legislativo completo** (matérias/votações/discursos do
  Senado) — desligados na base de dinheiro; ligar no Pro.

## 2. Curadoria & qualidade de dados

- 🟡 — **Autores de emenda sem perfil (219 pessoas).** Resolver por convergência
  (`sem_titulos` + UF, §5.3), com revisão humana do resíduo. Custo ~0 de espaço
  (UPDATE). Fecharia ~2.365 emendas hoje `null`.
- 🟢 — **Vínculo do senador 5718 (§4).** Períodos partidários sobrepostos na fonte
  → uma linha de `vinculo_temporal` recusada. Refinar `construir_vinculos_senado`.
- 🟡 — **Linhagem de partidos (§4).** Siglas históricas (PMDB→MDB) e fusões
  (DEM/PSL→UNIÃO) — curadoria; `partido_id` de períodos antigos fica null.
- 🟡 — **Suplente em exercício (§6.4).** Vincular o suplente à cadeira
  (cross-referência ao titular).
- 🟢 — **Presidência de votação (Artigo 17).** Hoje computada, sem coluna/tabela
  alvo — persistir.
- 🟢 — **Divergência da migration 0008** (arquivo diz `perfil_id`; banco e código
  usam o correto). Alinhar o arquivo via migration nova (regra 5).

## 3. App & UX

- 🟡 — **Detalhe da emenda: acesso ao Portal.** Manter link + instrução curta
  (decidido). Refinar de verdade quando os convênios entrarem (aí o objeto fica
  dentro do app e o link deixa de ser necessário).
- 🟡 — **Stats do topo do perfil** (Presença / Aliado / Proposições) — hoje
  **placeholder**. Ligar ao dado real (proposições dá pra contar da Câmara já).
- 🔴 — **Outras telas do protótipo** — proposição, partido, comissão, frente, feed
  cívico, busca, onboarding, configurações, editar perfil (todas no Claude Design).
- 🔴 — **Prometeus / IA** — os botões "Perguntar à IA" são placeholder; integrar
  o agente.
- 🟢 — **tema.ts → `@aquarius/ui`.** Hoje os tokens são cópia local (para o 1º
  vertical rodar sem monorepo). Ligar o Metro ao workspace e importar do pacote.
- 🟡 — **Shell de navegação** — bottom nav funcional, header, deep links (hoje o
  app é lista → perfil).

## 4. Infra & segurança

- 🟡 — **Free → Pro (Supabase).** A base de dinheiro está no teto do Free. Ligar
  áreas pesadas (legislativo, bronze, convênios) exige o Pro (8 GB).
- 🟢 — **Loader de `.env`** — parar de colar chave na mão a cada rodada de ingestão.
- 🟢 — **Agendador automático** — pôr os secrets Supabase no repo para o
  `ingestao.yml` rodar sozinho 2×/dia. (Rotação de chave: feita ✅.)
