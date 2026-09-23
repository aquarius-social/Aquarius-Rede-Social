# Relatório de Desenvolvimento — Aquarius

**Data:** 2026-08-10 · **Versão:** 1.0 · **Autor:** consolidação automática (Claude Code)

Snapshot completo do estado do produto: o que está pronto, o que falta, as fases
ainda não desenvolvidas e as melhorias possíveis em **todas** as camadas — dados,
ingestão, banco, backend/IA, app, admin, infra e produto.

> **Como este documento se relaciona com os outros:**
> - `ESTADO_ATUAL.md` = estado vivo, atualizado a cada entrega (a "verdade do dia").
> - `MELHORIAS.md` = backlog granular por área (A–I) com marcação de tamanho/bloqueio.
> - `PLANO.md` = plano em ondas + hierarquia de fontes + decisões em aberto.
> - **Este relatório** = fotografia consolidada e legível de tudo acima, num lugar só.
>
> Onde houver conflito, valem os documentos-fonte (`.docx` de Metodologia/Concepção +
> protótipo). Números de dado vêm das views ouro (ver Visão geral do admin).

**Legenda de status:** ✅ pronto · 🟨 parcial / em uso com ressalva · ⬜ não iniciado
**Tamanho da tarefa:** 🔴 grande (onda própria) · 🟡 médio · 🟢 pequeno
**Bloqueio:** ⛔Pro (precisa Supabase Pro/espaço) · ⛔fonte (depende de fonte/chave) ·
⛔IA (depende do agente) · ⛔escala (só faz sentido com base de usuários)

---

## 1. Sumário executivo

O Aquarius é uma **rede social cívica** que traduz dados oficiais do Congresso
Nacional em conteúdo neutro e rastreável, com um agente de IA (Prometeus) para
consulta analítica. Hoje o produto está assim:

| Camada | Estado | Resumo |
|---|---|---|
| **Dados & ingestão** | 🟨 | Fundação de identidade + pipeline de 3 camadas de pé. 5/9 áreas da Câmara com coletor; **servidos no banco**: despesas, emendas, eventos (o resto está truncado por espaço no Free). |
| **Banco (Supabase)** | 🟨 | 18 migrations (identidade → ouro → despesas/emendas/eventos → situação → admin_roles → follows). No teto do plano Free. |
| **App (Expo/React Native)** | ✅ | 15 telas navegáveis ponta a ponta, dado real onde existe. Modo escuro, header custom e sistema de "seguir" recém-concluídos. |
| **Admin (Next.js)** | 🟨 | Console com 14 telas fiéis ao protótipo (dado real onde há, placeholder marcado onde não) + RBAC com gate de login. Ainda em `localhost`, sem deploy. |
| **Agente Prometeus (IA)** | ⬜ | **Não construído.** As telas existem com placeholder honesto; o serviço Python + contrato de resposta é a próxima grande peça. |
| **Social / editorial** | ⬜ | Sem posts de IA, sem curtir/comentar, sem stories, sem notificações (dependem do agente + tabelas). |
| **Monetização / DaaS** | ⬜ | Premium e DaaS não iniciados (DaaS só faz sentido em escala de centenas de milhares de consentidos). |

**Números do repositório (2026-08-10):** 104 commits · 18 migrations SQL · ~78
arquivos Python de ingestão · **300 testes** de ingestão passando (sem rede) · 15
telas de app + 14 de admin · monorepo `apps/{app,admin}` + `packages/{types,ui}` +
`services/ingestao` + `supabase`.

**Contagens reais servidas** (views ouro, ver Visão geral do admin): ~623
parlamentares com mandato vigente, 22 partidos, ~19,5 mil emendas, 89 comissões,
+ eventos de agenda. *(O app mostra rótulos do protótipo em alguns cards; a fonte
da verdade das contagens é a camada ouro.)*

---

## 2. Arquitetura & stack

### 2.1 Monorepo (`codigo/`)

```
codigo/
├── apps/
│   ├── app/        Expo (React Native) — o app do cidadão. TypeScript.
│   └── admin/      Next.js 14 (App Router) — o console operacional. TypeScript.
├── packages/
│   ├── types/      Tipos TS compartilhados (modelo de dados, contrato do post).
│   └── ui/         Tokens de design + preset Tailwind (fonte da verdade visual).
├── services/
│   └── ingestao/   Coletores em Python 3.12 (Câmara/Senado/Portal) + pipeline.
└── supabase/
    └── migrations/ 21 migrations SQL (0001 … 0021; 0019 autor_nome_norm, 0020–0021 bancadas).
```

### 2.2 Decisões de stack (travadas — não reabrir sem discussão)

| Área | Decisão | Motivo |
|---|---|---|
| Banco / Auth / Storage | **Supabase** (Postgres gerenciado + Auth + RLS) | Não usar Postgres/Redis self-hosted. |
| Backend de dados e IA | **Python 3.12+** | Ecossistema de dados/LLM. |
| App | **React Native (Expo)** | Um código, iOS+Android+web. |
| Admin | **Next.js (App Router)** | Console web operacional. |
| API | **Sem `apps/api` genérico** | Leitura vai direto ao Supabase com RLS; servidor próprio só p/ DaaS, IA, ações admin e ingestão. |
| Login | **OTP por e-mail primeiro** | WhatsApp/SMS em paralelo (habilitação Meta é lenta). |
| Ordem | **Premium/billing antes do DaaS** | DaaS só é vendável na casa de centenas de milhares de consentidos (k-anonimato). |

### 2.3 Princípios inegociáveis (guardam a qualidade)

1. Todo post/story cita fonte oficial (`source` + `source_url` + `synced_at`) — sem isso, não publica.
2. Neutralidade: posts em terceira pessoa, factuais; a IA contextualiza, não opina.
3. DaaS só agrega. Zero PII exportada. k-anonimato + consentimento na borda.
4. Perfil opcional é opt-in (renda/escolaridade/ocupação são nudge, nunca obrigatório).
5. `confianca_ia < 0.65` **ou** `null` → revisão humana antes de publicar.
6. Identidade resolvida **na data do fato**, nunca no presente (voto de 2021 resolve o partido de 2021).

---

## 3. Progresso por Onda (o plano em fases)

O `PLANO.md` organiza o projeto em ondas, com a regra "nenhuma onda começa antes de
a anterior estar de pé". Estado de cada uma:

| Onda | Escopo | Status | O que falta |
|---|---|---|---|
| **0 — Fundação** | Resolução de identidade (`profiles`, `id_externo`, `vinculo_temporal`, `partido`), `packages/types`, `packages/ui` | ✅ | Verificar layout do código de autor de emenda contra a fonte viva; escolher ferramenta de workspace do monorepo. |
| **1 — Núcleo cívico** | 9 áreas de dado (Câmara + Senado) + junção bicameral, pipeline 3 camadas, auth/onboarding, WhatsApp Business em paralelo | 🟨 | 5/9 áreas com coletor; **reingerir** as truncadas (proposições, votações, tramitações, discursos); construir coletor de **presença**; iniciar burocracia do WhatsApp. |
| **1.5 — App de leitura** | Explorar, perfis polimórficos, proposição, busca, interesses, calendário | 🟨 | Tela de **Proposição** e **abas legislativas** do perfil (dependem de reingerir dado); busca dedicada. |
| **2 — Inteligência derivada** | Prometeus (contrato de 7 regras + banco de perguntas com gabarito), posts em 3ª pessoa, stories, cache de resumos + Torre de Controle (revisão editorial, feed/posts, stories, pipelines) | ⬜ | **Tudo o essencial da IA.** Admin já tem as telas de operação prontas (fachada); falta o motor. |
| **2.5 — Camada social** | Feed personalizado, stories, curtidas, comentários, seguir, compartilhar, notificações + moderação | 🟨 | **"Seguir" pronto**; falta curtir/comentar/compartilhar, stories, notificações e a moderação real. |
| **2.75 — Instrumentação & monetização** | Eventos de engajamento (vinculados a consentimento), premium, KYC, selo azul | ⬜ | Nada iniciado. Perfil opt-in já é coletado, mas não instrumentado. |
| **3 — Enriquecimento externo & DaaS** | Dados eleitorais/patrimônio/judiciário sob demanda + motor de audiências (k-anonimato) | ⬜ | Depende da decisão de **k** e do tamanho real da base consentida. |

**Resumo:** Ondas 0 e 1.5 substancialmente entregues; Onda 1 a meio caminho (código
pronto, dado truncado por espaço); Ondas 2, 2.75 e 3 não iniciadas; Onda 2.5 começou
pelo "seguir".

---

## 4. O que está PRONTO (detalhado)

### 4.1 Dados & ingestão (Ondas 0 e 1)

**Fundação de identidade (Onda 0).** `profiles` como tabela-mãe de toda entidade
seguível (parlamentar/partido/comissão/frente = o mesmo objeto polimórfico);
`id_externo` mapeando cada perfil para os ids da Câmara/Senado/código de autor
orçamentário **com método e grau de confiança por ligação**; `vinculo_temporal`
versionando partido/UF/cadeira por período; `partido` com histórico de siglas.
Quatro invariantes viram **constraint no banco** (recusa exige divergência; grau
"direto" exige ≥2 sinais; ninguém ocupa duas cadeiras na mesma casa ao mesmo tempo;
fonte com canário não validado não ativa). O **resolvedor** roda em dois tempos
(condições necessárias eliminam candidatos → só então soma evidências), como a
Metodologia §5.3 fixa.

**Pipeline de 3 camadas (Onda 1).** Bronze (cru, imutável) → prata (tratado) → ouro
(servido, sem PII, com proveniência e frescor). Portão de qualidade + quarentena com
motivo entre camadas. Coletor HTTP distingue **instabilidade de falha** (5xx/429/timeout
com retry; 4xx/DNS não). **Canário** valida a estrutura da fonte antes de qualquer OK.
Dedup opera sobre **conteúdo, não id** (detecta edição retroativa).

**Áreas de dado (5/9 da Câmara com coletor + Senado):**

| Área | Coletor | No banco (servido) |
|---|---|---|
| A · Despesas (CEAP) Câmara | ✅ | ✅ 2023–2026 |
| A · Despesas (CEAPS) Senado | ✅ | 🟨 2023–2025 (falta 2026) |
| B · Proposições (Câmara+Senado) | ✅ | ⬜ truncado |
| C · Votações + votos nominais | ✅ | ⬜ truncado |
| D · Tramitações | ✅ | ⬜ truncado |
| E · Presença | ⬜ **sem coletor** | ⬜ |
| F · Emendas parlamentares | ✅ | ✅ 2023–2026 (bicameral) |
| G · Discursos | ✅ | ⬜ truncado |
| H · Eventos/agenda | ✅ | ✅ **no ar** (Calendário consome) |
| Senado (junção bicameral) | ✅ | 🟨 |

**Verificação:** 300 testes de ingestão passando sem rede (`py -m unittest discover`);
os pontos de contato com a fonte foram, além disso, conferidos contra a API viva.

### 4.2 Banco (Supabase) — 18 migrations

`0001` identidade · `0002` camadas cívicas (bronze+prata) · `0003` votação nominal ·
`0004` placar nulável · `0005` vínculo upsert · `0006` camada ouro (views servidas) ·
`0007` ouro coletivos (comissão/frente) · `0008` despesas CEAP · `0009` emendas ·
`0010` Senado · `0011` discursos · `0012` eventos · `0013–0016` situação do
parlamentar (licenciado/suplente, titular opcional) · `0017` **admin_roles (RBAC)** ·
`0018` **follows (seguir)**.
Regra de disciplina respeitada: **correções vêm em migration nova**, nunca editando
antiga (preserva histórico + bancos em produção).

### 4.3 App (Expo / React Native) — 15 telas

**Telas (todas navegáveis, dado real onde existe):** Splash · Login (OTP e-mail +
gate de sessão) · Onboarding (gate por estado + opt-in LGPD) · Feed v1 (destaques de
dinheiro reais, sem IA) · Explorar (hub) + Listagem filtrável · Perfil parlamentar
(dinheiro real) · Partido · Comissão · Frente · Prometeus (lista + chat, placeholder
honesto) · Interesses · Calendário (agenda real) · Configurações (+ logout) · Editar
perfil. BottomNav 100% navegável. Fonte Inter + logo fiéis ao protótipo.

**Entregas recentes (esta rodada):**
- **Fidelidade ao protótipo** — auditoria PNG-vs-código das 15 telas; correções
  seguras de texto/rótulo aplicadas; divergências que dependem de dado/feature
  documentadas em vez de "fingidas".
- **Modo escuro** — sistema de tema (`lib/theme.tsx` + `lib/tema.ts`), com dois tokens
  semânticos (`texto`, `cartao`) resolvendo a sobrecarga de `navy`/`white`. Todas as
  telas + `base.tsx` migradas; toggle Automático/Claro/Escuro em Configurações
  (persiste em AsyncStorage). Verificado em runtime.
- **Header custom (AqHeader)** — logo+avatar (abas) / voltar+título+avatar (detalhe),
  com safe-area e tema; substitui o header nativo do `@react-navigation`.
- **Sistema de "seguir"** — tabela `follows` (0018) + `useFollows` (estado otimista) +
  botão Seguir persistido nas 4 telas de entidade; onboarding/Interesses/Configurações
  unificados na tabela; Feed "Seguindo" filtra os destaques por quem se segue.

### 4.4 Admin (Next.js) — 14 telas + RBAC

**Fundação:** scaffolding Next.js 14 (App Router) + tema ADM_DARK/ADM_LIGHT com toggle
(dark default) + shell (sidebar 16 itens em 5 seções + topbar). Roda em `localhost:3001`.

**Telas (fiéis ao protótipo, via adaptador de dados — dado real onde há, placeholder
marcado com selo onde não):** Visão geral (KPIs reais) · Pipelines · Feed & Posts ·
Stories da IA · Revisão editorial · Moderação · Prometeus IA (telemetria) · Usuários ·
Engajamento · Audiências/DaaS · Feature flags · Auditoria LGPD · Equipe & Permissões ·
Configurações.

**Padrão de adaptador de dados:** dados demo centralizados em `lib/demo*`, dados reais
em `lib/dados`/`lib/pipelines`, telas "congeladas" — o futuro é trocar o corpo das
funções, não as telas. Fidelidade marcada com `<Selo tipo="amostra"|"real"/>`.

**RBAC (0017):** tabela `admin_roles` + RLS "admin lê a própria linha" + `is_admin()`.
Gate de login (magic link) com bypass de dev (`NEXT_PUBLIC_ADMIN_DEV_BYPASS`, nunca em
produção).

---

## 5. O que FALTA + melhorias possíveis (por área)

> Esta é a seção de "possíveis melhorias em tudo". Espelha o backlog `MELHORIAS.md`
> (A–I), consolidado e priorizado.

### 5.A — Ingestão de dados

- 🔴 ⛔Pro — **Reingerir áreas truncadas** (proposições, votações + votos nominais,
  tramitações, discursos): o coletor existe; foram truncadas para caber a base de
  dinheiro no Free. É o que destrava a tela de Proposição e as abas legislativas do perfil.
- 🔴 ⛔fonte — **Área E · Presença** — **não há coletor.** Construir (Câmara+Senado):
  sessões convocadas/presentes/justificadas por legislatura.
- 🟡 ⛔Pro — **Despesas Senado 2026** (saiu por espaço).
- 🔴 ⛔fonte — **Convênios / transferências** (o "objeto" das emendas: para onde o
  dinheiro foi de fato — beneficiário, objeto). Coletor **novo** + migration. **Alta
  prioridade pós-MVP.**
- 🔴 ⛔fonte — **Siga Brasil / orçamento federal (Senado)** — execução orçamentária
  ampla. Não iniciada.
- 🟢 — **Agendador automático** — hoje a ingestão é manual; automatizar 2×/dia para
  manter despesas/emendas/eventos frescos.

### 5.B — Cobertura temporal (backfill)

- 🔴 ⛔Pro — **Estender pré-2018** (legislatura 54ª e anteriores) por **config**, não
  on-demand.
- 🟡 — **Fechar a base 2018** (conferir cobertura de 2015–2018 onde faz sentido).
- 🟢 — **On-demand do legado antigo (v2)** — buscar sob demanda em vez de ingerir tudo.

### 5.C — Identidade, curadoria & qualidade

- 🟡 — **219 autores de emenda sem perfil** — resolver por convergência + revisão do
  resíduo (reflete no Feed como "Autoria em resolução").
- 🟡 — **Linhagem de partidos** — siglas históricas (PMDB→MDB) e fusões (DEM/PSL→UNIÃO):
  `partido_id` de períodos antigos fica null sem curadoria.
- 🟡 ⛔fonte — **Link titular↔suplente da Câmara** (via ordem de suplência do TSE) —
  para dar o "no lugar de X".
- 🟢 — **Presidência de votação** (Artigo 17) — hoje computada, sem coluna alvo.
- 🟢 — **Monitorar os 12 modos de falha + estados do contrato** (§19) em produção →
  vira painel no admin (Pipelines).

### 5.D — Banco de dados & armazenamento

- 🔴 — **Tabelas de conteúdo do Feed** — `post` (draft/publicado), `story`,
  `editorial_review` (status, motivo, revisor, confiança), `retratacao`. Hoje o Feed
  monta posts **em memória** a partir de emendas (sem persistência). É o que a IA
  preenche e o admin aprova.
- 🔴 — **Camada social** — `reacao` (like/dislike), `comentario`, `salvo`,
  `compartilhamento` + moderação. Hoje o app **não** tem engajamento (nada falso).
- 🔴 — **Tabela `notificacao`** (por usuário; origem: follow/evento/editorial).
- 🟡 — **Views/RPC ouro agregadas** — hoje o app agrega dinheiro **no cliente** (ok p/
  1 parlamentar, pesado p/ partido/bancada/feed). Criar views: dinheiro por partido,
  maiores emendas, rankings sob demanda.
- 🟡 — **`feature_flags`** e **`audit_log`** (tabelas) — toggles por ambiente/usuário e
  trilha LGPD.
- 🟢 — **Política de retenção do bronze** (hoje opt-out por espaço) e revisão de
  RLS/GRANTs das views conforme novas áreas entram.

### 5.E — Infra, pipeline & segurança

- 🟡 — **Free → Pro (Supabase)** — a base de dinheiro está no teto do Free (8 GB no
  Pro destrava legislativo, bronze, convênios, pré-2018). **Bloqueio central de várias
  frentes.**
- 🔴 — **Deploy do admin** (Vercel/Next) + variáveis + proteção de acesso.
- 🔴 — **Hospedagem do serviço de IA** (Python) + `ANTHROPIC_API_KEY` como secret de
  **servidor** (nunca no cliente) + limites de custo/rate.
- 🟢 — **CI verde** (testes + type-check a cada push), **loader de `.env`** e
  **agendador** da ingestão.
- 🟢 — **Bumpar Next** (patch de segurança) antes do deploy do admin.

### 5.F — App (Expo) — front-end

- 🔴 ⛔IA — **Feed editorial** — posts gerados pela IA (fonte + confiança + revisão).
  Hoje só há os destaques de dinheiro. Depende do agente + tabelas de post.
- 🟠 — **Seguir — refinos** — seguir proposições (PL) quando a área legislativa existir;
  **badges de "N novidades desde a última visita"** (precisa tracking de visita +
  conteúdo por entidade); botão Seguir também na Listagem/cards.
- 🟡 — **Camada social do Feed** — curtir/reagir/comentar/salvar/compartilhar + modais.
- 🟡 ⛔IA — **Stories** (rail + viewer).
- 🔵 — **Notificações (tela)**.
- 🔴 ⛔Pro — **Proposição (tela)** + **abas legislativas** do perfil (votações,
  presença, discursos, proposições) — hoje placeholder; dependem de reingerir dado.
- 🟢 — **Wire dos botões "Perguntar à IA"** nos perfis → abrir chat com contexto.
- 🟡 — **Login SMS + WhatsApp** (hoje só e-mail).
- 🟢 — **Fotos reais** dos parlamentares · **Splash/ícone nativos** + build EAS ·
  **Deep links** · **Acessibilidade**.
- 🟡 — **Robustez** — error boundaries por rota, estados de erro de rede + retry,
  paginação das listas grandes (~600 parlamentares, ~1443 frentes), cache.
- 🟢 — **`tema.ts` → `@aquarius/ui`** (hoje tokens são cópia local; ligar o monorepo).

**F.1 · Fidelidade ao protótipo (deferido, depende de dado/feature — não "fingido"):**
rail de stories e barra de engajamento social no Feed; Interesses como overview com
badges de "novidades"; strip semanal + filtros por tipo + favoritos no Calendário;
subtítulos de mandato/ementa/espectro/fundação nos perfis; "colegiados"→"permanentes"
e "frentes"→"ativas" no Explorar (precisa filtro por tipo/status); refinos da Listagem
(título dinâmico, ordenar, "mais filtros", lista unificada); badge + map-pin do Editar
perfil.

### 5.G — Admin (Next.js)

- 🔴 — **Ligar as telas ao real** conforme as tabelas nascem: Pipelines (status/estados
  §19 dos coletores), Feed & Posts + Stories + **Revisão editorial** (workbench
  gerado-vs-fonte — **freio de segurança do agente, pré-requisito para ligar a IA**),
  Moderação, Notificações, Feature flags, Auditoria LGPD, Equipe.
- 🔴 ⛔escala — **Engajamento** e **Audiências/DaaS** (dependem de coletar analytics +
  base consentida).
- 🔴 — **Backend do admin** — tabelas privilegiadas + server actions/RPC `service_role`
  para ações admin.
- 🔴 — **Deploy** (ver 5.E).

### 5.H — Agente Prometeus (IA) — a peça mais delicada

**Decisões abertas (alinhar antes):** arquitetura de acesso (ferramentas curadas ×
texto-para-SQL × híbrido), onde roda (serviço Python × edge function), e a chave da
Anthropic.

- 🔴 — **Serviço Python (FastAPI)** + endpoint que o app consome; modelo Claude via
  Anthropic API; chave como secret de servidor.
- 🔴 — **Acesso a dados** — ferramentas curadas e/ou SQL de leitura restrito às views
  ouro. Guarda-corpos contra injeção, timeouts, limite de custo/rate, cache.
- 🔴 — **Contrato de resposta (7 regras)** — `source` + `source_url` + `synced_at`
  sempre; terceira pessoa/neutro; sem opinião; **recusa honesta quando não há dado**;
  `confiança` calculada.
- 🔴 — **Geração de posts do Feed** → grava como `post` draft → **fila de revisão
  editorial (admin)** → publicação. `confiança < 0.65` ou null → revisão obrigatória.
- 🔴 — **Wire no app** (chat real substituindo o placeholder; resumos nos perfis).
- 🔴 — **Avaliação/testes do agente** — cada regra com caso que aceita **e** que recusa
  (disciplina da Metodologia §5.2).

### 5.I — Produto & monetização

- 🔴 — **Premium / billing** (vem **antes** do DaaS).
- 🔴 ⛔escala — **DaaS (dados agregados)** — só agrega, zero PII, k-anonimato +
  consentimento.
- 🟡 — **Usar o perfil opt-in** (renda/escolaridade/ocupação já coletados) de forma
  agregada/anônima.

---

## 6. Ações pendentes do usuário (fora do código)

1. **Rodar a migration `0018_follows`** no SQL editor do Supabase — sem ela, o "seguir"
   não persiste (a inserção falha e reverte). Arquivo: `codigo/supabase/migrations/0018_follows.sql`.
2. **Template de OTP do Supabase** — editar o e-mail "Magic Link" para incluir
   `{{ .Token }}` (código de 6 dígitos).
3. **Supabase Free → Pro** — quando for ligar as áreas pesadas (legislativo, bronze,
   convênios, pré-2018). É o bloqueio de várias frentes.
4. **WhatsApp Business** — iniciar a habilitação Meta **agora, em paralelo** (é a
   dependência externa mais longa do projeto).
5. **Decisões de produto pendentes** (ver §7).

---

## 7. Decisões em aberto (precisam de você)

| # | Decisão | Impacto |
|---|---|---|
| 1 | **Valor de k** do anonimato (com parecer jurídico) | Decide se o DaaS é produto de médio ou longuíssimo prazo (k=1000 ≈ 250 mil usuários; k=100 ≈ 25 mil). |
| 2 | **Dislike** (curtir/descurtir) | Implicação direta de schema; o heatmap de sentimento do admin depende disso. |
| 3 | **Dimensões do DaaS** | Concepção fala em "tema + região"; protótipo tem 8 dimensões (inclui renda/escolaridade). Diferença real de ambição e risco. |
| 4 | **Escopo do Prometeus no WhatsApp** | Se é canal de entrega, é uma superfície de produto inteira (sessão, custo/msg, moderação própria). |
| 5 | **Arquitetura de acesso a dados da IA** | Ferramentas curadas × texto-para-SQL × híbrido — define segurança e custo do agente. |

---

## 8. Riscos & limitações conhecidas

- **Teto do Supabase Free** — a base de dinheiro está no limite; várias áreas estão
  truncadas por isso (não por falta de código). Bloqueia legislativo, bronze,
  convênios, pré-2018.
- **IA ainda não existe** — todo o valor "editorial" (posts, stories, resumos, chat
  real) depende de uma peça delicada não iniciada, que carrega o contrato de resposta
  e a fila de revisão como freios de segurança.
- **Sem instrumentação de uso** — não há analytics de engajamento; as métricas do admin
  estão marcadas honestamente como "não medido ainda". Sem isso, Engajamento/DaaS não
  saem do lugar.
- **Ambiente de dev com RAM limitada** — Metro (Expo web) e `tsc` estouram memória
  quando app + admin rodam juntos; usar `--max-workers 1` e liberar RAM antes de
  verificar boot (ver memória do projeto).
- **Fidelidade vs. honestidade** — onde o protótipo mostra features/dados que ainda não
  temos (stories, engajamento social, mandato/ementa), a decisão foi **marcar
  placeholder** em vez de fingir. Isso é intencional e alinhado com a Metodologia.

---

## 9. Recomendação de próximos passos

Sequência sugerida (respeita as dependências e a ordem macro decidida — fechar app →
admin → agente → áreas pesadas/monetização):

1. **Curto prazo (destravar o que já foi feito):** rodar a migration 0018; testar o
   "seguir" ponta a ponta; wire dos botões "Perguntar à IA" nos perfis; Notificações
   (tela) assim que a tabela existir.
2. **Habilitar dado (exige Pro):** subir para o Supabase Pro e **reingerir** as áreas
   truncadas — destrava a tela de Proposição, as abas legislativas e rankings.
3. **A grande peça — Agente Prometeus:** serviço Python + contrato de 7 regras + banco
   de perguntas com gabarito, com a **Revisão editorial** do admin ligada como freio.
   Só então o Feed editorial e os Stories fazem sentido.
4. **Camada social + moderação** (curtir/comentar/compartilhar/notificar) — juntas, não
   depois; conteúdo político atrai abuso desde o dia 1.
5. **Instrumentação → Premium → DaaS**, nessa ordem, com a decisão de k tomada.
6. **Em paralelo desde já:** habilitação do WhatsApp Business (dependência externa mais
   longa) e o agendador automático da ingestão.

---

*Gerado a partir de `ESTADO_ATUAL.md`, `MELHORIAS.md`, `PLANO.md`, `ONDA-0/1-LEIA-ME.md`
e do histórico de git (104 commits). Onde este relatório e o código divergirem, o código
e os documentos-fonte mandam — atualize este arquivo na próxima grande entrega.*
