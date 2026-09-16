# Estado atual do Aquarius

Documento de status do projeto — **snapshot completo e detalhado**. É o 2º arquivo a
ler (depois do `CLAUDE.md`). Complementos: `PLANO.md` (roadmap em ondas),
`RELATORIO_DESENVOLVIMENTO.md` (fotografia por camada, também publicada como página),
`MELHORIAS.md` (backlog A–I), `HISTORICO.md` (marcos e números de ingestão).

Atualização: 2026-09-16.

## Resumo executivo

O Aquarius tem **app (Expo) e admin (Next.js) no ar na Vercel**, com a camada de leitura
navegando dado oficial real (despesas, emendas, eventos) e login por OTP funcionando. A
peça em construção é o **Prometeus (Onda 2)** — o agente de IA. O **backend do Prometeus
está pronto, testado e agora VALIDADO contra o banco real** (as 7 ferramentas foram
conferidas ao vivo via Supabase MCP — schema bate 100%, dado e proveniência presentes).
Falta só **publicar (deploy no GCP Cloud Run)** e **colar a chave da Anthropic** — a chave
**já foi criada** e o **projeto GCP já existe com as APIs ativas**; o deploy será feito
**pelo dev** (máquina mais robusta). Novidade estrutural: o **Supabase migrou para o plano
Pago (Pro)**, com muito mais espaço — o que **destrava o backfill** das áreas truncadas e a
extensão de despesa/emenda para anos anteriores a 2023. A geração de posts (2ª face do
Prometeus) e o deploy são os próximos grandes passos.

## 1. App (Expo / React Native) — camada de leitura pronta

- **~15 telas navegáveis**, dado real onde existe: Perfil parlamentar, Partido, Comissão,
  Frente, Explorar + Listagem, Feed v1 (dinheiro real), Calendário, Interesses, Prometeus
  (lista + chat), Configurações, Editar perfil, Login, Onboarding.
- **Modo escuro ✅** (`lib/theme.tsx` + tema claro/escuro; tokens semânticos `texto`/`cartao`).
- **Header custom (AqHeader) ✅** (variantes home/detalhe).
- **Sistema de "seguir" ✅** (tabela `follows`, migration `0018` + provider + Feed "Seguindo")
  — falta **rodar a migration** pra persistir.
- **Login por OTP de 6 dígitos ✅** via **Resend como SMTP custom** no Supabase; o "colar o
  código inteiro" foi corrigido. Ressalva: `onboarding@resend.dev` só entrega pro e-mail da
  própria conta Resend — produção depende de **domínio verificado** (ver pendências).
- **Prometeus chat ligado ao endpoint:** `chat.tsx` chama `POST {EXPO_PUBLIC_PROMETEUS_URL}
  /perguntar`, renderiza resposta + **fontes clicáveis** + ressalvas, com fallback honesto
  enquanto não publicado. ✅ **Já pushado** (`ae0019f`). O app publicado só mostrará o chat
  real quando `EXPO_PUBLIC_PROMETEUS_URL` for setado (após o deploy); até lá, o fallback honesto.
- **Deploy:** app web na Vercel (`aquarius-rede-social-app.vercel.app`). Mobile (EAS): não
  iniciado (`eas.json`/`app.json` prontos).

## 2. Admin (Next.js) — fundação + RBAC no ar

- **14 telas fiéis ao protótipo** (via adaptador de dados).
- **RBAC** (`admin_roles` + RLS + gate de login por magic link). Superadmin logado.
- **Deploy na Vercel ✅** (produção) + `localhost:3001`.
- A **Revisão editorial** é o **freio de segurança** — pré-requisito para ligar a geração de
  posts da IA (ver Prometeus 2.3).

## 3. Dados & ingestão (Python)

- **Fundação de identidade** (`profiles`, `id_externo`, `vinculo_temporal`, partido canônico
  com linhagem) + **pipeline em 3 camadas** (bronze imutável → prata tratada → ouro servida)
  com portão de qualidade e quarentena.
- **8/9 áreas com coletor.** **Servidas (dado real):** despesas (Câmara CEAP + Senado CEAPS),
  emendas (Portal da Transparência), eventos (agenda bicameral). **Truncadas** (coletor pronto,
  dados incompletos por espaço): proposições, votações, tramitações, discursos. **Sem coletor:**
  presença.
- **Camada ouro = VIEWS** (`*_publico`/`*_publica`) com GRANT SELECT p/ `anon` — é o que o app
  e o Prometeus leem. Toda view carrega `source`/`source_url`/`synced_at`. PII nunca é projetada.
- **Cobertura real hoje (contagem das views ouro):** despesa **~1,86 mi** (Câmara + Senado,
  anos **2018–2026** — o backfill desta sessão adicionou ~1,1 mi), emenda **48.369**
  (**2018–2026**, 88% com perfil resolvido), voto_nominal 4.752, tramitacao 3.285, proposicao 2.300, frente 1.443,
  votacao 1.312, discurso 949, evento 363, comissao 90, partido 22. `parlamentar_publico` segue
  **624** (a view só traz vigentes; os ex-parlamentares do backfill entram como perfil
  **inativo**, fora do app, só memória do Prometeus). Os **domínios de atividade** (proposição/
  votação/voto_nominal/discurso/tramitação) seguem **parciais** (2ª rodada).
- **Banco agora no Supabase Pro (plano PAGO)** — muito mais espaço. Isso **destrava**: (a) o
  **backfill de despesa/emenda para 2018–2022**; (b) completar as **áreas truncadas**; (c) a
  **paridade Senado** onde falta. **Diagnóstico (mapeamento desta sessão):** as lacunas são de
  **execução, não de código** — o dinheiro rodou só na leg 57 e as áreas de atividade foram
  **desligadas por flag** pra caber no Free. Correção é **re-execução** (mudar env), sem código
  novo. Decisão: **fatia de valor primeiro** (identidade + dinheiro 2018–2022) — runbook em
  `RUNBOOK-BACKFILL.md`. Atividade + paridade ficam pra 2ª rodada.
- **Validação 2026-09-08:** as 7 ferramentas do Prometeus foram conferidas contra o dado real
  (schema das 5 views consumidas bate 100%; encadeamento `parlamentar_publico.id` →
  `despesa_publica.perfil_id` funciona; proveniência presente). **Achado:** `emenda.autor_profile_id`
  já está **88% populado** (17.135/19.476) — a ressalva do código que diz "chave ainda não
  carregada" ficou desatualizada (task `task_5e142e49` aberta pra melhorar a atribuição).
- **Testes:** **315**, sem rede (`cd codigo/services/ingestao && py -m unittest discover -s . -t .`).

## 4. Prometeus (Onda 2) — o agente de IA  [FOCO ATUAL]

Plano fechado em sub-etapas (detalhe na `PLANO.md`). **Arquitetura travada:**

- **Cérebro:** ReAct (loop nativo de tool-calling do Claude); **RAG** p/ dado textual (via
  `pgvector`, futuro); **text-to-SQL** só p/ casos que pedem, com guarda-corpos (só-leitura,
  views restritas, allow-list).
- **Ferramentas:** **servidor MCP** próprio sobre a camada ouro; cada consulta devolve dado +
  proveniência.
- **Modelo:** **Sonnet 5** principal + **fall-back nativo Claude→Claude (Opus 4.8)** em recusa —
  **1 chave (Anthropic)**. Cross-provider (OpenAI) parqueado.
- **Hospedagem:** **GCP** (Cloud Run + Secret Manager).
- **Faces:** fundação compartilhada, endpoints por tipo; **chat primeiro**, **posts em pipeline
  dedicado**.
- **Contrato de resposta:** as **7 regras da Metodologia §20** (fonte sempre, neutralidade em 3ª
  pessoa, ausência ≠ inexistência, estágio orçamentário declarado, exclusões estruturais, recusa
  honesta). Os **12 modos de falha (§21)** são o gabarito dos testes.

### Status das sub-etapas

| Sub-etapa | Status |
|---|---|
| **2.0 Fundação e decisões** | ✅ Feito (arquitetura + contrato lido + ferramentas definidas) |
| **2.1 Servidor MCP (consultas seguras)** | ✅ Feito — 14 testes; no repo |
| **2.2 Agente ReAct + endpoint + ligar no app** | ✅ Código pronto **e validado contra o banco real** (21 testes + 7 ferramentas conferidas ao vivo); falta só deploy p/ ao vivo |
| **2.3 Pipeline de posts + freio editorial** | ⬜ Não iniciado |
| **2.4 Deploy (GCP Cloud Run)** | 🟡 Pré-requisitos quase prontos: **chave Anthropic criada**, **projeto GCP `aquarius-prometeus` + APIs ativas**; falta instalar `gcloud` (no PC do dev) + rodar o deploy |
| **2.5 Refino (roteamento Haiku/Opus, RAG, rate limit, custo)** | ⬜ Pós-MVP |

### O serviço `codigo/services/prometeus/`

- **Acesso ao dado (2.1):** `gateway.py` (Consulta/Filtro/Gateway), `resultado.py`
  (Resultado/Proveniencia/Completude + `recusar()`), `consultas.py` (as 7 consultas puras),
  `supabase_gateway.py` (PostgREST real; `httpx` lazy), `servidor_mcp.py` (expõe via MCP).
- **Cérebro (2.2):** `contrato.py` (system prompt das 7 regras), `ferramentas.py` (registro
  esquema + despacho — fonte única), `modelo.py` (`Modelo` + `ModeloClaude` Sonnet 5 + fall-back),
  `agente.py` (loop ReAct + gating + acumula fontes/ressalvas), `api.py` (FastAPI `/perguntar`).
- **Deploy:** `requirements.txt` + `Procfile` (Cloud Run).
- **Testes:** `tests/` — **21 verdes** (modelo fake + FakeGateway), sem rede nem chave.
- **7 ferramentas:** `buscar_parlamentar`, `buscar_partido`, `despesas_parlamentar`,
  `total_despesas`, `emendas_por_municipio`, `emendas_por_autor_nome`, `agenda_eventos`.
  Guarda-corpos: exige janela temporal; ausência ≠ inexistência; nunca soma estágios; atribuição
  por nome com ressalva; conta entidades; partido é o de hoje.
- **Nota de arquitetura:** o agente usa as ferramentas **em processo** (via `ferramentas.py`); o
  `servidor_mcp.py` é a interface MCP reutilizável externa. Trocar o agente para o cliente MCP é
  um adaptador fino, se um dia forem separados.

### O que falta pra ligar o Prometeus ao vivo (a fazer **pelo dev**)

1. **Instalar o `gcloud`** no PC do dev + `gcloud init` (login + escolher o projeto
   `aquarius-prometeus`).
2. **Deploy no GCP Cloud Run** (`gcloud run deploy` a partir de `codigo/services/prometeus/`,
   sem GitHub — evita Actions). Env já conhecidos: `SUPABASE_URL` + `SUPABASE_ANON_KEY` (seguros,
   protegidos por RLS).
3. **Colar a chave da Anthropic** (`ANTHROPIC_API_KEY`) no campo **Variáveis** do painel do
   Cloud Run — nunca no chat nem no comando.
4. Setar `EXPO_PUBLIC_PROMETEUS_URL` (app: env na Vercel + `.env` local) pra URL do Cloud Run.
5. **Teste ao vivo** do chat com pergunta real (dado + fonte).

## 5. Deploys (o que está no ar)

- **Admin → Vercel** (produção). ✅
- **App web → Vercel** (`aquarius-rede-social-app.vercel.app`). ✅
- **Prometeus (serviço) → GCP:** 🟡 não deployado, mas pré-requisitos quase prontos (Etapa 2.4).
- **App mobile → EAS:** ⬜ não iniciado.

## 6. Estado do git / repositórios

- **Ownership transferida para a organização `aquarius-social`.** Remote do repo de código:
  `github.com/aquarius-social/Aquarius-Rede-Social.git`.
- **Repo de código:** `origin/main` e local **em `b1d6898`** (sincronizados) — os commits do
  backfill de despesa 2018–2022, dos 2 fixes de ingestão e do loader de `.env` foram **pushados**.
  Working tree limpo, **exceto `.mcp.json` não versionado** (commitar é opcional).
- **Repo agora PÚBLICO** (Actions grátis/ilimitado) — resolveu o billing que travava a ingestão
  agendada. Histórico varrido: **nenhum segredo commitado**. Docs de negócio ficam no repo separado
  `aquarius-contexto` (não afetado).
- **Repo de contexto** (`aquarius-contexto`): separado, sem alteração nesta sessão (prints/telas,
  docs-fonte, marketing, protótipo).
- **Segurança:** um **PAT do GitHub circulou no chat** na sessão anterior — **precisa ser revogado**
  se ainda não foi (ver pendências).

## 7. ⚠️ Ações pendentes

**Deploy do Prometeus (com o dev):**
1. Instalar `gcloud` + deploy no Cloud Run + colar a **chave Anthropic** (já criada) no painel +
   setar `EXPO_PUBLIC_PROMETEUS_URL`. *(Claude Max NÃO dá crédito de API — cobrança separada; teto
   de gasto já recomendado no Console.)*

**Dados (destravado pelo Supabase Pro):**
2. **Backfill de despesa — FEITO (2018–2022, as duas casas).** ~1,1 mi de lançamentos novos
   (total ~1,86 mi). Ex-parlamentares entram como **perfil inativo** (modelo escolhido: fora do
   app, memória do Prometeus). Emendas 2018–2022 **também FEITAS** (+29 mil; total **48.369**,
   88% com perfil) — **fatia de valor 100% completa**. Dois bugs corrigidos no caminho (com teste): crash de sobreposição de
   vínculo e a mudança da API da Câmara (`idLegislatura`, que também derrubava a ingestão de
   produção). **2ª rodada (depois):** religar atividade (proposições/votações/discursos — precisa
   do canário) + paridade (frentes Senado, blocos Câmara). Ver `RUNBOOK-BACKFILL.md`.
3. Melhorar **atribuição de emendas** usando `autor_profile_id` (88% populado) — decisão de
   produto; task `task_5e142e49` aberta.

**Segurança / infra:**
4. **Revogar o PAT do GitHub** que circulou no chat (se ainda não).
5. **Rotacionar a service key do Supabase** (também circulou no chat; prioridade segurança).
6. **Rodar a migration `0018_follows`** (sem ela o "seguir" não persiste).
7. **Secrets do repo** (`SUPABASE_URL`/`SUPABASE_SERVICE_KEY`) pro agendador `ingestao.yml`.

**Parqueado (dependências externas / decisão futura):**
8. **E-mail de produção — comprar domínio + verificar no Resend.** Sem domínio verificado, só o
   e-mail da conta Resend recebe o código.
9. **WhatsApp Business** — habilitação Meta em paralelo (dependência externa mais longa).

**Feito recentemente:**
- ✅ **Supabase Free → Pro** (plano pago ativo — mais espaço).
- ✅ **Chave da Anthropic criada**; **projeto GCP `aquarius-prometeus` + APIs (Cloud Run, Cloud
  Build) ativas**; crédito grátis do GCP ligado.
- ✅ **Supabase MCP conectado** (via Conectores da GUI) — usado nesta sessão pra validar o dado.

> **GitHub Actions:** só `git push` dispara Actions; o limite do plano free reseta por mês (ou
> repo público = Actions ilimitado). Como não há nada pendente pra pushar agora, não é bloqueio.

## 8. Próximo passo

**Plano refeito em 5 partes — detalhe no `PLANO.md` (topo). Ordem decidida: 1 → 2 → 3 → 4 → 5.**

- **Parte 1 — ligar o que já está pronto:** rodar migration `0018`; **deploy do Prometeus (2.4)**
  pelo dev (gcloud + `ANTHROPIC_API_KEY` no painel + `EXPO_PUBLIC_PROMETEUS_URL`); secrets do repo
  p/ ingestão agendada; **segurança** (revogar PAT + rotacionar service key); wire dos botões de IA.
- **Parte 2 — completar os dados (2ª rodada, a próxima):** validar o **canário de proposições**
  (dívida de integridade) → backfillar proposições/votações/tramitações/discursos; paridade (frentes
  Senado, blocos Câmara); juntar as 2 pernas de tramitação; presença; curadoria (linhagem de partidos).
- **Partes 3–5** (produto/social → monetização/mobile → DaaS): detalhe no `PLANO.md`.

## 9. Notas de ambiente

- Interpretador Python é **`py`** (não `python`, alias fantasma da Microsoft Store).
- **Testes sem rede:** ingestão **315** + Prometeus **21** = **336** verdes. Rodar dentro de cada
  serviço: `py -m unittest discover -s . -t .`.
- **Padrão da ingestão (fixado no código):** segredos no `.env` de `codigo/services/ingestao/`
  (lido por `env_local.carregar_env`; nunca colar chave à mão — foi assim que a service key vazou).
  Rodar `py run_backfill.py` (histórico) / `run_ingestao.py` (incremental). Ver `RUNBOOK-BACKFILL.md`.
- **RAM limitada:** Metro (Expo web) e `tsc` estouram memória; parar preview antes do `tsc`. Ver a
  memória do projeto `ambiente-ram-limitada`. **Relevante pro backfill:** rodar ingestão pesada
  pode competir por memória — avaliar rodar por domínio/ano e/ou na máquina do dev.
- **GitHub Actions:** só `git push` dispara Actions; `git commit` local **não**.
- **Push ao GitHub** funciona via credencial de arquivo (memória `github-push-acesso`); alterar
  `.github/workflows/` exige o escopo `workflow` no token. Remote agora na org `aquarius-social`.
- **Supabase MCP** conectado (project ref `nqebfmyzchpkufsytvyf`) — usar só operações de leitura
  sem pedido explícito (permissões amplas: database/functions/branching).

## 10. O que NÃO fazer (resumo — detalhe no `CLAUDE.md`)

- Não editar migration antiga (correção vem em migration nova).
- Não copiar código de `basedosdados/pipelines` (sem licença) nem `parlametria/leggo-backend`
  (AGPL). OK ler como referência de campo/modelagem.
- Não pular a resolução de identidade ("resolver depois"). Dado errado é pior que ausente.
- Prometeus lê **só a camada ouro** (views), nunca a prata; toda resposta cita fonte; recusa
  honesta quando falta dado.
- Não criar arquivos fora da pasta do projeto.
