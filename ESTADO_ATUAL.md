# Estado atual do Aquarius

Documento de status do projeto — **snapshot completo e detalhado**. É o 2º arquivo a
ler (depois do `CLAUDE.md`). Complementos: `PLANO.md` (roadmap em ondas),
`RELATORIO_DESENVOLVIMENTO.md` (fotografia por camada, também publicada como página),
`MELHORIAS.md` (backlog A–I), `HISTORICO.md` (marcos e números de ingestão).

Atualização: 2026-09-23.

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
- **Emendas — autoria (§6.3/§13).** Base de **48.966** emendas (9 anos), autor em **99,986%** (48.959)
  — resolução em `id_externo` (sistema='autor_orcamentario') + backfill do `autor_profile_id`.
  **Individuais 100%** (backfill + casamento por nome + **dedup dos 203 residuais**, migration
  **0026**: casa na data do fato ancorada em mandato oficial + verificação adversarial de 10 agentes —
  homônimo Pedro Chaves MS/GO separado, "Rocha"=Wherles Rocha, "Pedro Dalua"=DaLua do Rota; 0 perfil
  criado); **bancadas estaduais
  como PERFIL COLETIVO** — 27 perfis `tipo='bancada'`, ligação 71xx→bancada, **1.882 emendas de
  bancada**, + views `bancada_publica`/`bancada_membro_publico` (composição atual por UF, **sem
  colunas de dinheiro**). **Anti-duplicidade:** cada emenda tem 1 dono (pessoa OU bancada, disjuntos);
  emenda de bancada nunca soma ao total individual. **Relator-Geral (RP9 / "orçamento secreto") —
  resolvido (mesma disjunção):** as **295 Emendas de Relator** (8100, R$19,4bi, 2020–2022) viram
  donas de um **perfil INSTITUCIONAL** `tipo='relatoria'`, nunca somadas a ninguém; a tabela
  `relatoria_geral` liga cada exercício ao **relator formal** verificável (2020 Domingos Neto / 2021
  Marcio Bittar / 2022 Hugo Leal) como **responsabilidade**, não autoria pessoal (migrations
  **0023/0024**, *a aplicar*). O **solicitante real** de cada RP9 fica honestamente ausente (fora da
  fonte). **Comissões — FEITAS:** 13 códigos por **sigla-na-fonte + casa** (determinístico, migration
  **0025**) + ~19 por **nome** (cobertura bidirecional + vencedor claro; `metodo='convergencia'`,
  `pendente_conferencia=true` — via PostgREST, provisório). **Comissões — sucessão de órgão FEITA
  (migration `0027`):** 11 comissões renomeadas na reforma 2023 ligadas ao perfil do órgão CONTÍNUO
  (id `/orgaos/{id}` desde 2011, dataFim null — ex. CSSF→Saúde id 2014, CTASP→Trabalho id 2015) +
  ' GE'→Relator-Geral; verificado por 18 agentes vs API de órgãos. **Mistas + Senado + resíduo FEITOS
  (0028/0029/0030):** 3 perfis de comissão MISTA criados (CCAI/CMMC/Migrações, órgão oficial); CCDD e
  Defesa da Democracia ligadas às comissões do Senado; a linha "Sem informação" (Emenda de Relator S/I,
  R$459mi) → Relator-Geral (§13). **Ainda sem autor (7, só COLETIVO, R$9,5mi emp / 0,0045%):** rótulo
  5035 (combina CFFC+CDC, sem órgão único) + CSF "Senado do Futuro" (comissão extinta 2019). **Resíduo
  EXPLÍCITO (§1):** view `emenda_autoria_resumo_publico` + tool Prometeus `emendas_resumo` reportam
  SEMPRE o total-geral com o split de autoria — o dinheiro sem-autor nunca some de um ranking.
  Migrations **0020**–**0030**. **11 ferramentas** Prometeus: `emendas_por_autor_perfil` + `buscar_bancada`
  + `relator_geral_orcamento` + `emendas_resumo` (total geral + resíduo de autoria). Re-resolução:
  `run_reresolver_autores_emendas.py`.
- **Auditoria de fill-rate (2026-09-23):** a maioria dos campos está 100%. **Preenchível em curso:**
  `proposicao.tema/situacao/inteiro_teor_url` (era 0% — enriquecimento pelo detalhe `/proposicoes/{id}`,
  `run_proposicao_detalhe.py` + workflow, rodando na nuvem). **Piso honesto da FONTE (não preencher =
  não inventar, §1):** placar de votação (sim/não/abstenção — texto livre), `tramitacao.despacho` (77%),
  `despesa.url_documento` (66%), foto de ex-parlamentar do Senado (fonte não tem). **Decisão de escopo:**
  `votacao.proposicao_id` (32%) — o resto aponta a proposições fora do nosso escopo (REQ/PDC/antigas) ou
  não tem matéria; preencher exige expandir a ingestão.
- **9/9 áreas com coletor, TODAS servidas com dado real — bicameral.** despesas (Câmara CEAP +
  Senado CEAPS), emendas (Portal da Transparência), eventos (agenda bicameral), **proposições/votações/
  discursos/tramitações** (backfill 2018–2026 completo) e **presença (Área E) — a última área,
  construída e no ar nas DUAS casas** nesta sessão: **1.580 sessões, 528.495 registros** (Câmara 1.141
  sessões / lista de presença; Senado 439 / comparecimento em votações — `source` distingue). View
  `presenca_publica` com % realistas nas duas casas. Ver `ONDA-1-PRESENCA-LEIA-ME.md`.
- **Camada ouro = VIEWS** (`*_publico`/`*_publica`) com GRANT SELECT p/ `anon` — é o que o app
  e o Prometeus leem. Toda view carrega `source`/`source_url`/`synced_at`. PII nunca é projetada.
- **Cobertura real hoje (contagem das views ouro, 2026-09-22):** despesa **~1,88 mi** (Câmara +
  Senado, **2018–2026**), emenda **48.369** (88% com perfil), **tramitação 705.096** (bicameral
  2018–2026: Câmara 544.930 + Senado 160.166), **voto_nominal ~997 mil**, **discurso 155.984**,
  **votação 65.623**, **proposição 52.869**, evento ~4 mil, frente 1.443, comissao 90, partido 22.
  `parlamentar_publico` segue **624** (a view só traz vigentes; os ex-parlamentares do backfill
  entram como perfil **inativo**, fora do app, só memória do Prometeus).
- **Atividade — COMPLETA 2018–2026 (backfill desta sessão, verificado no banco 2026-09-20).**
  Contagens ouro atuais: **despesa 1,88 mi**, **proposição 52.869**, **votação 65.623**,
  **discurso 155.984**, **voto_nominal ~997 mil**. Todos os 9 anos têm proposição + votação +
  discurso reais (antes só 2024). Rodou na nuvem (workflow `backfill-atividade.yml`, matriz por
  ano); só as votações de **2021 e 2023** foram fechadas numa passada local (a API da Câmara
  limitava o IP do runner nos 2 anos mais pesados — código correto, throttle de ambiente).
- **Tramitações — BICAMERAIS COMPLETAS 2018–2026** (verificado 2026-09-22): **705.096 linhas**
  (Câmara 544.930 / Senado 160.166). **Câmara:** 41.046 proposições, via `run_tramitacoes.py` +
  `backfill-tramitacoes.yml`; a nuvem fez ~66% (rate-limit por IP de runner) e o resto fechou local.
  **Senado:** ~11.826 matérias, via `run_tramitacoes_senado.py` + `backfill-tramitacoes-senado.yml`
  (recupera o `id_processo` pelo detalhe da matéria, não persistido) — a nuvem **fechou 100% sozinha**
  (API do Senado é outro host, sem o throttle da Câmara; 0 falhas). *(Presença — Área E — já está
  completa nas duas casas; ver bullet acima.)* Top-ups opcionais: **2020 votação=1.663** e **2018
  matérias do Senado (só 21)**.
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
- **Testes:** ingestão **345** + Prometeus **29**, sem rede (`cd codigo/services/<serviço> && py -m unittest discover -s . -t .`).

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

**Emendas — autoria (autoria FECHADA em 99,986%; resíduo explícito):**
- **APLICAR as migrations `0023`/`0024` (relatoria) + `0030` (view `emenda_autoria_resumo_publico`)**
  no SQL Editor — a view é DDL (não deu pra aplicar via PostgREST) e a tool `emendas_resumo` do
  Prometeus depende dela. O resto de 0026–0029 já foi aplicado via PostgREST (DML).
- ✅ **Comissões — FECHADAS:** 13 sigla+casa (`0025`) + 11 sucessão de órgão (`0027`) + 2 do Senado
  (`0028`) + 3 mistas criadas (`0029`) + S/I→Relator-Geral (`0030`). **Sobram 7 (R$9,5mi, 0,0045%):**
  rótulo 5035 (CFFC+CDC, sem órgão único) + CSF extinta — ficam como **resíduo explícito** (view acima),
  contados no total geral e reportados pelo `emendas_resumo`, nunca somem de ranking. Não há mais nada
  a atribuir sem inventar (§1).
- ✅ **Individuais — FECHADO (dedup dos 203 residuais):** migration `0026`, casa na data do fato por
  mandato oficial + verificação adversarial (ver `DEDUP-EMENDAS-INDIVIDUAIS.md`). **0 individual pendente.**
- **~675 `pendente_conferencia`** em `id_externo` (autor_orcamentario) — **sign-off humano** (casamento
  por nome = 1 sinal); ao conferir, marcar `conferido_por_humano` e re-rodar (não editar id_externo cru).

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
6. **Rodar a migration `0018_follows`** (sem ela o "seguir" não persiste). *(A `0019_presenca` já foi
   aplicada e o backfill de presença rodou — ver §Feito recentemente.)*

**Parqueado (dependências externas / decisão futura):**
8. **E-mail de produção — comprar domínio + verificar no Resend.** Sem domínio verificado, só o
   e-mail da conta Resend recebe o código.
9. **WhatsApp Business** — habilitação Meta em paralelo (dependência externa mais longa).

**Feito recentemente:**
- ✅ **Presença (Área E) — construída e no ar, BICAMERAL.** migration `0019` aplicada + backfill na
  nuvem (`backfill-presenca.yml` + `backfill-presenca-senado.yml`, 9 anos cada, success). **1.580
  sessões, 528.495 registros** (Câmara 1.141 = lista de presença; Senado 439 = comparecimento em
  votações — sem lista de presença por sessão na fonte do Senado). View ouro `presenca_publica` com %
  realistas nas duas casas. Era a última área sem coletor → **9/9 áreas servidas**. 12 testes novos
  (suíte 339).
- ✅ **Tramitações BICAMERAIS completas** (Câmara 544.930 + Senado 160.166 = 705.096 linhas).
- ✅ **Emendas — autoria fechada (98,5%):** individuais ~100% + **bancadas estaduais como perfil
  coletivo** (27 perfis `tipo='bancada'`, 1.882 emendas, views `bancada_*` + ferramentas Prometeus
  `buscar_bancada`/`emendas_por_autor_perfil`). Migrations 0020–0022.
- ✅ **Supabase Free → Pro** (plano pago ativo — mais espaço).
- ✅ **Chave da Anthropic criada**; **projeto GCP `aquarius-prometeus` + APIs (Cloud Run, Cloud
  Build) ativas**; crédito grátis do GCP ligado.
- ✅ **Supabase MCP conectado** (via Conectores da GUI) — usado nesta sessão pra validar o dado.
- ✅ **Repo PÚBLICO** (Actions grátis/ilimitado) + **secrets do repo setados** (`SUPABASE_URL`/
  `SUPABASE_SERVICE_KEY`, via API) → a **ingestão incremental roda na NUVEM** 2×/dia (leve) +
  1×/semana (completa), sem PC ligado. Confirmado ao vivo: run #100 verde gravou
  proposições/eventos/discursos frescos no Supabase (2026-09-17 18:xx UTC).
- ✅ **2 fixes de coleta** pushados: API Câmara exige `idLegislatura` (despesa) e janela de data
  larga dá HTTP 400 (proposições/votações → fatiamento em pedaços ≤60 dias).
- ✅ **Backfill de ATIVIDADE histórico na nuvem — proposições + discursos FEITOS 2018–2026.**
  Novo flag `AQUARIUS_TRAMITACOES=0` (desacopla a cauda cara) + workflow `backfill-atividade.yml`
  (**matriz por ano em paralelo**, sem PC). Run #1 encheu **proposições** (~34 mil) e **discursos**
  (~92 mil) de todos os anos.
- ✅ **Votações — COMPLETAS 2018–2026** (total 65.623). Dois consertos no caminho (`fdb3fac`,
  **327 testes verdes**): (a) o lookup voto→perfil fazia **um SELECT ao Supabase por voto**
  (44 mil/ano) → **memoizado** (45k reads → ~600), matando o gargalo de tempo; (b) **retry em
  502/503/504** de gateway (um 502 avulso derrubava o ano). Achado de ambiente: nos **2 anos mais
  pesados (2021, 2023)** a API da Câmara **rate-limita o IP do runner** quando as votações rodam
  por último (após ~7k proposições + ~25k discursos); fechados numa passada **votações-primeiro
  local** (2021: 308.971 votos nominais; 2023: 123.525).

> **GitHub Actions:** repo público = **grátis e ilimitado**. Workflows na nuvem (sem PC):
> `ingestao.yml` (incremental, 2×/dia leve + 1×/semana completo), `backfill-atividade.yml`
> (proposições/votações/discursos histórico), `backfill-tramitacoes.yml` e
> `backfill-tramitacoes-senado.yml`, `backfill-presenca.yml` e `backfill-presenca-senado.yml` (matriz
> por ano). Atividade + tramitações + **presença BICAMERAIS COMPLETAS** (2018–2026). **Falta ainda:**
> ajustar o diário "leve" pra ser mesmo leve. **Lição de ambiente:** a API da **Câmara** rate-limita
> por IP de runner sob volume alto (a nuvem faz o grosso, o rabo teimoso fecha local); a API do
> **Senado** (outro host) NÃO tem esse throttle — fechou 100% na nuvem.

## 8. Próximo passo

**Plano refeito em 5 partes — detalhe no `PLANO.md` (topo). Ordem decidida: 1 → 2 → 3 → 4 → 5.**

- **Parte 1 — ligar o que já está pronto:** rodar migration `0018`; **deploy do Prometeus (2.4)**
  pelo dev (gcloud + `ANTHROPIC_API_KEY` no painel + `EXPO_PUBLIC_PROMETEUS_URL`); secrets do repo
  p/ ingestão agendada; **segurança** (revogar PAT + rotacionar service key); wire dos botões de IA.
- **Parte 2 — completar os dados (2ª rodada):** atividade (proposições/votações/discursos/eventos)
  **2018–2026 COMPLETA** ✅; **tramitações BICAMERAIS (Câmara + Senado) 2018–2026 COMPLETAS** ✅.
  **presença (Área E) BICAMERAL COMPLETA** ✅ (1.580 sessões / 528.495 registros / `presenca_publica`).
  **Falta ainda:** "justificadas" (a fonte do Senado até distingue os motivos de ausência — dá pra
  extrair depois); paridade (frentes Senado, blocos Câmara, votações do Senado nos anos históricos);
  juntar as 2 pernas de tramitação (Câmara↔Senado da mesma matéria); curadoria (linhagem de partidos);
  top-ups opcionais (**2020 votação**=1.663; **2018 matérias do Senado**=21).
- **Partes 3–5** (produto/social → monetização/mobile → DaaS): detalhe no `PLANO.md`.

## 9. Notas de ambiente

- Interpretador Python é **`py`** (não `python`, alias fantasma da Microsoft Store).
- **Testes sem rede:** ingestão **345** + Prometeus **29** = **374** verdes. Rodar dentro de cada
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
