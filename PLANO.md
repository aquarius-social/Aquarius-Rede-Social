# Aquarius — Plano de execução v2

Substitui integralmente o `PLANO_AQUARIUS_v1.md`. Incorpora os dois documentos de
julho de 2026 (`Concepção do Produto` e `Metodologia de Dados`), que são as fontes
mais recentes do acervo e resolvem várias contradições que o v1 apontava em aberto.

---

## ⭐ PLANO REFEITO (2026-09) — a fonte de verdade atual

> As Partes 1–6 abaixo são o plano original (ago/2026) — valem como **histórico e
> decisões travadas** (hierarquia de fontes, arquitetura do Prometeus, matemática do
> k-anonimato). Esta seção, no topo, é o **plano corrente**, refeito depois do backfill
> 2018–2026, da migração para Supabase **Pro** e do repositório ter ficado **público**.

### Onde estamos (set/2026)

Prontos: dinheiro **2018–2026 das duas casas** (~1,86 mi despesas + 48k emendas);
fundação de identidade + **perfis históricos inativos** (ex-parlamentares fora do app, só
memória do Prometeus); **app de leitura** (~15 telas, web na Vercel); **admin** (14 telas +
RBAC + revisão editorial, na Vercel); **Prometeus 2.0–2.2** (validado, 21 testes); **repo
público** (Actions grátis); Supabase **Pro**. O bloqueio `⛔Pro` caiu em toda a lista de
`MELHORIAS.md` — onde estava "truncado por espaço", agora falta **execução (2ª rodada)**,
não espaço nem código novo.

### As 5 partes — ordem decidida com o usuário: **1 → 2 → 3 → 4 → 5**

**Parte 1 — Ligar o que já está pronto** 🟢
- Rodar a migration `0018_follows` (destrava seguir persistido + feed "Seguindo").
- **Deploy do Prometeus (2.4)** — pelo dev: `gcloud run deploy` de `codigo/services/prometeus/`,
  colar `ANTHROPIC_API_KEY` no painel do Cloud Run, setar `EXPO_PUBLIC_PROMETEUS_URL` no app →
  **chat da IA ao vivo**.
- Pôr `SUPABASE_URL`/`SUPABASE_SERVICE_KEY` nos secrets do repo → ingestão agendada roda sozinha.
- **Segurança:** revogar o PAT do GitHub + rotacionar a `service_role` do Supabase (circularam no chat).
- Wire dos botões "Perguntar ao Prometeus" nos perfis.

**Parte 2 — Completar os dados (2ª rodada)** 🟡 ← *próxima após a Parte 1*
- **Validar o canário de proposições** (nunca rodado ao vivo — dívida de integridade nº1).
- Backfillar **proposições / votações+votos / tramitações / discursos** 2018–2026 (código pronto).
- **Paridade:** frentes do Senado + blocos da Câmara (faltam nas duas direções).
- **Juntar as 2 pernas de tramitação** (identidade cross-casa da proposição).
- **Presença** (Área E) — coletor novo (não existe).
- **Curadoria:** linhagem de partidos (`partido_id` histórico), resíduo de autores de emenda (12%),
  vínculo do senador 5718, mapa de autores de emenda multi-ano.

**Parte 3 — Conteúdo da IA + camada social** 🔴
- Tabelas `post`/`story`/`editorial_review`/`retratacao` + social (`reacao`/`comentario`/`salvo`/
  `compartilhamento`) + `notificacao` + `feature_flags` + `audit_log`.
- **Prometeus 2.3:** IA gera post → fila editorial no admin → publica (gating `confiança < 0.65`
  ou null → revisão humana). Ligar a **Revisão editorial** ponta-a-ponta (o freio) + server actions.
- App: feed editorial + curtir/comentar/salvar/compartilhar + stories + notificações.
- Ligar as 14 telas do admin nas tabelas reais (hoje são UI sobre dado de demonstração).

**Parte 4 — Monetização + mobile + produção** 🔴
- **Premium/billing (Stripe)** — ordem travada: **antes** do DaaS.
- **App mobile via EAS** (builds nativos, push, ícones/splash).
- Robustez (paginação/cache/error boundaries), acessibilidade, LGPD acionável (exportar/deletar),
  compartilhamento nativo, fotos reais de perfil.
- E-mail de produção (domínio + Resend); login por SMS/WhatsApp.

**Parte 5 — DaaS + enriquecimento externo (longo prazo)** ⛔escala
- Decidir **k** (com parecer jurídico); instrumentação de engajamento consentida.
- DaaS k-anônimo; **convênios/transferências** ("pra onde o dinheiro foi de fato").
- Enriquecimento externo (eleitoral/patrimônio/judiciário); Siga Brasil; backfill pré-2018.

### Gotchas registrados

- **Canário de proposições** nunca validado ao vivo; hoje roda assumindo `canario_validado=True`.
  Validar antes de backfillar atividade (Parte 2).
- **2 bugs de ingestão já corrigidos** (overlap de vínculo `c67b275`; API da Câmara exigindo
  `idLegislatura` `f2f9cfc` — este também consertava a ingestão de produção).
- Admin: as 14 telas existem como UI, mas **sem escrita real** até as tabelas da Parte 3.

---

## Parte 1 — Hierarquia de fontes (decidir isto primeiro resolve metade das dúvidas)

O acervo tem quatro gerações de documento, e elas se contradizem porque foram
escritas em momentos diferentes, não porque alguém errou. A ordem cronológica é:

| Quando | Documento | Papel proposto |
|---|---|---|
| Julho 2026 | **Metodologia de Dados** | **Autoridade máxima sobre a camada de dados**: modelo relacional, identidade, qualificação, ingestão, contrato de resposta da IA. |
| Julho 2026 | **Concepção do Produto** | **Autoridade máxima sobre intenção de produto e arquitetura macro**: o que o produto é, para quem, e por quê. |
| Julho 2026 | **Protótipo** (`.dc.html` + PNGs) | **Autoridade máxima sobre UX**: layout, textos, fluxo, comportamento de tela. Já é a regra vigente no `CLAUDE.md`. |
| Junho 2026 | **Handoff** (`docs/*`, `prototype/*.jsx`) | Referência de implementação e *shape* de dados. Cede para os três acima. |
| Maio 2026 | **PRDs** (4 arquivos) | Contexto histórico e regras de negócio ainda não cobertas pelos documentos novos. Cede para todos os acima. |

**Regra prática:** onde a Metodologia de Dados fala, ela ganha na camada de dados.
Onde o protótipo mostra, ele ganha na tela. Os PRDs só decidem o que ninguém mais
cobriu. Vale gravar isso no `CLAUDE.md` — sem essa regra escrita, cada divergência
vira uma decisão nova no meio da implementação.

---

## Parte 2 — O que os documentos novos resolvem

Cinco contradições que o v1 deixou em aberto agora têm resposta oficial.

**Perfil polimórfico: confirmado, e com mais rigor do que se supunha.** A Concepção
é explícita: "Partidos, comissões e frentes são o mesmo objeto, com o conjunto de
abas próprio de cada um". E a Metodologia vai além, definindo `profiles` como
identificador próprio do Aquarius, com uma tabela `id_externo` mapeando para os
identificadores da Câmara, do Senado e do código de autor orçamentário, cada
ligação carregando método e grau de confiança. Fecha a questão: o
`DATA-MODEL.md` do handoff, que lista entidades separadas, está desatualizado.

**Backend em Python: confirmado.** A Concepção fixa "o backend, em Python, sobre um
banco PostgreSQL". Encerra a disputa entre o `CLAUDE.md` ("TS em todo lugar") e o
`PRD_agent` (Python). A camada de dados e a IA são Python; o app e a Torre de
Controle continuam em TypeScript.

**Selo azul: confirmado e coerente.** Verificação por identidade real, restrita a
comunicadores, analistas, jornalistas e acadêmicos, **vedada a parlamentares e
partidos**. Isso resolve a estranheza que a auditoria encontrou — o único campo
`verificado` que existe hoje nos dados está justamente na entidade que não pode ser
verificada.

**Nada é consultado ao vivo: confirmado como princípio de arquitetura.** A
Metodologia é categórica: "nada é servido ao oráculo sem percorrer todas as
camadas, e nada é consultado ao vivo no momento da pergunta". Isso valida a decisão
de shadow cache e define o pipeline em três camadas — bruto imutável, tratado,
servido — com portão de qualidade e quarentena entre elas.

**IA consulta o banco de forma estruturada, não por busca semântica.** A Concepção
justifica: modelo de linguagem solto alucina tabela, coluna e valor. O Prometeus
usa consulta ancorada no esquema, com a fonte explícita, e um contrato de resposta
de sete regras que obriga declarar fonte, data, base da atribuição, e recusar
quando não há base. Isso não é detalhe de implementação — é a promessa central do
produto, e precisa de teste automatizado desde cedo.

---

## Parte 3 — A correção que devo ao plano anterior

No v1 recomendei trocar o login por WhatsApp por SMS ou e-mail, tratando o WhatsApp
como burocracia dispensável no início. **A Concepção do Produto muda esse quadro.**

O WhatsApp não é só o meio de enviar um código de login. É descrito como o canal
por onde o Prometeus "chega primeiro" ao usuário, justificado pelo alcance de cerca
de 94% do público brasileiro conectado. Ou seja, é um canal de distribuição do
produto, não um detalhe de autenticação.

Isso não invalida a recomendação técnica — continua sendo certo **não bloquear o
desenvolvimento** esperando aprovação da Meta, e continua sendo certo abstrair o
fluxo de autenticação para que a troca seja barata. Mas inverte a prioridade
gerencial: por ser lento, burocrático e fora do seu controle, **o processo de
habilitação do WhatsApp Business deve ser iniciado agora, em paralelo**, e não
adiado. É a dependência externa mais longa do projeto inteiro.

---

## Parte 4 — O que ainda está em aberto

**O valor de k no anonimato.** A Metodologia e a Concepção falam em "garantia de
anonimato por grupo mínimo" sem fixar número. O k ≥ 1.000 vem do
`ANALYTICS-DAAS.md` e de uma constante do protótipo — é parâmetro, não lei. Isso
importa muito: a conta que fiz no v1 mostrava que k = 1.000 exige da ordem de
250 mil usuários consentidos para uma célula comum passar. Com k = 100, o mesmo
recorte precisa de cerca de 25 mil. **A escolha de k decide se o DaaS é produto de
médio ou de longuíssimo prazo.** Merece decisão consciente, com parecer jurídico,
não herança de uma constante de protótipo.

**As dimensões do DaaS.** A Concepção descreve apenas "engajamento por tema e por
região". O protótipo implementa oito dimensões, incluindo renda, escolaridade e
ocupação — dados sensíveis, coletados por nudge opcional, com cobertura baixa. Há
uma diferença real de ambição e de risco entre as duas versões, e o documento mais
recente é o mais modesto.

**Curtir e descurtir.** Os PRDs pedem *like* e *dislike*; o protótipo implementa os
dois; o `DATA-MODEL.md` só prevê `likes`. O `PRD_admin` quer um heatmap de
sentimento construído sobre aprovação e rejeição — impossível sem o campo. Nenhum
dos documentos novos menciona *dislike*. Decisão de produto pendente, com
implicação direta de schema.

**Escopo do Prometeus no WhatsApp.** Se o WhatsApp é canal de entrega, ele é uma
superfície de produto inteira — com sessão, histórico, custo por mensagem e
moderação próprios. Nada nos documentos especifica esse recorte.

---

## Parte 5 — O plano

A Metodologia de Dados já traz um plano em ondas para a camada de dados, com a
regra "nenhuma onda começa antes de a anterior estar de pé". O plano abaixo
preserva essas ondas e encaixa o produto em volta delas — em vez de criar uma
terceira ordem concorrente.

### Onda 0 — Fundação (bloqueia tudo)

Da Metodologia: arquitetura, registro de fontes, **resolução de entidade** e
linhagem partidária. Do lado do produto: monorepo, dois ambientes Supabase,
segredos, integração contínua, `packages/types` e `packages/ui`.

O item mais importante desta onda é a resolução de identidade. A Metodologia é
clara sobre o motivo: se a identidade não estiver resolvida, todo cruzamento atribui
dado ao parlamentar errado, e a qualidade de todas as camadas seguintes deixa de
importar. Entram aqui `profiles`, `id_externo`, `vinculo_temporal` e `partido`
canônico com linhagem.

*Concluída quando:* a tabela de correspondência de identidade existe com grau de
confiança por ligação, os estudos de validação da Metodologia são reproduzíveis
contra o banco, e build e CI estão verdes.

### Onda 1 — Núcleo cívico

As nove áreas de dado da Parte II da Metodologia (despesas, proposições, votações,
tramitações, parlamentares, emendas, discursos, eventos, Senado), mais a junção
bicameral. Pipeline em três camadas com portão de qualidade e quarentena. Teste de
contrato com consulta-canário antes de cada ingestão. Cadência por volatilidade,
com janela móvel maior que a maior defasagem observada.

Em paralelo, porque não dependem do dado completo: autenticação, onboarding e
captura de consentimento; e o início do processo burocrático do WhatsApp Business.

*Concluída quando:* dado oficial real de todas as áreas está na camada servida, os
portões de qualidade estão ativos, a quarentena registra motivo, e um usuário real
completa o onboarding.

### Onda 1.5 — App de leitura

Explorar, perfis polimórficos, proposição, busca, interesses, calendário. Consome a
camada servida. Feed ainda vazio de conteúdo gerado.

Esta onda não está na Metodologia porque é produto, não dado — mas cabe aqui porque
não depende da inteligência derivada da Onda 2, e é o que permite validar o dado
com gente de verdade antes de investir em geração de conteúdo.

*Concluída quando:* dá para navegar dado oficial real no celular via Expo Go, com
proveniência e frescor visíveis na tela.

### Onda 2 — Inteligência derivada

Da Metodologia: resumos, classificação temática e rankings, **somente sobre dado
completo, com método publicado**. Aqui entram os posts em terceira pessoa, os
stories diários, o cache compartilhado de resumos, e o Prometeus com o contrato de
resposta de sete regras e o banco de perguntas com gabarito.

Junto: a Torre de Controle na parte que torna isso operável — revisão editorial,
Feed e Posts, Stories, Pipelines.

Precedida de estimativa de custo de LLM com teto configurável.

*Concluída quando:* o banco de perguntas com gabarito passa, incluindo os casos em
que a resposta correta é a recusa; e um editor humano aprova conteúdo pela
interface, com registro.

#### Construção do Prometeus — sub-etapas (Etapas 2.0 → 2.5)

> Detalhamento de execução da Onda 2, fechado com o usuário em 12/08/2026.
> "Etapa 2.x" é passo de construção **interno à Onda 2** — não confundir com a
> estratégica **Onda 2.5 (Camada social)** logo abaixo.

**Arquitetura travada** (o "como" do Prometeus):

- **Cérebro:** ReAct (loop nativo de tool-calling do Claude) como principal; **RAG**
  para dado textual (teor de proposição, discurso — via `pgvector` no próprio
  Supabase); **text-to-SQL** só para casos que pedem, sempre com guarda-corpos
  (role só-leitura, views restritas, tabelas em allow-list).
- **Ferramentas:** expostas por um **servidor MCP** próprio — cada consulta segura
  ao Supabase devolve dado + `source`/`source_url`/`synced_at`. Analogia: o agente
  é o pesquisador; as ferramentas MCP são as gavetas; o banco é o conteúdo das
  gavetas. Ampliar cobertura = **adicionar gaveta**, sem trocar o pesquisador.
- **Modelo:** **Sonnet 5** principal; fall-back **nativo Claude→Claude** (Sonnet 5 →
  Opus 4.8) em recusa/erro/limite — **1 chave (Anthropic)**. Cross-provider (OpenAI,
  ex.: "GPT-5.6 Terra" a validar) parqueado para depois, se o uptime exigir.
- **Hospedagem:** servidor próprio no **GCP** (Cloud Run + Secret Manager).
- **Faces:** fundação compartilhada (mesmo MCP/modelo/contrato), **endpoints
  distintos por tipo de info**; **geração de posts = pipeline dedicado**.
- **Ordem:** **chat primeiro**, posts depois.

**Sub-etapas:**

- **2.0 — Fundação e decisões.** Fixar o contrato de resposta lendo a Metodologia
  (autoridade); definir o conjunto inicial de ferramentas MCP e o dado disponível
  hoje (despesas Câmara+Senado, emendas, eventos). Pré-requisitos externos: chave
  Anthropic (com teto de gasto), chave do MCP, projeto GCP. *(As decisões de
  arquitetura acima já são parte desta etapa.)*
- **2.1 — Servidor MCP.** As consultas seguras ao Supabase com proveniência.
  Testável sem IA, na disciplina "um caso aceita, um recusa". As duas faces usam.
- **2.2 — Agente conversacional (ReAct) + ligar no app.** Loop Claude↔MCP; contrato
  de chat; gating de confiança → resposta honesta "não tenho esse dado". Trocar o
  placeholder de `app/prometeus/chat.tsx`.
- **2.3 — Pipeline de posts + freio editorial.** Seleção (quais fatos viram post) →
  gerar post neutro com fonte → gating: `confiança < 0.65` ou nula = fila de
  **revisão editorial no admin** antes de publicar; `≥ 0.65` = publica no feed.
- **2.4 — Deploy e operação.** Hospedar MCP + orquestrador + agendador dos posts no
  GCP; chaves como secrets; teto de gasto no painel Anthropic.
- **2.5 — Refino (pós-MVP).** Roteamento Haiku/Opus, RAG para texto, rate limit,
  observabilidade, monitor de custo, cross-provider (se necessário).

### Onda 2.5 — Camada social

Feed personalizado, stories, curtidas, comentários com thread, seguir,
compartilhar, notificações. Moderação entra junto, não depois — conteúdo político
atrai abuso desde o primeiro dia.

### Onda 2.75 — Instrumentação e monetização

Eventos de engajamento, já vinculados ao consentimento desde a Onda 0. Depois
premium, KYC e selo azul, com a regra de inelegibilidade de parlamentares aplicada.

### Onda 3 — Enriquecimento externo e DaaS

Da Metodologia: dados eleitorais, patrimônio, judiciário, sob demanda e com parecer
prévio. E o motor de audiências, condicionado à decisão sobre k e ao tamanho real
da base consentida.

---

## Parte 6 — Decisões que precisam de você antes da Onda 0

1. Confirmar a hierarquia de fontes da Parte 1 e gravá-la no `CLAUDE.md`.
2. Confirmar Supabase como banco, autenticação e storage, com backend Python.
3. Confirmar o corte do `apps/api` como gateway REST genérico.
4. Definir o valor de k do anonimato, com parecer jurídico.
5. Decidir se o produto terá *dislike*.
6. Confirmar o início imediato, em paralelo, do processo do WhatsApp Business.
