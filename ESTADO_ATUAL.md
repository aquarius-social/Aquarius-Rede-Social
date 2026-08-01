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
  linhagem de fusões = curadoria, §4 — etapa própria).
- Perfis coletivos (comissão + frente): **prontos** — `camara/coletivos.py`
  popula os tipos `comissao` (comissões permanentes, `/orgaos?codTipoOrgao=2`) e
  `frente` (`/frentes`) da tabela polimórfica `profiles`. Views ouro na 0007.
  Validado ao vivo: 30 comissões permanentes, 100+ frentes. **4 dos 6 tipos de
  perfil populados** (parlamentar, partido, comissão, frente); faltam bloco/órgão.
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
- Senado — senadores + junção bicameral (Área I, §17): **coletor pronto** —
  `senado/senadores.py`, fonte **Dados Abertos do Senado** (JSON via header
  `Accept`), lista (`/senador/lista/atual`) + enriquecimento por detalhe
  (`/senador/{cod}` → nascimento/naturalidade, sinais §5.3). Verificado ao vivo
  (2026-07-31): 81 senadores em exercício, contrato OK. Senadores entram na
  MESMA tabela polimórfica `profiles` (a fundação já previa as duas casas).
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

Deve dar `Ran 253 tests` e `OK`. Se algum falhar, é o primeiro problema
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

Base de testes: **253 passando** (+17 dos discursos bicamerais: coletores da
Câmara e do Senado, portão, rodada com vazio-legítimo, persistência que resolve
o autor pelas duas casas, e a prova ponta a ponta no orquestrador), sem rede.

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
- **Deploy / infra operacional** — o que falta para a base ficar viva:
  1. provisionar o projeto Supabase + aplicar migrations 0001–0007;
  2. pôr `SUPABASE_URL`/`SUPABASE_SERVICE_KEY` nos secrets do repo (aí o
     agendador começa a rodar sozinho, 2×/dia).
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
