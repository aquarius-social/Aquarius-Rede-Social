# MELHORIAS.md — backlog completo (dados, ingestão, banco, app, produto)

Lista viva de **tarefas inacabadas ou que precisam de refinamento**, cobrindo a
plataforma inteira — não só o app. Decisão do usuário: **fechar o MVP primeiro**,
depois voltar aqui e refinar item a item.

Marcação: 🔴 grande (onda própria) · 🟡 médio · 🟢 pequeno.
Bloqueio: ⛔Pro (precisa Supabase Pro por espaço) · ⛔fonte (depende de fonte/chave).
Quando concluir, mover para `ESTADO_ATUAL.md` e riscar aqui.

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
  da base atual. Reingerir para ligar a aba do app.
- 🔴 ⛔Pro — **Área C · Votações + votos nominais (Câmara + Senado)** — coletor
  pronto; truncado. Reingerir (é o "como cada um votou").
- 🔴 ⛔Pro — **Área D · Tramitações (Câmara + Senado)** — coletor pronto; truncado.
- 🔴 ⛔fonte — **Área E · Presença** — **NÃO há coletor ainda.** Construir (Câmara +
  Senado): sessões convocadas/presentes/justificadas por legislatura.
- 🟢 — **Área F · Emendas parlamentares** — ✅ no ar (2023–2026, bicameral na fonte).
- 🔴 ⛔Pro — **Área G · Discursos (Câmara + Senado)** — coletor pronto; truncado.
- 🟡 ⛔Pro — **Área H · Eventos/agenda (Câmara + Senado)** — coletor pronto; truncado.
- 🔴 ⛔fonte — **Convênios / transferências (o "objeto" das emendas)** — para onde o
  dinheiro foi de fato (beneficiário, objeto). Coletor NOVO + migration. Fonte:
  `/convenios` e `/transferencias` do Portal (mesma chave). Escopo em
  `ESTADO_ATUAL.md`. **Alta prioridade pós-MVP.**
- 🔴 ⛔fonte — **Siga Brasil / orçamento federal (Senado)** — fonte futura prevista
  no `CLAUDE.md` (execução orçamentária ampla). Ainda não iniciada.

## B. Cobertura temporal (backfill)

- 🔴 ⛔Pro — **Estender pré-2018** (legislaturas 54ª e anteriores). Hoje a base é
  2018–2026; a estratégia é estender por **config**, não on-demand (ver memória
  de backfill). Volume grande.
- 🟡 — **Base 2018 completa** — hoje o backfill mapeia ≤2018→leg 55; conferir se
  2015–2018 (leg 55) está coberto onde faz sentido.
- 🟢 — **On-demand do legado antigo** (v2) — buscar sob demanda quando um usuário
  pedir dado muito antigo, em vez de ingerir tudo.

## C. Identidade, curadoria & qualidade (Metodologia §4–§6)

- 🟡 — **219 autores de emenda sem perfil** — resolver por convergência
  (`sem_titulos` + UF, §5.3) + revisão humana do resíduo. ~0 espaço (UPDATE).
- 🟢 — **Vínculo do senador 5718 (§4)** — períodos partidários sobrepostos na fonte;
  1 linha de `vinculo_temporal` recusada. Refinar `construir_vinculos_senado`.
- 🟡 — **Linhagem de partidos (§4)** — siglas históricas (PMDB→MDB) e fusões
  (DEM/PSL→UNIÃO); `partido_id` de períodos antigos fica null sem curadoria.
- 🟡 — **Suplente em exercício (§6.4) — Câmara.** O **Senado está FEITO** (suplente
  ganha vínculo por período real de exercício + titular + causa; view 0014 + card
  no app). Falta a **Câmara** — e é ela que cobre casos como a **Marina Silva**
  (deputada licenciada para ser ministra). Dois problemas próprios da Câmara:
  (1) a lista `/deputados` só devolve quem está **sentado**, então o titular
  licenciado (Marina) talvez nem esteja ingerido — só o suplente dele; precisa de
  fonte com o roster completo/afastamentos. (2) `camara/mandatos.py` põe o suplente
  em quarentena. Investigar a estrutura da Câmara (equivalente a `Exercicios`/
  `Titular` do Senado).
- 🟢 — **Presidência de votação (Artigo 17)** — hoje computada, sem coluna alvo.
- 🟡 — **Mapa de autores de emenda por ano** — hoje o mapa é de 2025; autores de
  outros anos fora do mapa não resolvem.
- 🟢 — **Monitorar os 12 modos de falha (§) e os estados do contrato §19**
  (OK/INSTABILIDADE/FALHA/QUEBRA/ALERTA) em produção — painel/log.

## D. Banco de dados & camadas

- 🟡 — **Views ouro agregadas** — hoje o app agrega no cliente (ok para 1
  parlamentar). Para **Partido/bancada** e rankings, criar views/RPC de agregação
  (ex.: dinheiro somado por partido) — senão fica pesado no cliente.
- 🟡 — **Política do bronze** — hoje opt-out (por espaço). Definir retenção (o app
  lê do ouro; o bronze é auditoria/reprocesso).
- 🟢 — **Alinhar migration 0008** (arquivo diz `perfil_id`; banco/código corretos)
  via migration nova (regra 5).
- 🟢 — **Revisar RLS/GRANTs** das views ouro conforme novas áreas entram.

## E. Infra, pipeline & segurança

- 🟡 — **Free → Pro (Supabase)** — a base de dinheiro está no teto do Free. Ligar
  áreas pesadas (legislativo, bronze, convênios, pré-2018) exige o Pro (8 GB).
- 🟢 — **Loader de `.env`** — parar de colar chave na mão a cada rodada de ingestão
  (backfill e app).
- 🟢 — **Agendador automático** — pôr os secrets Supabase no repo para o
  `ingestao.yml` rodar sozinho 2×/dia (mantém despesas/emendas frescas).
- 🟢 — **CI verde** — garantir os testes + type-check rodando a cada push.
- 🟢 — **Rotação de chave** — ✅ feita (mantê-la fora do chat daqui pra frente).

## F. App & UX (Expo)

- 🟢 — **Perfil parlamentar** — ✅ feito (dinheiro real: despesas + emendas com
  drill-down e fonte).
- 🟡 — **Stats do topo do perfil** (Presença / Aliado / Proposições) — hoje
  **placeholder**; ligar ao real (proposições dá pra contar da Câmara já).
- 🔴 — **Telas do protótipo a fazer** (Claude Design): Explorar/Busca (refinar),
  **Partido** (próxima), Comissão, Frente, Proposição, Feed cívico, Splash/Login/
  Onboarding, Listagem, Configurações, Editar perfil.
- 🔴 — **Prometeus / IA** — botões "Perguntar à IA" são placeholder; integrar o
  agente (chat + resumos com fonte).
- 🟡 — **Shell de navegação** — bottom nav funcional, header, deep links.
- 🟢 — **`tema.ts` → `@aquarius/ui`** — hoje os tokens são cópia local; ligar o
  monorepo no Metro e importar do pacote.
- 🟡 — **Abas não-monetárias com dado real** — dependem de reingerir as áreas
  B/C/D/E/G/H (⛔Pro).

## G. Produto & monetização (decisões travadas)

- 🔴 — **Premium / billing** — vem **antes** do DaaS (decisão travada, `PLANO.md`).
- 🔴 — **DaaS (dados agregados)** — só agrega, zero PII, k-anonimato + consentimento;
  só vendável na casa de centenas de milhares de usuários consentidos.
- 🟡 — **Perfil opt-in** (renda, escolaridade, ocupação) — nudge, nunca obrigatório.
- 🟡 — **Login OTP** (SMS/e-mail primeiro; WhatsApp em paralelo pela lentidão da
  habilitação Meta).
