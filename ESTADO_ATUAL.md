# Estado atual do Aquarius

Documento vivo. **Atualizar a cada onda concluída.** Se você (Claude Code
ou humano) está lendo isto agora, este é o segundo arquivo a ler, depois
do `CLAUDE.md`.

## Onde estamos

**Onda 0 — Fundação de identidade: concluída.**

**Deploy real + base de dinheiro público: concluído (2026-08-04).**
- Supabase **provisionado** (projeto `nqebfmyzchpkufsytvyf`), migrations 0001–0012
  aplicadas, ingestão rodando **de verdade** contra o Postgres gerenciado (não é
  mais só fake/duble — o adaptador concreto está em produção).
- **Backfill de despesas/CEAP 2023–2026 (57ª legislatura) concluído** — **708.170
  lançamentos** de cota parlamentar, **732 deputados** (titulares + suplentes que
  assumiram), banco em **441 MB**. 2026 completo até a disponibilidade da fonte
  (meses 1–7 + início do 8); a cauda decrescente reflete a **defasagem de reembolso
  da CEAP** (o deputado protocola semanas depois), não corte de rede. Idempotente:
  a tabela guarda a união de todos os runs, sem duplicar (chave
  `perfil_id,cod_documento,parcela`).
- **Estratégia caminho B (Free enxuto, dinheiro primeiro):** o Free do Supabase
  (500 MB) obriga base enxuta. **Flags de área** em `run_backfill.py`
  (`AQUARIUS_BRONZE/PROPOSICOES/VOTACOES/DISCURSOS/EVENTOS/SENADO/HISTORICO/
  ENRIQUECER`, padrão LIGADO) desligam as áreas pesadas; a rodada de dinheiro roda
  só deputados + despesas. **Bronze (JSON cru) era o maior peso** — o app lê da
  camada OURO, não do bronze, então `AQUARIUS_BRONZE=0` corta storage sem perder
  o produto.
- **Backfill de emendas parlamentares 2023–2026 (Área F, Portal da Transparência)
  concluído** — **19.444 emendas** (empenhado/liquidado/pago + restos). Autor
  resolvido pela curadoria §6.3: 328 autores distintos em 2023, ~557–578 em
  2024–2026 (a resolução menor de 2023 é honesta — o mapa curado é da composição
  de 2025; autores fora dele ficam `null`, degradação declarada, não erro).
  Custou só ~5 MB/ano — emenda é fração do tamanho da despesa. Exige a chave
  pessoal `AQUARIUS_TRANSPARENCIA_KEY` (agora cadastrada).
- **Combo de dinheiro público completo:** despesas/CEAP (708.170 lançamentos) +
  emendas (19.444) — as duas frentes de "dinheiro público", o maior gap de
  mercado, agora vivas no banco. Base enxuta (bronze/legislativo off) cabe no Free.
- **Folga:** o combo fechou sob **~455 MB** de 500 (as emendas somaram só ~9 MB
  aos 446 já medidos). O Pro (8 GB) fica reservado para quando o volume de
  usuários/áreas pedir — não é gargalo agora.
- **Persistência endurecida** (`supabase_adapter.py` + `repositorio.py`): upsert
  **em lote** (`LOTE_UPSERT=500`) + **retry** só de erros de conexão (com backoff)
  + **dedup-antes-do-lote**. Motivo real: o HTTP/2 do supabase-py encerra a conexão
  após ~20k streams — o upsert linha-a-linha esgotava (`ConnectionTerminated`). O
  Postgres também recusa afetar a mesma chave de conflito 2× no mesmo lote → dedup
  obrigatória. run_backfill tem **checkpoint por ano** (Ctrl+C e rerodar continua).
- ⚠️ **Pendência de segurança:** a service/secret key circulou no chat durante os
  testes e **precisa ser rotacionada** (Supabase → Settings → API Keys → revoke +
  gerar nova). Não quebra o app (usa a `anon`).

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
  linhagem de fusões = curadoria, §4 — etapa própria).
- Perfis coletivos (comissão + frente): **prontos** — `camara/coletivos.py`
  popula os tipos `comissao` (comissões permanentes, `/orgaos?codTipoOrgao=2`) e
  `frente` (`/frentes`) da tabela polimórfica `profiles`. Views ouro na 0007.
  Validado ao vivo: 30 comissões permanentes, 100+ frentes. (Bloco entrou depois,
  pelo Senado — ver abaixo; **5 dos 6 tipos de perfil populados**, falta só órgão.)
- Tramitações: **coletor pronto** — `camara/tramitacoes.py`, por proposição,
  com a identidade §5.2 de sequência monotônica (por data de calendário — a
  fonte viva mostrou tramitações com hora `00:00`, e comparar por instante
  gritava à toa) e a ressalva bicameral da §11 (`casa` explícito). Persistido
  e wireado no orquestrador. Validado ao vivo (PL 736/2015, 64 tramitações).
- Despesas / CEAP (Área A, §8): **coletor pronto** — `camara/despesas.py`, por
  parlamentar/ano, com a identidade §5.2 (`documento − glosa = líquido`) no
  portão. Tabela `despesa` + view ouro (0008). Achado ao vivo: valor negativo é
  **estorno legítimo** (satisfaz a identidade) — a regra "não-negativo" era
  falso-positivo e foi removida (100 aprovados/0 quarentena após o fix). **5 de
  9 áreas de dado da Câmara prontas.**
- Emendas parlamentares / execução orçamentária (Área F, §13): **coletor pronto**
  — `transparencia/emendas.py`, fonte **Portal da Transparência** (não a Câmara),
  por exercício, paginado. Identidade de ordem §5.2 no portão (empenhado ≥
  liquidado ≥ pago; restos pago+cancelado ≤ inscrito — estágios NUNCA se somam).
  Valores em formato BR (`10.000,00`) parseados; autor extraído do `codigoEmenda`
  (§6.3) como `autor_codigo`, resolvido ao perfil por `id_externo`
  `autor_orcamentario` quando o mapa de autores existe (curadoria própria — a
  resolução fica `null` sem o mapa, degradação honesta). Tabela `emenda` + view
  ouro `emenda_publica` (0009). Campos conferidos contra o dado real
  (`emendas_2024.json`, 6990 registros). **EXIGE** a chave pessoal
  `chave-api-dados` (env `AQUARIUS_TRANSPARENCIA_KEY`); sem ela a área é pulada.
  Primeira área fora da Câmara.
- Curadoria: autor de emenda → perfil (§6.3): **pronto** — `transparencia/autores.py`
  + `salvar_autores_orcamentarios`. Materializa o mapa curado
  (`dados/mapa_autores_emendas_2025.csv`, 628 autores) como `id_externo`
  (sistema='autor_orcamentario') ANTES das emendas, para que `salvar_emendas`
  resolva `autor_profile_id`. **Dois braços (§17):** Câmara (`deputado_id` →
  perfil, **580/628 = 92%**) e Senado (nome → senador, os que o mapa não achou por
  só tentar a Câmara). Grau pelo nº de sinais (§5.3): 2+ → 'direto'; 1 →
  'com_ressalva' + pendente. Bancadas estaduais/comissões (36) ficam sem perfil
  (não há tipo 'bancada'; honesto). **Braço Senado — resolvido:** com o roster
  completo da legislatura (ver bullet de senadores), os autores-senadores
  licenciados (AUGUSTA BRITO, FERNANDO FARIAS, JORGE SEIF, MECIAS DE JESUS,
  RODRIGO CUNHA) passaram a casar — **0 → 5**. Verificado ao vivo (2026-08-02):
  mapa carrega 628, braço Câmara 580 + braço Senado 5 resolvíveis.
- Senado — senadores + junção bicameral (Área I, §17): **coletor pronto** —
  `senado/senadores.py`, fonte **Dados Abertos do Senado** (JSON via header
  `Accept`), lista (`/senador/lista/atual`) + enriquecimento por detalhe
  (`/senador/{cod}` → nascimento/naturalidade, sinais §5.3). Senadores entram na
  MESMA tabela polimórfica `profiles` (a fundação já previa as duas casas).
  **Roster COMPLETO da legislatura** (`rodada_senadores(legislatura=57)`, raiz
  `ListaParlamentarLegislatura`): ingere titulares + suplentes (**245**, não só os
  **81** em exercício), com `ativo` marcado pela lista em-exercício. Isso FECHA a
  lacuna §6.4 — os senadores licenciados/suplentes que aparecem em CEAPS e emendas
  mas não estão sentados hoje. Verificado ao vivo (2026-08-02): 245 perfis (81
  ativos + 164 inativos); CEAPS passou a resolver **87/88** nomes (era 73) e o
  braço Senado da curadoria de emendas **0 → 5** autores.
  **Junção bicameral (§17):** `resolucao/bicameral.py` reusa o núcleo de
  convergência do resolvedor (nome civil + nascimento + naturalidade, §5.3) SEM
  o filtro de mandato vigente — o deputado que virou senador nunca sobrepõe no
  tempo. `salvar_senadores` decide: 2+ sinais → é a mesma pessoa, anexa o
  `id_externo(senado)` ao perfil do deputado (metodo='convergencia', SEM perfil
  novo); 1 sinal só → perfil próprio + `pendente_conferencia` (§13, ambíguo não
  auto-funde). Migration 0010 torna a view `parlamentar_publico` bicameral
  (partido/UF/`casa_atual` para senadores). Fonte pública, sem chave. Prova de
  ponta a ponta no teste do orquestrador (senador 900 = deputada Ana → vincula).
- Discursos — **bicameral** (Área G, §13): **coletores prontos** para as DUAS
  casas. `camara/discursos.py` (`/deputados/{id}/discursos`, id composto
  deputado:dataHoraInicio, como o voto) e `senado/discursos.py`
  (`/senador/{cod}/discursos`, `CodigoPronunciamento`, janela `YYYYMMDD`).
  Produzem a MESMA prata; a tabela `discurso` (0011) serve as duas casas
  (coluna `casa`) + view ouro `discurso_publico` SEM PII, citando `url_texto` da
  fonte. `salvar_discursos` resolve o autor por `id_externo` (camara/senado)
  antes de gravar — sem perfil, pula (§6). A transcrição integral NÃO é copiada:
  guarda-se resumo + flag `tem_transcricao` + URL. Verificado ao vivo
  (2026-07-31): deputado 74784 = 4 discursos, senador 5672 = 19 pronunciamentos.
  Prova ponta a ponta no orquestrador (discurso da Câmara + do Senado na mesma
  tabela; o do senador resolve ao perfil unificado da §17). **Primeira área
  construída bicameral desde o início** (decisão de paridade Câmara↔Senado).
- Matérias do Senado — proposições (Área B, bicameral): **coletor pronto** —
  `senado/materias.py`, fonte `/materia/pesquisa/lista` com janela de
  apresentação (`dataInicioApresentacao/Fim`, YYYYMMDD), uma consulta por sigla
  suportada (PL/PEC/PLP/PDL). Produz a MESMA prata da Câmara
  (`casa_origem='senado'`) e reusa `salvar_proposicoes` — **sem migration nova**,
  a tabela `proposicao` já era bicameral (0002, §17). Tipos procedurais do Senado
  (RQS, MSF) ficam de fora (ampliar o enum é decisão de escopo, não técnica).
  Verificado ao vivo (2026-07-31): 85 matérias PL/PLP/PDL em jun/2024, 0
  quarentena. Início da onda de PARIDADE do Senado (fechar o que só a Câmara
  tinha antes de partir para áreas novas).
- Tramitações do Senado (Área D, bicameral): **coletor pronto** —
  `senado/tramitacoes.py`. **Achado §19:** o endpoint antigo
  `/materia/movimentacoes` foi DESCONTINUADO (desativação 2026-02-01); a própria
  fonte aponta `/processo/{idProcesso}` como substituto — usamos o substituto,
  não o endpoint morto. O `idProcesso` (≠ código da matéria) vem da pesquisa de
  matérias e viaja na prata como `id_processo`. A tramitação é
  `autuacoes[].informesLegislativos` (eventos datados com colegiado/descrição).
  Sem número de sequência na fonte → ordena por `id` (ordem de criação) e atribui
  1..N; a checagem §5.2 de monotonicidade (reusada da Câmara) confere que a data
  não retrocede nessa ordem — teste REAL. Mesma prata da Câmara
  (`casa='senado'`) → reusa `salvar_tramitacoes`, **sem migration**. Verificado
  ao vivo (2026-08-01): PL 1/2024 = 19 tramitações, 0 violações.
- Votações + votos nominais do Senado (Área C, §10/§5.2, bicameral): **coletor
  pronto** — `senado/votacoes.py`. **Achado §19:** `/materia/votacoes` também
  descontinuado; substituto é `/votacao?dataInicio&dataFim`. Bem mais limpo que a
  Câmara: placar (`totalVotosSim/Nao/Abstencao`) e votos nominais (`votos[]`) vêm
  INLINE e estruturados — sem parse de texto (a reforma V1–V4 da Câmara foi por
  isso). Mapeia a sigla de voto do Senado → enum `voto_tipo` (Sim/Não/Abstenção +
  ausências AP/LS/NCom/MIS/P-NRV→ausente). §10: voto secreto (`votacaoSecreta='S'`
  → siglas 'Votou') grava `secreta=true` e NENHUM nominal. §5.2: contagem dos
  nominais reconciliada contra o placar oficial. Resolve o senador pelo mesmo
  lookup `id_externo(senado)`. Mesmas tabelas da Câmara (`casa='senado'`) → reusa
  `salvar_votacoes`/`salvar_votos_nominais`, **sem migration**. Verificado ao vivo
  (2026-08-01): dez/2024 = 27 votações (15 secretas), **888 votos nominais
  resolvidos**, 0 divergências §5.2. Fecha o cruzamento "como cada senador votou".
- Comissões + blocos do Senado (perfis coletivos, bicameral): **coletor pronto** —
  `senado/coletivos.py`. Comissões via `/comissao/lista/colegiados` (301 → JSON
  estático, urllib segue), filtrando ao que É comissão
  (`DescricaoTipoColegiado` começa com "Comiss") — o resto (frentes, grupos, mesa)
  é escopo próprio. Blocos via `/composicao/lista/blocos`. Popula os tipos
  `comissao` e **`bloco`** da tabela polimórfica `profiles` — o **bloco estreia**
  (era o 5º dos 6 tipos). Slug leva `-sf` para não colidir com comissões homônimas
  da Câmara (CCJ existe nas duas casas). Reusa `salvar_perfis_coletivos`, **sem
  migration** (enum já tinha `bloco`/`comissao`). Verificado ao vivo (2026-08-01):
  58 comissões, 6 blocos.
- Mandato histórico do Senado → `vinculo_temporal` (§4/§17): **coletor pronto** —
  `senado/mandatos.py`, `/senador/{cod}/mandatos`. **Corrige um bug de correção:**
  o coletor de senadores gravava o partido ATUAL sobre o mandato inteiro (o modo
  de falha §4 "atributo no presente"); agora cada `Mandato` traz `Partidos` com
  `DataFiliacao/DataDesfiliacao`, e a legislatura é cruzada com os períodos
  partidários (clipados à janela do mandato) em vigências NÃO sobrepostas. O
  vínculo coarse saiu de `salvar_senadores` (que voltou a só perfil + id_externo,
  como a Câmara); `salvar_vinculos_temporais` ficou bicameral (resolve o perfil
  por `lookup(casa, id_fonte)`). Verificado ao vivo (2026-08-01): Alan Rick =
  UNIÃO (2023-02-01→2025-11-10) + REPUBLICANOS (2025-11-12→2031-01-31), sem
  sobreposição. **Fecha a paridade de dados legislativos Câmara↔Senado.**
- Despesas do Senado / CEAPS (Área A, §8, bicameral): **coletor pronto** —
  `senado/despesas.py`. A fonte NÃO está na API JSON; é um **CSV anual**
  (`.../transparencia/LAI/verba/despesa_ceaps_{ano}.csv`, ISO-8859-1, `;`). O
  nome de arquivo correto (`despesa_ceaps_{ano}`, não `{ano}`) foi recuperado de
  snapshots recentes do **Internet Archive** — o serviço JSON dedicado
  (`adm.senado.gov.br`) estava em manutenção (503), mas o CSV oficial sempre
  esteve vivo. Fetcher PRÓPRIO (Latin-1, `Accept: */*` — `text/csv` dá 406),
  injetável. Parse com `csv.reader` sobre o texto inteiro (trata quebras dentro
  de aspas). Senador resolvido por **NOME** (a fonte não traz código): mapa nome
  parlamentar normalizado → perfil. Sem glosa (valor reembolsado = líquido);
  `parcela=0` torna a unique key `(perfil,cod_documento,parcela)` efetiva. Mesma
  tabela `despesa` da Câmara → reusa via `salvar_despesas_senado`, **sem
  migration**. Verificado ao vivo (2026-08-01): **2024 = 21.431 lançamentos,
  R\$ 32,2 mi, 0 quarentena; 73/88 nomes casam com a lista viva** (o resto =
  ex-senadores/suplentes que gastaram no ano). **Fecha as 6 de 6 áreas da
  paridade Câmara↔Senado.**
- Eventos — agenda legislativa (área NOVA, bicameral): **coletores prontos** para
  as DUAS casas. `camara/eventos.py` (`/eventos?dataInicio&dataFim` — sessões,
  reuniões, audiências) e `senado/eventos.py` (`/comissao/agenda/mes/{YYYYMM}` —
  agenda de reuniões de comissão; achei o endpoint `/comissao/agenda` por ele dar
  400 e não 404). Produzem a MESMA prata; tabela `evento` (0012) serve as duas
  casas (`casa`) + view ouro `evento_publico`. `data_hora` é `timestamp` SEM fuso
  (hora de parede de Brasília; para agenda, converter p/ UTC deslocaria 3h).
  `salvar_eventos` liga `orgao_profile_id` ao perfil da comissão pelo slug
  reconstruído (null p/ plenário/órgão não-ingerido, honesto). Verificado ao vivo
  (2026-08-02): Câmara 8 eventos/semana, Senado 7 reuniões/mês, slug do órgão
  batendo. **Primeira área que nenhuma casa tinha — nasce bicameral.**
- Repositório (persistência em Supabase): **lógica pronta e testada** —
  `persistencia/repositorio.py` com porta injetável `ClienteBanco`, upsert de
  bronze/profiles/id_externo/proposicao/votacao/voto_nominal, resolução de FKs e
  o **lookup real de `id_externo`** (o que era injetado nos coletores). Migration
  **0004** torna o placar nulável (não fabrica 0). Falta só o **adaptador
  concreto Supabase** (pacote `supabase` não instalado neste ambiente).
- Adaptador Supabase concreto: **escrito e testado** —
  `persistencia/supabase_adapter.py` implementa `ClienteBanco` sobre o
  cliente supabase-py (import tardio), provado contra um duble stateful e como
  drop-in do repositório. Cliente HTTP real (`pipeline/http.py`, urllib) e o
  entrypoint `run_ingestao.py` completam o wiring. **Só falta `pip install
  supabase` + credenciais no deploy** — a lógica inteira já roda com fakes.
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
py -m unittest discover -s . -t .
```

Deve dar `Ran 302 tests` e `OK`. Se algum falhar, é o primeiro problema
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

Base de testes: **302 passando** (+17 dos discursos bicamerais: coletores da
Câmara e do Senado, portão, rodada com vazio-legítimo, persistência que resolve
o autor pelas duas casas, a prova ponta a ponta no orquestrador; +2 das flags de
área: fronteiras de `legislatura_do_ano` e a config enxuta que só grava dinheiro
sem bronze/proposição/votação), sem rede.

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

- **CI + agendador diário: prontos** — `.github/workflows/ci.yml` roda os 173
  testes + type-check TS a cada push (fecha o "CI verde" da Onda 0);
  `.github/workflows/ingestao.yml` agenda `run_ingestao.py` 2×/dia (06h/18h BRT)
  + disparo manual, e pula com verde enquanto os secrets Supabase não existirem.
- **Camada ouro: pronta** — migration `0006_camada_ouro.sql` cria as views
  servidas (`parlamentar_publico`, `partido_publico`, `proposicao_publica`,
  `votacao_publica`, `voto_nominal_publico`, `tramitacao_publica`) com
  proveniência/frescor embutidos, `grant select` a anon/authenticated, e **sem
  PII** (§3.5 — a view é a fronteira, já que RLS não corta coluna). É a camada
  que o app/Prometeus leem. Verificado: todas as colunas existem, nenhuma PII
  projetada. (SQL validado no deploy, como as demais migrations.)
- **Deploy / infra operacional** — provisionamento **feito** (projeto Supabase
  vivo, migrations 0001–0012 aplicadas, ingestão local rodando de verdade). O que
  falta para o piloto automático:
  1. **rotacionar a service key** que vazou no chat (ver marco 2026-08-04);
  2. pôr `SUPABASE_URL`/`SUPABASE_SERVICE_KEY` (a nova) nos secrets do repo (aí o
     agendador `.github/workflows/ingestao.yml` roda sozinho, 2×/dia);
  3. resolver o loader de `.env` para o usuário parar de colar chave na mão a cada
     rodada.
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
