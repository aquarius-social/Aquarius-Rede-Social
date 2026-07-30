# Estado atual do Aquarius

Documento vivo. **Atualizar a cada onda concluída.** Se você (Claude Code
ou humano) está lendo isto agora, este é o segundo arquivo a ler, depois
do `CLAUDE.md`.

## Onde estamos

**Onda 0 — Fundação de identidade: concluída.**

**Onda 1 — Ingestão da Câmara: em progresso.**
- Proposições: coletor pronto, 27 testes. Campos conferidos contra a API viva
  (2026-07-29) — sem divergência.
- Votações + votos nominais: coletor **reformado (V1–V4 concluídos)** conforme a
  Metodologia §10/§5.2 (ver `ANALISE-Metodologia-vs-Codigo.md`). Placar extraído
  do texto da descrição (plenário + comissão) e reconciliado contra os nominais.
  Parser validado contra amostras vivas. Não trava mais em QUEBRA.
- Deputados: **coletor com enriquecimento pronto** — lista por legislatura,
  dedup por id (§12), perfil + `id_externo`, e enriquecimento por detalhe
  (nome civil, nascimento, naturalidade — sinais §5.3). Validado ao vivo:
  1.073 linhas → 613 pessoas (leg. 56); PII do detalhe confirmada e
  `ultimoStatus` temporal ignorado.
- Histórico de mandatos → `vinculo_temporal`: **pronto** — `camara/mandatos.py`
  converte os snapshots do histórico em vigências não sobrepostas (partido/UF/
  ocupação por período, §4/§12 D4). Validado ao vivo (Danilo Forte: 23
  snapshots → 10 vínculos; 1 suplente à quarentena aguardando o titular, §6.4).
  Migration 0005 dá o alvo de upsert idempotente.
- Partidos canônicos: **pronto** — `camara/partidos.py` ingere os partidos
  atuais (profile tipo=partido + `partido`); o vínculo resolve `partido_id` por
  sigla. Validado ao vivo: 22 partidos atuais; das siglas do Danilo Forte,
  PSB/PSDB/UNIÃO/PP resolvem, PMDB/DEM/S.PART. ficam null (siglas históricas e
  linhagem de fusões = curadoria, §4 — etapa própria). Comissões (§12 D5): falta.
- Tramitações: **coletor pronto** — `camara/tramitacoes.py`, por proposição,
  com a identidade §5.2 de sequência monotônica (por data de calendário — a
  fonte viva mostrou tramitações com hora `00:00`, e comparar por instante
  gritava à toa) e a ressalva bicameral da §11 (`casa` explícito). Persistido
  e wireado no orquestrador. Validado ao vivo (PL 736/2015, 64 tramitações).
- Repositório (persistência em Supabase): **lógica pronta e testada** —
  `persistencia/repositorio.py` com porta injetável `ClienteBanco`, upsert de
  bronze/profiles/id_externo/proposicao/votacao/voto_nominal, resolução de FKs e
  o **lookup real de `id_externo`** (o que era injetado nos coletores). Migration
  **0004** torna o placar nulável (não fabrica 0). Falta só o **adaptador
  concreto Supabase** (pacote `supabase` não instalado neste ambiente; wireado
  no deploy — ver docstring do repositório).
- Orquestrador: **pronto e testado** — `orquestracao/orquestrador.py` roda uma
  ingestão completa na ordem de FKs (deputados → lookup real → proposições →
  votações → votos), HTTP e banco injetados. Teste de integração prova a
  resolução de votos ponta a ponta (e, pela negativa, que sem deputados os
  votos não resolvem).

Passos 1 (testes verdes) e 2 (conferência contra API viva) do plano abaixo:
**concluídos** em 2026-07-29. Base era **72 testes**; `tsc` de `types` e `ui`
sem erros (após `npm install` por pacote — não há workspace na raiz).

Nota de ambiente: o interpretador aqui é **`py`**, não `python` (este é o alias
fantasma da Microsoft Store).

## O que fazer agora, na ordem

### 1. Verificar que tudo compila e testa

```
cd codigo/services/ingestao
python -m unittest discover -s . -t .
```

Deve dar `Ran 72 tests` e `OK`. Se algum falhar, é o primeiro problema
a resolver, não seguir em frente.

```
cd codigo/packages/types  &&  npx tsc --noEmit
cd codigo/packages/ui     &&  npx tsc --noEmit
```

Ambos devem sair sem erros.

### 2. Confirmar os `[verificar]` contra a API real

O código tem marcadores explícitos onde os nomes de campo vieram de
documentação e não de conferência ao vivo — a sessão anterior não tinha
rede para APIs governamentais. Rodar (uma vez, sob supervisão humana):

```
curl -sS 'https://dadosabertos.camara.leg.br/api/v2/proposicoes?itens=1' > /tmp/prop.json
curl -sS 'https://dadosabertos.camara.leg.br/api/v2/votacoes?itens=1'    > /tmp/vot.json
curl -sS 'https://dadosabertos.camara.leg.br/api/v2/deputados?itens=1'   > /tmp/dep.json
```

Comparar cada campo com o que está em `codigo/services/ingestao/camara/*.py`
e com as constantes `CAMPOS_CRITICOS_*`. Discrepância é QUEBRA no
vocabulário do canário — deve ser endereçada, não silenciada.

Nota: a Base dos Dados (`github.com/basedosdados/pipelines`) usa CSVs
anuais em vez da API JSON. Nomes de campo em geral batem entre os dois,
mas o CSV achata aninhados com underscore (ex: `ultimoStatus.despacho`
vira `ultimoStatus_despacho`). A API JSON preserva o aninhamento.

### 3. Próximo entregável — REFORMA do coletor de votações (Rota A)

Detalhado em `ANALISE-Metodologia-vs-Codigo.md` (itens V1–V4). Estado:
- **V1 ✅** — busca o **detalhe** da votação e lê `proposicoesAfetadas`;
  `proposicoes_` saiu dos campos críticos; a lista mantém o contrato barato.
- **V2 ✅** — corrobora a matéria pelo id da votação, que começa pelo id da
  proposição (escolhe a afetada certa quando há várias).
- **V3 ✅** — **Artigo 17 = quem presidiu**: vai a `ResultadoVotos.presidencia`,
  fora do placar e do enum de posição (conflito resolvido a favor da §10).
- **V4 ✅** — placar extraído do texto da `descricao`: formato de plenário
  (`Sim: N; não: N; abstenção: N; total: N`) e três sub-formatos de comissão
  (rótulo+`Total de Votantes`, `N votos "X"`, tipo único). Descrição narrativa
  sem número → placar `None` (nunca zero). Identidade aritmética no portão
  (posições somam o total) e reconciliação contra os nominais na rodada
  (soma dos individuais == placar; votantes ≤ 513). Parser validado contra
  amostras vivas de plenário e comissão.
  - Ressalva honesta: cobre os formatos amostrados; frase de comissão nova e
    não vista tende a devolver placar parcial ou `None` — degradação honesta,
    não invenção. "Quórum" NÃO é lido como total (conservador).

Base de testes: **164 passando** (72 → … → 137 bronze de votos → 154 histórico/
`vinculo_temporal` → 164 partidos canônicos; +92 no total), todos sem rede.

### 3b. Coletor de deputados — primeiro passe ✅

Entregue em `codigo/services/ingestao/camara/deputados.py` (§12, D1/D3/D6):
- `coletar_bronze_deputados` (`GET /deputados` por legislatura, paginado).
- `deduplicar_por_id` — a disciplina central: a lista repete o id por filiação;
  dedup precede qualquer contagem de pessoas.
- `transformar_deputado` → perfil (`profiles`, identidade estável) + vínculo
  (`id_externo`, sistema='camara', método='fonte_direta', grau='direto').
- UF/partido de mandato NÃO viram atributo do perfil — vão em `mandato_hint`
  para o passo de `vinculo_temporal` (D3).
- **Enriquecimento por detalhe** (`GET /deputados/{id}`): nome civil,
  nascimento, naturalidade (sinais §5.3, PII interna §3.5). `rodada_deputados`
  busca 1 detalhe por pessoa deduplicada; falha pontual do detalhe não derruba
  a rodada (a pessoa entra sem PII). `ultimoStatus` (temporal) é ignorado.
- Portão + contrato (§19) + `rodada_deputados`.

Falta neste coletor (etapas próprias, não feitas):
- Histórico de transições e `vinculo_temporal` (§12, D2/D4): fonte instável,
  em lote com retry, persistida, nunca ao vivo.
- Comissões (§12, D5).

### 4. Depois do orquestrador

- **Adaptador Supabase concreto** — implementar os 3 métodos de `ClienteBanco`
  sobre o cliente Supabase (service role) quando o pacote/creds existirem no
  deploy. Aplicar migrations 0001–0004. É o único elo que falta para a ingestão
  rodar de verdade (a lógica toda já está testada com fakes).
- **Linhagem de partidos (§4)** — siglas históricas (PMDB→MDB) e fusões
  (DEM/PSL→UNIÃO) precisam de `partido_sigla_historico` + `partido_linhagem`
  por curadoria; sem fonte de curadoria, o `partido_id` de períodos antigos
  fica null (a sigla-fonte é preservada).
- **Resolver o titular do suplente** (§6.4) — hoje períodos de suplente em
  exercício vão à quarentena; a cadeira precisa de cross-referência.
- **Comissões** dos deputados (§12 D5).
- **Persistir a presidência** (Artigo 17, §10): hoje computada em
  `ResultadoVotos.presidencia`, sem coluna/tabela alvo.

## O que NÃO fazer

- **Não usar `pytest`** sem checar se está instalado; os testes rodam sob
  `unittest` sem dependência externa. Manter assim.
- **Não copiar código de `basedosdados/pipelines`** — sem licença explícita
  = todos os direitos reservados. OK usar como referência para nomes de
  campo (fato factual sobre API pública, não copyrightável).
- **Não copiar código de `parlametria/leggo-backend`** — AGPL-3.0
  contaminaria o Aquarius inteiro. OK ler como referência de modelagem.
- **Não pular a resolução de identidade** para "resolver depois". O
  princípio da Metodologia é: dado errado é pior que dado ausente.
- **Não editar migration antiga.** Novas correções vêm em migration nova
  (padrão que 0003 estabeleceu).
- **Não criar arquivos fora da pasta Aquarius Rede Social.** Tudo (código,
  docs, testes) vive dentro dela, na estrutura descrita no `CLAUDE.md`.

## Documentos de referência (nesta pasta)

- `CLAUDE.md` — instruções permanentes para o Claude Code (regras
  anti-alucinação, hierarquia de fontes, mapa desta pasta).
- `PLANO.md` — auditoria do plano original e plano em 12 fases.
- `ONDA-0-LEIA-ME.md` — o que foi feito na fundação.
- `ONDA-1-LEIA-ME.md` — o que foi feito na ingestão até aqui.
- `Aquarius_Metodologia_de_Dados.docx` — a Metodologia (fonte de tudo
  sobre dados). Formato Word — abrir para consultar.
- `Aquarius_Concepcao_do_Produto.docx` — a Concepção (fonte de intenção
  de produto).
- `PRD_Aquarius_redesocial/*.md` — PRDs originais (mai/26).
- `Aquarius Rede Social.zip` — protótipo navegável (não portar código;
  ler como referência de UX).
