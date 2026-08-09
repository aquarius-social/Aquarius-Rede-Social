# MELHORIAS.md — backlog completo (dados, ingestão, banco, app, admin, IA)

Lista viva de **tarefas inacabadas ou que precisam de refinamento**, cobrindo a
plataforma inteira. Varredura completa: ingestão, banco/armazenamento, app (Expo),
**admin (Next.js)**, **agente Prometeus (IA)** e produto.

Marcação: 🔴 grande (onda própria) · 🟡 médio · 🟢 pequeno.
Bloqueio: ⛔Pro (precisa Supabase Pro por espaço) · ⛔fonte (depende de fonte/chave) ·
⛔IA (depende do agente) · ⛔escala (só faz sentido com base de usuários).
Quando concluir, mover para `ESTADO_ATUAL.md` e riscar aqui.

Ordem macro decidida com o usuário: **fechar telas do app → construir o admin
inteiro (a revisão editorial é freio de segurança do agente) → construir o agente
Prometeus** → depois ligar áreas ⛔Pro e monetização.

---

## A. Ingestão de dados — áreas (Metodologia §8–§17)

Os **coletores** da maioria já existem e passam nos testes; o que falta em muitos
é **reingerir no banco** (foram truncados para caber a base de dinheiro no Free) —
isso é ⛔Pro, não código novo.

- 🟢 — **Área A · Despesas Câmara (CEAP)** — ✅ no ar (2023–2026). Falta só manter
  atualizado (agendador).
- 🟡 ⛔Pro — **Área A · Despesas Senado (CEAPS)** — 2023–2025 no ar; **falta 2026**
  (saiu por espaço).
- 🔴 ⛔Pro — **Área B · Proposições (Câmara + Senado)** — coletor pronto; **truncado**
  da base atual. Reingerir para ligar a aba do app + a tela de Proposição.
- 🔴 ⛔Pro — **Área C · Votações + votos nominais (Câmara + Senado)** — coletor
  pronto; truncado. Reingerir (é o "como cada um votou").
- 🔴 ⛔Pro — **Área D · Tramitações (Câmara + Senado)** — coletor pronto; truncado.
- 🔴 ⛔fonte — **Área E · Presença** — **NÃO há coletor ainda.** Construir (Câmara +
  Senado): sessões convocadas/presentes/justificadas por legislatura.
- 🟢 — **Área F · Emendas parlamentares** — ✅ no ar (2023–2026, bicameral na fonte).
- 🔴 ⛔Pro — **Área G · Discursos (Câmara + Senado)** — coletor pronto; truncado.
- 🟢 — **Área H · Eventos/agenda (Câmara + Senado)** — ✅ **no ar** (o Calendário do
  app já consome `evento_publico`). Falta manter atualizado + cobrir janelas maiores.
- 🔴 ⛔fonte — **Convênios / transferências (o "objeto" das emendas)** — para onde o
  dinheiro foi de fato (beneficiário, objeto). Coletor NOVO + migration. Fonte:
  `/convenios` e `/transferencias` do Portal (mesma chave). Escopo em
  `ESTADO_ATUAL.md`. **Alta prioridade pós-MVP.**
- 🔴 ⛔fonte — **Siga Brasil / orçamento federal (Senado)** — fonte futura prevista
  no `CLAUDE.md` (execução orçamentária ampla). Ainda não iniciada.

## B. Cobertura temporal (backfill)

- 🔴 ⛔Pro — **Estender pré-2018** (legislaturas 54ª e anteriores). Hoje a base é
  2018–2026; estender por **config**, não on-demand (ver memória de backfill).
- 🟡 — **Base 2018 completa** — hoje o backfill mapeia ≤2018→leg 55; conferir se
  2015–2018 (leg 55) está coberto onde faz sentido.
- 🟢 — **On-demand do legado antigo** (v2) — buscar sob demanda quando um usuário
  pedir dado muito antigo, em vez de ingerir tudo.

## C. Identidade, curadoria & qualidade (Metodologia §4–§6)

- 🟡 — **219 autores de emenda sem perfil** — resolver por convergência
  (`sem_titulos` + UF, §5.3) + revisão humana do resíduo. ~0 espaço (UPDATE).
  Reflete no Feed (posts com "Autoria em resolução").
- 🟢 — **Vínculo do senador 5718 (§4)** — períodos partidários sobrepostos na fonte;
  1 linha de `vinculo_temporal` recusada. Refinar `construir_vinculos_senado`.
- 🟡 — **Linhagem de partidos (§4)** — siglas históricas (PMDB→MDB) e fusões
  (DEM/PSL→UNIÃO); `partido_id` de períodos antigos fica null sem curadoria.
- 🟡 ⛔fonte — **Link titular↔suplente da Câmara (via TSE)** — para dar o "no lugar
  de X" na Câmara, ingerir a **ordem de suplência** do TSE. Onda própria.
- 🟢 — **Presidência de votação (Artigo 17)** — hoje computada, sem coluna alvo.
- 🟡 — **Mapa de autores de emenda por ano** — hoje o mapa é de 2025; autores de
  outros anos fora do mapa não resolvem.
- 🟢 — **Monitorar os 12 modos de falha e os estados do contrato §19**
  (OK/INSTABILIDADE/FALHA/QUEBRA/ALERTA) em produção — vira painel no admin (Pipelines).

## D. Banco de dados & armazenamento

- 🟡 — **Views/RPC ouro agregadas** — hoje o app agrega dinheiro **no cliente** (ok p/
  1 parlamentar; pesado p/ partido/bancada e feed). Criar views/RPC: dinheiro por
  partido, maiores emendas (o Feed hoje ordena no cliente), rankings sob demanda.
- 🔴 — **Tabela `follows`** (seguir parlamentar/partido/comissão/frente/proposição) +
  RLS por usuário. Base do Feed "Seguindo", do Interesses (parlamentares/PLs) e das
  Notificações. **Hoje não existe** (Interesses só guarda temas/partidos no metadata).
- 🔴 — **Tabelas de conteúdo do Feed** — `post` (draft/publicado), `story`,
  `editorial_review` (status, motivo, revisor, confiança), `retratacao`. São o que a
  IA preenche e o admin aprova. **Contrato do post** (source, source_url, synced_at,
  confiança, tipo) precisa virar schema. Hoje o Feed monta posts **em memória** a
  partir de emendas (sem persistência).
- 🔴 — **Camada social** — `reacao` (like/dislike), `comentario`, `salvo`,
  `compartilhamento` + moderação. Hoje o app **não** tem engajamento (nada falso).
- 🔴 — **Tabela `notificacao`** (por usuário; origem: follow/evento/editorial).
- 🔴 — **Papel de admin** — coluna/claim de role + **RLS**: tabelas privilegiadas
  (editorial, auditoria, usuários, flags) só para admin; `service_role` só no servidor.
- 🟡 — **Política do bronze** — hoje opt-out (por espaço). Definir retenção.
- 🟢 — **Alinhar migration 0008** (arquivo diz `perfil_id`; banco/código corretos) via
  migration nova (regra 5).
- 🟢 — **Revisar RLS/GRANTs** das views ouro conforme novas áreas entram.
- 🟡 — **`feature_flags`** (tabela) — liga/desliga recursos por ambiente/usuário.
- 🟡 — **`audit_log`** (tabela) — trilha LGPD (quem acessou/alterou o quê).

## E. Infra, pipeline & segurança

- 🟡 — **Free → Pro (Supabase)** — a base de dinheiro está no teto do Free. Ligar
  áreas pesadas (legislativo, bronze, convênios, pré-2018) exige o Pro (8 GB).
- 🟢 — **Loader de `.env`** — parar de colar chave na mão a cada rodada de ingestão.
- 🟢 — **Agendador automático** — secrets Supabase no repo p/ `ingestao.yml` rodar
  sozinho 2×/dia (mantém despesas/emendas/eventos frescos).
- 🟢 — **CI verde** — testes + type-check (app e, futuramente, admin) a cada push.
- 🔴 — **Deploy do admin** (Vercel/Next) + variáveis + proteção de acesso.
- 🔴 — **Hospedagem do serviço de IA** (Python) + `ANTHROPIC_API_KEY` como secret de
  servidor (nunca no cliente) + limites de custo/rate.
- 🟢 — **Config do OTP por e-mail no Supabase** — editar template "Magic Link" p/
  incluir `{{ .Token }}` (código de 6 dígitos). **Ação do usuário no painel.**

## F. App (Expo) — front-end

**✅ Feito:** Perfil parlamentar, Partido, Comissão, Frente, Explorar (hub) + Listagem
filtrável, Splash, Login (e-mail OTP + gate de sessão), Onboarding (gate por estado),
Configurações (+ logout), Editar perfil (opt-in LGPD), Interesses, Prometeus (lista +
chat, com placeholder honesto), **Feed v1** (destaques de dinheiro reais), **Calendário**
(agenda real). BottomNav 100% navegável. Fonte Inter + logo do protótipo.

**A fazer / refinar:**
- 🟡 — **Header custom (AqHeader)** — telas internas usam o header nativo do
  `@react-navigation` (título sai Inter SemiBold em vez de ExtraBold). Trocar por
  logo à esquerda + avatar à direita.
- 🔴 ⛔IA — **Feed editorial** — os posts gerados pela IA (com fonte + confiança +
  revisão). Hoje o Feed só tem os destaques de dinheiro (sem IA). Depende do agente +
  tabelas de post + fila editorial.
- 🔴 — **Sistema de "seguir"** — botões nos perfis (parlamentar/partido/comissão/
  frente/PL) + Feed "Seguindo" real + Interesses (grupos de parlamentares e
  proposições) + Notificações. Depende da tabela `follows`.
- 🟡 — **Camada social do Feed** — curtir/reagir/comentar/salvar/compartilhar +
  modais (comentários com disclaimer de neutralidade, share sheet). Depende das
  tabelas sociais + moderação.
- 🟡 ⛔IA — **Stories** (rail + viewer) — conteúdo editorial, depende do agente.
- 🔵 — **Notificações (tela)** — depende de eventos/follow/`notificacao`.
- 🔴 ⛔Pro — **Proposição (tela)** + **abas legislativas** do perfil (votações,
  presença, discursos, proposições) — hoje **placeholder**; dependem de reingerir
  B/C/D/E/G. (Proposições dá p/ **contar** da Câmara já, como número no topo.)
- 🟡 — **Stats do topo do perfil** (Presença / Aliado / Proposições) — placeholder;
  ligar ao real conforme as áreas entram.
- 🟢 — **Wire dos botões "Perguntar à IA"** nos perfis (AIPill/AICard) → abrir
  `/prometeus/chat` com contexto (o Feed já faz isso; os perfis ainda não).
- 🟡 — **Login SMS + WhatsApp** (hoje só e-mail) — SMS precisa provedor (Twilio) no
  Supabase; WhatsApp depende da habilitação Meta (lenta).
- 🟢 — **Fotos reais** dos parlamentares (`foto_url`) no Avatar — hoje gradiente+iniciais.
- 🟢 — **Splash/ícone nativos** (expo-splash-screen, adaptive icon, nome nas stores,
  build EAS) — hoje só o Splash React durante a carga.
- 🟡 — **Robustez** — error boundaries por rota, estados de erro de rede + retry,
  revisão dos empty states, paginação das listas grandes (parlamentares ~600,
  frentes ~1443), cache de dados.
- 🟢 — **Deep links / linking** (abrir `/parlamentar/x` por URL ou notificação).
- 🟢 — **Acessibilidade** (labels, contraste, área de toque).
- 🟢 — **`tema.ts` → `@aquarius/ui`** — hoje tokens são cópia local; ligar o monorepo.

## G. Admin (Next.js) — a construir do zero

App novo em `codigo/apps/admin` (App Router). Referência: PNGs `01-visao-geral`…
`14-configuracoes` e `handoff/prototype/aq-admin-*.jsx`. Tema dark por padrão
(ferramenta operacional).

**Fundação:**
- 🟢 — ✅ **Scaffolding** Next.js 14 (App Router) em `codigo/apps/admin` + tema
  ADM_DARK/ADM_LIGHT com toggle (dark default) + **shell** (sidebar 16 itens em 5
  seções + topbar). Verificado: builda e roda (porta 3001).
- 🟢 — ✅ **Visão geral (01)** — KPIs REAIS (parlamentares/partidos/emendas/eventos/
  comissões/frentes via views ouro) + estado das áreas de dados + métricas de uso
  marcadas honestamente como "não medido ainda".
- 🟢 — **Bumpar Next** 14.2.15 → patch mais novo (CVE de segurança) antes de deploy.
- 🔴 — **Auth + role de admin** (Supabase Auth + claim/tabela de role + middleware de
  proteção de rota + RLS). Hoje o admin lê via anon (só contagens públicas); ações
  privilegiadas e telas sensíveis exigem isso. **Sem isso, não vai pra produção.**

**Telas (do protótipo admin):**
- 🔴 — **Visão geral (01)** — saúde da ingestão, contadores, últimas sincronizações.
- 🔴 — **Pipelines (02)** — status dos coletores por área, últimas rodadas, erros,
  estados do contrato §19. (Consome logs/estado da ingestão.)
- 🔴 — **Feed / Posts (03)** — gestão dos posts publicados/agendados.
- 🔴 — **Stories (04)** — gestão de stories.
- 🔴 — **Revisão editorial (05)** — **workbench gerado-vs-fonte**: aprovar/editar/
  rejeitar com motivo, correções e retratações, ver `confiança`. **Freio de
  segurança do agente — pré-requisito para ligar a IA.**
- 🔴 — **Moderação (06)** — moderação de comentários/conteúdo de usuário.
- 🔴 — **Usuários (08)** — abas Comportamento, Diretório, Interesses & Segmentos, DaaS.
- 🔴 ⛔escala — **Engajamento (09)** — métricas de uso (depende de coletar analytics).
- 🔴 ⛔escala — **Audiências / DaaS (10)** — audiências agregadas (k-anonimato + consentimento).
- 🔴 — **Notificações (10)** — compor/enviar/gerir notificações.
- 🔴 — **Feature flags (11)** — toggles por ambiente/usuário.
- 🔴 — **Auditoria & LGPD (12)** — trilha de auditoria, exportação/deleção de dados.
- 🔴 — **Equipe & permissões (13)** — gestão de admins e papéis.
- 🔴 — **Configurações (14)** — settings do sistema.

**Backend do admin:**
- 🔴 — Tabelas (ver seção D): `post`, `story`, `editorial_review`, `retratacao`,
  `audit_log`, `feature_flags`, `admin_roles`, `notificacao`.
- 🔴 — Server actions / RPC privilegiadas (`service_role`) para ações admin.
- 🔴 — (Opcional) coleta de eventos de uso p/ Engajamento/DaaS.

## H. Agente Prometeus (IA) — a peça mais delicada

Serviço de IA (Python, decisão travada) que o app chama; responde SEMPRE com fonte,
neutro, e recusa honestamente quando não há dado. **Decisões abertas** (alinhar antes):
arquitetura de acesso (ferramentas curadas × texto-para-SQL × híbrido), onde roda
(serviço Python × edge function × protótipo), e a chave da Anthropic.

- 🔴 — **Serviço Python (FastAPI)** + endpoint que o app consome; modelo Claude
  (Anthropic API); `ANTHROPIC_API_KEY` como secret de servidor.
- 🔴 — **Acesso a dados** — ferramentas curadas (despesas/emendas/votações/…) e/ou
  SQL de leitura restrito às views ouro. Guarda-corpos contra injeção, timeouts,
  limite de custo/rate, cache.
- 🔴 — **Contrato de resposta** (§ Metodologia): `source` + `source_url` + `synced_at`
  sempre; terceira pessoa/neutro; sem opinião; recusa quando ausência de dado;
  `confiança` calculada.
- 🔴 — **Geração de posts do Feed pela IA** → grava como `post` draft → **fila de
  revisão editorial (admin)** → publicação. `confiança < 0.65` ou null → revisão
  obrigatória.
- 🔴 — **Wire no app** — chat real (substituir o placeholder), botões "Perguntar ao
  Prometeus" (Feed já manda o prompt; perfis a ligar), resumos nos perfis.
- 🔴 — **Avaliação/testes do agente** — cada regra com caso que aceita e que recusa
  (disciplina da Metodologia §5.2). Auditoria das consultas/estados do contrato.

## I. Produto & monetização (decisões travadas)

- 🔴 — **Premium / billing** — vem **antes** do DaaS (decisão travada, `PLANO.md`).
- 🔴 ⛔escala — **DaaS (dados agregados)** — só agrega, zero PII, k-anonimato +
  consentimento; só vendável na casa de centenas de milhares de usuários consentidos.
- 🟡 — **Perfil opt-in** (renda, escolaridade, ocupação) — ✅ coletado (Onboarding +
  Editar perfil); falta **usar** de forma agregada/anônima (liga com DaaS).
