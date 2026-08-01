# CLAUDE.md — ponto de entrada para o Claude Code

Você está lendo isto porque a pasta **Aquarius Rede Social** foi conectada
a você. Antes de qualquer outra ação, leia este arquivo por inteiro. Depois
leia `ESTADO_ATUAL.md`. Só então proponha ou execute qualquer tarefa.

---

## Mapa desta pasta

Esta pasta mistura três coisas: documentos-fonte do usuário, o protótipo
navegável, e o código do produto real. **Não invente arquivos.** O que
existe está listado abaixo — se pediram para você mexer em algo que não
está aqui, pergunte antes de agir.

### Documentos de trabalho (na raiz)

- `CLAUDE.md` — este arquivo.
- `ESTADO_ATUAL.md` — onde o desenvolvimento está e qual é o próximo passo.
  **Leia este antes de tudo.**
- `PLANO.md` — auditoria do plano original e plano em 12 fases (Ondas).
- `ONDA-0-LEIA-ME.md` — o que foi entregue na fundação de identidade.
- `ONDA-1-LEIA-ME.md` — o que foi entregue na ingestão da Câmara.

### Código do produto (subpasta `codigo/`)

Todo o código real vive aqui. Nada de código deve ser criado fora.

- `codigo/packages/types/` — tipos TypeScript compartilhados (app + admin).
- `codigo/packages/ui/` — tokens de design + preset de Tailwind.
- `codigo/services/ingestao/` — coletores em Python (Câmara, futuro Senado
  e Siga Brasil), com resolução de identidade e pipeline em camadas.
- `codigo/supabase/migrations/` — migrations SQL (0001, 0002, 0003…).

### Documentos-fonte (originais do usuário, NÃO editar)

- `Aquarius_Metodologia_de_Dados.docx` — jul/26. **Autoridade máxima sobre
  a camada de dados** (ingestão, identidade, qualificação, contrato de
  resposta).
- `Aquarius_Concepcao_do_Produto.docx` — jul/26. **Autoridade máxima sobre
  intenção de produto e arquitetura macro.**
- `PRD_Aquarius_redesocial/` — 4 arquivos PRD_*.md (mai/26), histórico
  do produto. Cede para os DOCX acima quando houver conflito.

### Protótipo navegável (não portar, referência de UX)

- `Aquarius Rede Social.zip` — pacote completo do protótipo (HTML + JSX
  + imagens). Contém `handoff/prototype/*.jsx` que definem cada tela e
  `handoff/docs/*.md` que documentam UX, dados, API, DaaS, ROADMAP antigo.
- `Aquarius Rede Social Homepage (standalone).html` — landing.
- `Aquarius Rede Social Deck (standalone).html` — pitch em slides HTML.
- `Aquarius - Protótipos.dc.html` — protótipo de design.

### Referências visuais (PNGs numerados)

19 imagens de tela do app e do admin: `01-splash.png`, `02-login.png`,
`03-onboarding.png`, `04-feed.png`, `05-explorar.png`, `06-moderacao.png`,
`06-prometeus-lista.png`, `07-prometeus-chat.png`, `07-prometeus.png`,
`08-interesses.png`, `08-usuarios.png`, `09-calendario.png`,
`09-engajamento.png`, `10-audiencias-daas.png`, `10-notificacoes.png`,
`11-feature-flags.png`, `11-perfil-parlamentar.png`, `12-auditoria-lgpd.png`,
`12-proposicao.png`, `13-equipe-permissoes.png`, `13-partido.png`,
`14-comissao.png`, `14-configuracoes.png`, `15-frente.png`, `16-busca.png`,
`17-listagem.png`, `18-configuracoes.png`, `19-editar-perfil.png`,
`01-visao-geral.png`, `02-pipelines.png`, `03-feed-posts.png`,
`04-stories.png`, `05-revisao-editorial.png`.

**Estes são screenshots (imagens), não documentos de texto.** Não
interprete os números como se fossem uma série de arquivos `.md`
numerados. Se for descrever esta pasta, use ferramenta de listagem —
não infira.

### Material de marketing

`aquarius-pitch-deck-v6.pptx` (mais recente), versões anteriores, e
`aquarius-one-pager-v2.pdf`. Referência de posicionamento.

---

## Regras de conduta (obrigatórias)

Estas regras existem porque a Metodologia de Dados na `.docx` cataloga
doze modos de falha, e o modo nº 10 — "ausência concluída de amostra" —
já se manifestou nesta sessão: uma sessão anterior do Claude Code, ao
não achar um arquivo, **inventou uma lista de arquivos vizinhos**
(`00_MASTER_Brief_Aquarius.md`, `01_Estrategia_e_Pivo.md`, `99_Decisoes_Pendentes_e_Conflitos.md`,
subpasta `Aquarius Beta/PRDs Aquarius MVP`) que **não existem**. As
regras abaixo previnem que isso se repita.

### 1. Verificar antes de descrever

Toda descrição de arquivos ou pastas exige listagem por ferramenta,
citada literalmente. Nunca inferir nomes de arquivo a partir de padrões
que você vê em nomes vizinhos. Se você viu `01-splash.png` e
`02-login.png`, isso **não** significa que existe `03-qualquer_coisa.md`.

### 2. Ausente é ausente

Quando pediram X e X não existe, a resposta correta é "não encontrei X".
Não é "encontrei Y, Z, W que parecem cumprir papel semelhante" a menos
que Y, Z, W tenham sido listados por ferramenta e realmente existam.

### 3. Fatos com fonte, ou tag de incerteza

Ao afirmar algo sobre o produto (regra, valor, prazo, política), cite o
arquivo e trecho de origem, ou marque a afirmação como `[inferido]`. Se
não tem base, diga que não tem base.

### 4. Nada de suposição sobre ambiente

Antes de propor um comando, verifique se a ferramenta existe. Antes de
usar rede, saiba que este ambiente pode ou não ter. Antes de assumir
uma versão de biblioteca, cheque.

### 5. Não editar migration antiga

Correções vêm em migration nova (padrão que 0003 estabeleceu). Isso
preserva o histórico de decisão e o comportamento de bancos já em
produção.

### 6. Testes seguem a disciplina da Metodologia

Cada regra tem um caso que aceita e um que recusa. "Verificação que
sempre passa é indistinguível de verificação desligada" (Metodologia,
seção 5.2).

### 7. Não copiar código de terceiros

- `basedosdados/pipelines` — sem licença explícita. OK usar como
  referência para nomes de campo de API pública (fato factual, não
  copyrightável). NÃO copiar linha de código.
- `parlametria/leggo-backend` — AGPL-3.0. Copiar contamina o produto
  inteiro. OK ler como referência de modelagem.

---

## Hierarquia de fontes (onde documentos discordam)

Fixada com o usuário. Onde os documentos entram em conflito, quem manda
é, nesta ordem:

1. **Protótipo** (arquivos dentro do `Aquarius Rede Social.zip` +
   PNGs de tela) — autoridade máxima sobre o que é observável em tela:
   layout, texto, fluxo, cor, comportamento de interação.
2. **Metodologia de Dados** (`Aquarius_Metodologia_de_Dados.docx`) —
   autoridade máxima sobre camada de dados.
3. **Concepção do Produto** (`Aquarius_Concepcao_do_Produto.docx`) —
   autoridade máxima sobre intenção de negócio, público, princípios.
4. **Handoff** (`docs/` dentro do zip) — referência de implementação e
   shape de dados.
5. **PRDs** (`PRD_Aquarius_redesocial/*.md`) — histórico, cede para tudo
   acima.

## Decisões travadas (não reabrir sem discussão)

- **Banco/Auth/Storage:** Supabase (Postgres gerenciado + Auth + RLS).
  Não usar Postgres/Redis self-hosted.
- **Backend de dados e IA:** Python 3.12+ (ecossistema de dados/LLM).
- **App:** React Native (Expo). **Admin:** Next.js (App Router).
- **Sem `apps/api` gateway REST genérico** — leitura vai direto ao
  Supabase com RLS; código de servidor próprio só para DaaS, IA, ações
  admin privilegiadas e ingestão.
- **Login:** OTP por SMS ou e-mail primeiro; WhatsApp começa em paralelo
  porque a habilitação Meta Business é lenta.
- **Ordem invertida:** premium/billing **antes** de DaaS. Ver `PLANO.md`
  Parte 4 (cálculo de k-anonimato mostra que DaaS só é vendável na
  casa de centenas de milhares de usuários consentidos).

## Princípios inegociáveis

1. Todo post/story cita fonte oficial. Sem `source` + `source_url` +
   `synced_at`, não publica.
2. Neutralidade — posts em terceira pessoa, factuais. IA contextualiza,
   não opina.
3. DaaS só agrega. Zero PII exportada. k-anonimato + consentimento na
   borda.
4. Perfil opcional é opt-in — renda, escolaridade, ocupação são nudge,
   nunca obrigatório.
5. `confianca_ia < 0.65` **ou** `null` → revisão humana antes de
   publicar. Confiança ausente ≠ confiança baixa, mas ambas exigem
   revisão.
6. Identidade resolvida na data do fato, nunca no presente. Voto de 2021
   resolve o partido de 2021.

---

## Como trabalhar

1. Leia `ESTADO_ATUAL.md`.
2. Rode os testes existentes antes de propor qualquer mudança:
   ```
   cd codigo/services/ingestao
   py -m unittest discover -s . -t .
   ```
   Devem passar **239 testes** com "OK". Se não, primeiro problema a resolver.
   (Neste ambiente o interpretador é `py`, não `python` — o `python` é o alias
   fantasma da Microsoft Store.)
3. Ao terminar uma peça de trabalho, atualize `ESTADO_ATUAL.md` para
   refletir o novo estado.
4. Ao entregar novo módulo, crie um `ONDA-N-LEIA-ME.md` explicando o que
   mudou e por quê.

Se algo neste arquivo estiver desatualizado em relação ao código,
**pergunte antes de agir**. Não infira, não corrija por sua conta.
