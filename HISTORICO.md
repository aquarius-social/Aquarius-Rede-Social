# HISTÓRICO — marcos detalhados do Aquarius

Log de marcos com os detalhes finos (números de ingestão, achados §19, débitos
conhecidos). Movido para cá para manter o `ESTADO_ATUAL.md` enxuto (onboarding
barato). Para o estado atual, leia `ESTADO_ATUAL.md`; para a visão completa,
`RELATORIO_DESENVOLVIMENTO.md`; para o backlog, `MELHORIAS.md`.

> Ordem: mais recente no topo de cada bloco. Datas absolutas.

---

## App (Expo) — camada de leitura, tema, header, seguir (ago/2026)

- **Sistema de "seguir" (2026-08-10): núcleo + consumidores.** Migration
  `0018_follows` (tabela `follows` + RLS por dono) + `lib/follows.tsx`
  (`FollowsProvider`/`useFollows`, estado otimista, migração única de temas/partidos
  antigos). Botão Seguir persistido nas 4 telas de entidade; onboarding grava follows;
  Interesses e Configurações leem follows; Feed "Seguindo" filtra os destaques por quem
  se segue. Verificação de boot ao vivo ficou bloqueada por RAM baixa (Metro OOM) — `tsc` verde.
- **Header custom (AqHeader) (2026-08-10).** `components/header.tsx`, variantes home
  (logo+avatar) e detalhe (voltar+título+avatar), safe-area + tema; header nativo do
  Stack substituído via option `header` (`AqHeaderNav`).
- **Modo escuro (2026-08-10).** Sistema de tema em `lib/theme.tsx` (`TemaProvider` +
  `useTema`/`useTemaEstilos`) + paletas em `lib/tema.ts` (tokens semânticos `texto`/`cartao`
  resolvem a sobrecarga de `navy`/`white`). 15 telas + `base.tsx` migradas; toggle em
  Configurações (persiste em AsyncStorage). Verificado em runtime (Expo web).
- **Fidelidade ao protótipo (2026-08-10).** Auditoria das 15 telas; correções de
  texto/rótulo aplicadas; gaps que dependem de feature/dado documentados em `MELHORIAS.md` F.1.

## Deploy real + base de dinheiro público (2026-08-04)

- Supabase **provisionado** (projeto `nqebfmyzchpkufsytvyf`), migrations 0001–0012
  aplicadas, ingestão rodando **de verdade** contra o Postgres gerenciado (adaptador
  concreto em produção, não fake).
- **Backfill de despesas/CEAP 2023–2026 (57ª legislatura):** **708.170 lançamentos**,
  **732 deputados**, banco em 441 MB. Idempotente (chave `perfil_id,cod_documento,parcela`).
  A cauda decrescente de 2026 reflete a defasagem de reembolso da CEAP, não corte de rede.
- **Estratégia caminho B (Free enxuto, dinheiro primeiro):** flags de área em
  `run_backfill.py` desligam áreas pesadas; a rodada de dinheiro roda só deputados +
  despesas. Bronze (JSON cru) era o maior peso — o app lê do OURO, então `AQUARIUS_BRONZE=0`
  corta storage sem perder produto.
- **Emendas 2023–2026 (Área F):** **19.444 emendas**; autor resolvido pela curadoria §6.3
  (~88% com autor). Custo ~5 MB/ano. Exige a chave `AQUARIUS_TRANSPARENCIA_KEY`.
- **Despesas Senado / CEAPS 2023–2026:** **73.459 lançamentos**; estreou os 245 perfis de
  senador. Débito: senador 5718 com vínculos sobrepostos na fonte (1 linha recusada §4).
- **Combo bicameral completo:** CEAP Câmara (708.170) + Senado (73.459) + emendas
  federais (19.444). Free praticamente no teto: **476 MB de 500 (95%)** — a próxima
  expansão (legislativo, bronze, discursos, convênios) é território do **Pro** (8 GB).
- **Persistência endurecida** (`supabase_adapter.py` + `repositorio.py`): upsert em lote
  (`LOTE_UPSERT=500`) + retry só de erros de conexão + dedup-antes-do-lote (o HTTP/2 do
  supabase-py encerra a conexão após ~20k streams). Checkpoint por ano.
- ⚠️ **Pendência de segurança:** a service/secret key circulou no chat durante os testes
  e **precisa ser rotacionada** (Supabase → Settings → API Keys → revoke + gerar nova).
  Não quebra o app (usa a `anon`). **Ver ESTADO_ATUAL → Ações pendentes.**

## App (Expo) — primeiro vertical: perfil parlamentar (2026-08-04)

- Scaffold Expo Router lendo a camada OURO pela chave **anon** (RLS), nunca a service key.
  `tsc` limpo, bundle Metro (web) compila.
- Perfil parlamentar completo e fiel ao Claude Design: cover com onda, avatar-gradiente,
  chips, faixa de stats, 9 abas. Dado REAL em Despesas e Emendas; demais abas com
  dado-exemplo rotulado "não ingerido".
- Tela de Partido (bancada + dinheiro): dado real em Membros e Emendas (agregado dos
  membros via um `IN`, somado no cliente). Débito: `lib/tema.ts` é cópia dos tokens de
  `packages/ui` (trocar por `@aquarius/ui` quando o monorepo Metro for ligado).

## Vínculo Câmara + situação do parlamentar (2026-08-05/06)

- Histórico de mandatos da Câmara ingerido (leg 57): 2.253 vínculos / ~567 deputados.
- View `parlamentar_publico` (0013): projeta `situacao`, não esconde titular licenciado,
  current-ness pelo vínculo vigente (caiu de 1.352 para 581 do parlamento atual).
- **§6.4 (licenciado × suplente):** view mostra **623 atuais** (573 em exercício, 25
  licenciados, 25 suplentes). Senado (0014): suplente com período real + `titular_profile_id`
  + causa. Câmara (0015/0016): corrigido `situacao="Licença"`; Câmara não expõe o link
  titular↔suplente (é dado TSE) → suplente aparece sem "no lugar de X". Pendente: link TSE.

## Convênios / transferências — o objeto das emendas (PLANEJADO, não iniciado)

- **Problema:** a API de emendas descreve por função/subfunção/localidade + estágios — sem
  "objeto/beneficiário". O objeto real mora em **convênios** e **transferências** vinculados
  à emenda (Portal da Transparência, mesma chave `chave-api-dados`).
- **Plano:** (1) verificar campos ao vivo; (2) migration `00NN_convenios.sql` (tabela +
  view ouro sem PII); (3) coletor(es) em `transparencia/` no pipeline bronze→prata→ouro;
  (4) resolver o vínculo emenda→convênio→beneficiário (bicameral por natureza); (5) seção
  "Objeto/Beneficiário" no detalhe da emenda.
- **Considerações:** volume ALTO → quase certo que exige **Supabase Pro**. Onda própria,
  prioridade alta (fecha "para onde foi o dinheiro"), depois de Free→Pro.

## Onda 1 — ingestão (Câmara + Senado bicameral): coletores prontos

Todas as áreas abaixo têm **coletor pronto e testado**; muitas estão **truncadas do banco**
(por espaço no Free), não faltando código. Detalhe completo em `ONDA-1-LEIA-ME.md`.

- **Câmara — 5/9 áreas:** proposições (27 testes), votações + votos nominais (reformadas
  V1–V4 §10/§5.2; placar do texto reconciliado com nominais), deputados (dedup §12 +
  enriquecimento §5.3), tramitações (sequência monotônica por data §5.2), despesas/CEAP
  (identidade `documento − glosa = líquido`; negativo = estorno legítimo).
- **Identidade:** histórico de mandatos → `vinculo_temporal` (vigências não sobrepostas
  §4/§12); partidos canônicos (22 atuais; siglas históricas/fusões = curadoria pendente);
  perfis coletivos comissão + frente.
- **Senado (paridade bicameral):** senadores + junção bicameral (§17, roster completo 245,
  não só 81 em exercício; convergência nome+nascimento+naturalidade sem filtro de mandato);
  matérias/proposições; tramitações (endpoint `/processo` — o antigo foi descontinuado, §19);
  votações (`/votacao`, votos nominais inline — 888 resolvidos em dez/2024); comissões +
  **blocos** (bloco estreou); mandato histórico (partido por período, corrige o bug "partido
  no presente" §4); despesas/CEAPS (CSV anual ISO-8859-1; nome de arquivo recuperado do
  Internet Archive; resolvido por nome); curadoria autor de emenda (Câmara 580/628 + Senado 5).
- **Discursos (bicameral):** coletores Câmara + Senado; tabela `discurso` (0011) serve as
  duas casas; guarda resumo + `tem_transcricao` + URL (não copia a transcrição integral).
- **Eventos/agenda (bicameral, área nova):** coletores Câmara + Senado; tabela `evento`
  (0012) + view `evento_publico`; o Calendário do app consome. Nasceu bicameral.
- **Pipeline & persistência:** repositório com porta injetável `ClienteBanco`; adaptador
  Supabase concreto; orquestrador na ordem de FKs (deputados → lookup → proposições →
  votações → votos). Migration 0004: placar nulável (não fabrica 0).

## Onda 0 — Fundação de identidade (concluída)

Resolvedor de identidade em dois tempos (§5.3); `profiles`/`id_externo`/`vinculo_temporal`/
`partido`; `packages/types` e `packages/ui`. Quatro invariantes como constraint no banco.
Detalhe em `ONDA-0-LEIA-ME.md`.

## Infra pronta (com pendências de deploy)

- **CI + agendador:** `.github/workflows/ci.yml` (testes + type-check dos pacotes TS a cada
  push) + `ingestao.yml` (agenda `run_ingestao.py` 2×/dia, pula com verde sem os secrets).
- **Camada ouro:** views servidas (0006/0007) com proveniência/frescor, `grant select` a
  anon/authenticated, **sem PII** (§3.5 — a view é a fronteira).
- **Pendências de deploy:** rotacionar a service key vazada; pôr `SUPABASE_URL/SERVICE_KEY`
  nos secrets do repo (liga o agendador); loader de `.env` (parar de colar chave à mão).
