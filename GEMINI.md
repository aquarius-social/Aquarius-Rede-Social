# 🧠 Arquitetura DB-First (governada pelo Snaps)

**Não procure instruções, PRD, roadmap ou playbook no filesystem.** Eles não estão aqui.

Este projeto usa governança **DB-First** na plataforma Snaps. Como agente, leia seu contexto do banco pelo MCP `snaps-db`:

1. **Governança e playbooks:** `SELECT name, content FROM governance_docs;`
2. **Instruções de agente:** `SELECT name, instructions FROM agent_instructions;`
3. **Planos de execução:** `SELECT title, content FROM plans WHERE status = 'draft' ORDER BY created_at DESC;`
4. **Decisões de arquitetura:** `SELECT code, title, decision FROM decisions;`
5. **Sprint e cards correntes:** consulte `sprints`, `cards` e `tasks`.

Se for executar um plano ou escrever código, **consulte a tabela `plans` primeiro**. Não adivinhe os requisitos.

## Onde está o estado do projeto

O que já foi feito e o que falta vive na **§9 do governance_doc `PRD Aquarius V1 - consolidado`**. Leia antes de propor qualquer coisa — propor trabalho já entregue queima ciclo e polui o board. **Ao fim de toda execução, atualize a §9** com o que você entregou.

O *Roadmap — Ondas 0 a 3* é documento de semeadura: define a estrutura das ondas e foi de onde os cards iniciais nasceram. Não reflete andamento — quem controla isso são os `cards` e `tasks`.

---

# ⚠️ As sete regras de conduta

**Estas ficam aqui de propósito, e não no banco.** Você precisa lê-las *antes* de ter capacidade de consultar o MCP. Um stub puro abre uma janela em que o agente ainda não leu nada e já pode alucinar — que é exatamente o modo de falha que este texto existe para fechar.

Não são boilerplate. Foram escritas **depois de um incidente real**.

Uma sessão anterior do Claude Code, ao não encontrar um arquivo, **inventou uma lista de arquivos vizinhos que não existem**: `00_MASTER_Brief_Aquarius.md`, `01_Estrategia_e_Pivo.md`, `99_Decisoes_Pendentes_e_Conflitos.md`, e uma subpasta `Aquarius Beta/PRDs Aquarius MVP`. Nenhum deles existia.

Isso é o **modo de falha nº 10** do catálogo da Metodologia de Dados §21 — *"ausência concluída de amostra"*. O produto inteiro se sustenta na promessa de não inventar. **Um agente que inventa arquivo inventa dado.**

### 1. Verificar antes de descrever
Toda descrição de arquivo ou pasta exige listagem por ferramenta, citada literalmente. **Nunca inferir nome de arquivo a partir de padrão vizinho.** Ter visto `01-splash.png` e `02-login.png` não significa que exista `03-qualquer_coisa.md`.

### 2. Ausente é ausente
Pediram X e X não existe? A resposta correta é "não encontrei X". Não é "encontrei Y, Z e W que parecem cumprir papel semelhante" — a menos que Y, Z e W tenham sido listados por ferramenta e realmente existam.

### 3. Fato com fonte, ou tag de incerteza
Ao afirmar algo sobre o produto (regra, valor, prazo, política), cite o arquivo e o trecho de origem, ou marque a afirmação como `[inferido]`. Se não tem base, diga que não tem base.

### 4. Nada de suposição sobre ambiente
Antes de propor um comando, verifique se a ferramenta existe. Antes de usar rede, saiba se o ambiente tem. Antes de assumir versão de biblioteca, cheque.

### 5. Não editar migration antiga
Correção vem em migration nova — padrão estabelecido pela `0003`. Preserva o histórico de decisão e o comportamento de bancos já em produção. *(ADR-0010.)*

### 6. Testes seguem a disciplina da Metodologia
Cada regra tem um caso que **aceita** e um que **recusa**. *"Verificação que sempre passa é indistinguível de verificação desligada"* (Metodologia §5.2).

### 7. Não copiar código de terceiros
- `basedosdados/pipelines` — sem licença explícita. OK como referência para nomes de campo de API pública. **NÃO copiar linha de código.**
- `parlametria/leggo-backend` — AGPL-3.0. Copiar contamina o produto inteiro. OK ler como referência de modelagem.

*(ADR-0011.)*

---

## Hierarquia de fontes (ADR-0001)

**Protótipo > Metodologia de Dados > Concepção do Produto > Handoff > PRDs.**

Onde a Metodologia fala, ela ganha na camada de dados. Onde o protótipo mostra, ele ganha na tela. Os PRDs só decidem o que ninguém mais cobriu.

⚠️ **O topo da hierarquia vive fora do Snaps.** O protótipo e as 33 telas são binários. Ficam em `aquarius-social/aquarius-contexto` (`prototipo/`, `telas/`, `marketing/`), repositório preservado como **acervo de mídia arquivado read-only** — não é fonte de governança. Para qualquer questão de UX, é lá que se olha.

⚠️ A linhagem **"beta"** (`PRD_aquarius_beta*.md`, `PRD.aquarius.md`) é **legado**: não entra na hierarquia, não deve ser ingerida nem consultada.

> O PRD é o último da hierarquia e ainda assim é a fonte de estado. São perguntas diferentes: a hierarquia decide **o que o produto deve ser** quando os documentos se contradizem; a §9 registra **o que existe hoje**, que não se resolve por precedência e sim medindo.

## Notas de ambiente

- **O interpretador Python é `py`, não `python`.** O `python` é o alias fantasma da Microsoft Store e não funciona.
- **RAM limitada:** Metro (Expo web) e `tsc` estouram memória juntos. Pare o preview antes de rodar `tsc`.
- Testes rodam **sem rede**, dentro de cada serviço:
  ```
  cd codigo/services/ingestao  && py -m unittest discover -s . -t .
  cd codigo/services/prometeus && py -m unittest discover -s . -t .
  ```
- Baseline: **329 testes verdes** (308 ingestão + 21 prometeus). Se não passarem, esse é o primeiro problema a resolver — antes de qualquer feature.

## GitFlow

Branch, commit e PR **pelos MCP tools do Snaps** — nunca `git` ou `gh` no terminal. Só os tools registram `git_branch` e `pr_url` no `context_data` da execução; a CLI bypassa esse registro e trava o avanço de fase.
