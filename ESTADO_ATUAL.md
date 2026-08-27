# Estado atual do Aquarius

Documento de status do projeto — **snapshot completo e detalhado**. É o 2º arquivo a
ler (depois do `CLAUDE.md`). Complementos: `PLANO.md` (roadmap em ondas),
`RELATORIO_DESENVOLVIMENTO.md` (fotografia por camada, também publicada como página),
`MELHORIAS.md` (backlog A–I), `HISTORICO.md` (marcos e números de ingestão).

Atualização: 2026-08-12.

## Resumo executivo

O Aquarius tem **app (Expo) e admin (Next.js) no ar na Vercel**, com a camada de leitura
navegando dado oficial real (despesas, emendas, eventos) e login por OTP funcionando. A
peça em construção é o **Prometeus (Onda 2)** — o agente de IA. O **backend do Prometeus
está pronto e testado** (servidor MCP de consultas seguras + agente ReAct + endpoint),
faltando só **publicar (deploy no GCP)** e a **chave da Anthropic** para ligá-lo ao vivo. A
geração de posts (2ª face do Prometeus) e o deploy são os próximos grandes passos.

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
  enquanto não publicado. ⚠️ Esse arquivo está **commitado localmente, ainda não pushado** —
  o app publicado na Vercel segue com o placeholder até o push.
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
- **Banco no teto do Free (~476/500 MB).** Subir pro Pro destrava a reingestão das áreas
  truncadas.
- **Testes:** **308**, sem rede (`cd codigo/services/ingestao && py -m unittest discover -s . -t .`).

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
| **2.2 Agente ReAct + endpoint + ligar no app** | ✅ Código pronto — 21 testes; falta deploy + chave p/ ao vivo |
| **2.3 Pipeline de posts + freio editorial** | ⬜ Não iniciado |
| **2.4 Deploy (GCP Cloud Run)** | ⬜ Não iniciado (precisa chave Anthropic + GCP) |
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

### O que falta pra ligar o Prometeus ao vivo

1. **Chave da Anthropic** (Console + crédito + teto) — o motor.
2. **Deploy no GCP Cloud Run** (via `gcloud` local, sem GitHub — evita Actions).
3. Setar `EXPO_PUBLIC_PROMETEUS_URL` (app: env na Vercel + `.env` local) pra URL do Cloud Run.
4. **Pushar o `chat.tsx`** (hoje local) pra o app web publicado usar o chat real.

## 5. Deploys (o que está no ar)

- **Admin → Vercel** (produção). ✅
- **App web → Vercel** (`aquarius-rede-social-app.vercel.app`). ✅
- **Prometeus (serviço) → GCP:** ⬜ não deployado (Etapa 2.4).
- **App mobile → EAS:** ⬜ não iniciado.

## 6. Estado do git / repositórios

- **Repo de código** (`Aquarius-Rede-Social`): `origin/main` em `1861d90`. **Local está 2 commits
  À FRENTE, não pushados:**
  - `ae0019f` — `chat.tsx` + `requirements.txt` + `Procfile` (os "pusháveis").
  - `cd9b001` — `ci.yml` (economia de Actions; **precisa do escopo `workflow` no token** pra pushar).
  - Motivo de segurar o push: **GitHub Actions no limite do mês**; validação feita **localmente**
    pelos testes.
- **Repo de contexto** (`aquarius-contexto`): separado, sem alteração nesta sessão (prints/telas,
  docs-fonte, marketing, protótipo).

## 7. ⚠️ Ações pendentes do usuário (fora do código)

1. **Chave da Anthropic** (Console + crédito US$5–10 + teto ~US$20/mês) → destrava o teste ao vivo
   da 2.2 e o deploy 2.4. *(O plano Claude Max NÃO dá crédito de API — é cobrança separada.)*
2. **Projeto no GCP** → deploy do Prometeus (Cloud Run).
3. **GitHub Actions no limite** → reseta no próximo mês (ou tornar o repo de código público =
   Actions ilimitado, ou pagar). Até lá, **pushes segurados**.
4. **Escopo `workflow` no token do GitHub** → pra pushar o commit do `ci.yml`.
5. **E-mail de produção — comprar domínio + verificar no Resend** *(parqueado)*. Sem domínio
   verificado, só o e-mail da conta Resend recebe o código.
6. **Rotacionar a service key do Supabase** (circulou no chat; prioridade segurança).
7. **Rodar a migration `0018_follows`** (sem ela o "seguir" não persiste).
8. **Secrets do repo** (`SUPABASE_URL`/`SUPABASE_SERVICE_KEY`) pro agendador `ingestao.yml`.
9. **Supabase Free → Pro** — destrava a reingestão das áreas truncadas + várias frentes.
10. **WhatsApp Business** — habilitação Meta em paralelo (dependência externa mais longa).

## 8. Próximo passo

- **Imediato (caminho "ao vivo"):** usuário cria a **chave Anthropic** → **deploy do Prometeus no
  GCP (2.4)** → setar a URL no app → **teste ao vivo** do chat.
- **Em paralelo (sem pré-requisitos):** construir a **2.3 (pipeline de posts + freio editorial)** —
  Python, testável local.
- **Dados:** subir pro Pro e reingerir as áreas truncadas (destrava proposições/votações → mais
  ferramentas do Prometeus).

## 9. Notas de ambiente

- Interpretador Python é **`py`** (não `python`, alias fantasma da Microsoft Store).
- **Testes sem rede:** ingestão **308** + Prometeus **21** = **329** verdes. Rodar dentro de cada
  serviço: `py -m unittest discover -s . -t .`.
- **RAM limitada:** Metro (Expo web) e `tsc` estouram memória; parar preview antes do `tsc`. Ver a
  memória do projeto `ambiente-ram-limitada`.
- **GitHub Actions:** só `git push` dispara Actions; `git commit` local **não**. Estamos
  committando local e segurando os pushes até o limite resetar.
- **Push ao GitHub** funciona via credencial de arquivo (memória `github-push-acesso`); alterar
  `.github/workflows/` exige o escopo `workflow` no token.

## 10. O que NÃO fazer (resumo — detalhe no `CLAUDE.md`)

- Não editar migration antiga (correção vem em migration nova).
- Não copiar código de `basedosdados/pipelines` (sem licença) nem `parlametria/leggo-backend`
  (AGPL). OK ler como referência de campo/modelagem.
- Não pular a resolução de identidade ("resolver depois"). Dado errado é pior que ausente.
- Prometeus lê **só a camada ouro** (views), nunca a prata; toda resposta cita fonte; recusa
  honesta quando falta dado.
- Não criar arquivos fora da pasta do projeto.
