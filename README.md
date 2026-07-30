# Aquarius — Rede Social de Inteligência Legislativa

Plataforma de inteligência legislativa cujo componente central, o oráculo
**Prometeus**, responde em linguagem natural a perguntas de cidadãos sobre a
atividade parlamentar brasileira. A confiabilidade das respostas é construída na
**camada de dados** que antecede o modelo de linguagem — é dela que este
repositório trata.

## Estado atual

**Onda 1 — Ingestão da Câmara dos Deputados: completa em lógica**, testada sem
rede e verificada contra a API viva. Cobre proposições, votações (com votos
nominais), deputados (com enriquecimento), o histórico de mandatos
(`vinculo_temporal`, que resolve o partido *na data do fato*), partidos
canônicos, tramitações, a persistência e o orquestrador que amarra tudo.

O único elo que falta para rodar em produção é o **adaptador Supabase concreto**
(depende de credenciais de deploy). Ver `ESTADO_ATUAL.md` para o próximo passo.

## Mapa do repositório

```
codigo/
  packages/types/          tipos TypeScript compartilhados (app + admin)
  packages/ui/             tokens de design + preset Tailwind
  services/ingestao/       coletores em Python (Câmara), pipeline em camadas,
                           resolução de identidade, persistência, orquestração
  supabase/migrations/     schema SQL (0001–0005)
```

Documentos de trabalho na raiz:

- **`CLAUDE.md`** — regras de conduta e mapa do projeto (ponto de entrada).
- **`ESTADO_ATUAL.md`** — onde o desenvolvimento está e o próximo passo.
- **`ONDA-0-LEIA-ME.md` / `ONDA-1-LEIA-ME.md`** — o que cada onda entregou e por quê.
- **`ANALISE-Metodologia-vs-Codigo.md`** — decisões de dados conferidas contra a fonte.
- **`PLANO.md`** — auditoria e plano em fases.

## Rodar os testes

O ecossistema de dados/IA é Python 3.12+; os testes usam apenas `unittest`
(sem dependência externa) e rodam **sem rede** (HTTP e banco são injetados).

```bash
cd codigo/services/ingestao
python -m unittest discover -s . -t .
```

Devem passar **164 testes** com `OK`. (Em ambiente Windows onde `python` é o
alias da Microsoft Store, use `py` no lugar de `python`.)

Type-check dos pacotes TypeScript:

```bash
cd codigo/packages/types && npm install && npx tsc --noEmit
cd codigo/packages/ui    && npm install && npx tsc --noEmit
```

## Princípios inegociáveis (da Metodologia de Dados)

1. Todo post/story cita fonte oficial (`source` + `source_url` + `synced_at`).
2. Neutralidade: posts em terceira pessoa, factuais; a IA contextualiza, não opina.
3. DaaS só agrega — zero PII exportada (k-anonimato + consentimento na borda).
4. Perfil opcional é opt-in.
5. `confianca_ia < 0.65` ou `null` → revisão humana antes de publicar.
6. Identidade resolvida **na data do fato**, nunca no presente.

## Decisões de arquitetura travadas

- **Banco/Auth/Storage:** Supabase (Postgres gerenciado + Auth + RLS).
- **Backend de dados e IA:** Python 3.12+.
- **App:** React Native (Expo). **Admin:** Next.js (App Router).
- Leitura vai direto ao Supabase com RLS; servidor próprio só para DaaS, IA,
  ações admin privilegiadas e ingestão.

---

Material proprietário (metodologia e concepção em `.docx`, decks, protótipo,
imagens) **não é versionado** — ver `.gitignore`.
