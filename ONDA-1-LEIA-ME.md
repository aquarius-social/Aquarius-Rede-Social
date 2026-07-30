# Onda 1 — Ingestão da Câmara

Ingestão da Câmara dos Deputados, ponta a ponta em lógica: proposições,
votações (com votos nominais), deputados (com enriquecimento), persistência e
o orquestrador que amarra tudo na ordem certa. Tudo testado sem rede; os pontos
de contato com a fonte foram, além disso, **verificados contra a API viva**.

> Este documento consolida a Onda 1 inteira. Detalhe de decisões de dados vive
> em `ANALISE-Metodologia-vs-Codigo.md`; o estado corrente e o próximo passo em
> `ESTADO_ATUAL.md`.

```
supabase/migrations/
  0001_identidade.sql          profiles, id_externo, partido, vinculo_temporal
  0002_camadas_civicas.sql     bronze + prata (proposição, votação, tramitação)
  0003_votacao_nominal.sql     distingue nominal de secreta em votacao
  0004_placar_nao_extraido.sql placar da votação nulável (None = não extraído)
  0005_vinculo_upsert.sql      alvo de upsert idempotente do vinculo_temporal
  0006_camada_ouro.sql         views servidas (ouro) — proveniência/frescor, sem PII
  0007_ouro_coletivos.sql      views ouro de comissão e frente
  0008_despesas_ceap.sql       Área A — despesas/CEAP (tabela + view ouro)
services/ingestao/
  pipeline/
    camadas.py       bronze, portão bronze→prata, verificadores reutilizáveis
    coletor.py       HTTP com retry, distingue instabilidade de falha
    http.py          cliente HTTP concreto (urllib) — implementação real de ClienteHttp
    dedup.py         dedup por conteúdo (o instrumento da seção 5.4)
  contrato/
    canario.py       os cinco estados (ok / instabilidade / falha / quebra / alerta)
  camara/
    proposicoes.py   coletor — proposições
    votacoes.py      coletor — votações + votos nominais (reformado, §10/§5.2)
    deputados.py     coletor — perfis parlamentares (dedup §12 + enriquecimento §5.3)
    mandatos.py      coletor — histórico → vinculo_temporal (partido na data, §4/§12)
    partidos.py      coletor — partidos canônicos (profile tipo=partido, §4)
    coletivos.py     coletor — comissões e frentes (profiles tipo=comissao/frente)
    despesas.py      coletor — despesas/CEAP (Área A, §8; identidade §5.2)
    tramitacoes.py   coletor — tramitações (Área D, §11; monotonicidade §5.2)
  persistencia/
    repositorio.py       upsert bronze/prata + lookup real (porta injetável)
    supabase_adapter.py  ClienteBanco concreto sobre supabase-py (import tardio)
  orquestracao/
    orquestrador.py  uma rodada na ordem de FKs, HTTP e banco injetados
  run_ingestao.py    entrypoint de deploy (urllib + Supabase → orquestrador)
  .env.example       variáveis de credencial exigidas no deploy
```

Verificar tudo (o interpretador aqui é `py`, não `python`):

```
cd services/ingestao && py -m unittest discover -s . -t .
```

Resultado atual: **190 testes passando**, todos sem rede.

Áreas de dado da Câmara: **5 de 9** (proposições, votações, tramitações,
parlamentares, despesas/CEAP). Faltam emendas, discursos, eventos e o Senado.

---

## As invariantes que este código sustenta

**Instabilidade não é falha.** 5xx, 429 e timeout retornam com retry
exponencial; 4xx e DNS não. Sem essa distinção, o painel confunde "a fonte
piscou" com "a fonte quebrou". A §19 chama isso de estado próprio.

**Canário validado antes de qualquer OK.** `avaliar` recusa quando o canário da
fonte não foi validado. Fonte nova entra em regime deliberadamente, não por
esquecimento.

**Alerta e quebra são estados distintos.** Campo novo → ALERTA (processa e
sinaliza leitura humana); campo crítico ausente → QUEBRA (suspende a área).
Testado dos dois lados.

**Dedup opera sobre conteúdo, não sobre id.** Duas coletas do mesmo id com
payloads diferentes não são repetição — são o instrumento que detecta edição
retroativa (§5.4). `ResultadoDedup` separa `repetidos` de `alterados`.

**Portão triam, não erra.** Payload corrompido vai à quarentena com o motivo, e
a rodada segue. Leitura literal da §3.1.

---

## Verificação contra a API viva (o que a §2 exige)

A Metodologia é categórica: "toda afirmação sobre a estrutura de uma fonte foi
verificada por consulta à interface real, não inferida de documentação" (§2).
Sessões anteriores escreveram os coletores só da documentação. Nesta onda, os
campos foram conferidos ao vivo (`dadosabertos.camara.leg.br`, 2026-07-29):

- **Proposições:** os 6 campos críticos presentes na lista; `statusProposicao` e
  `uriAutores` no detalhe. Sem divergência.
- **Votações:** confirmou-se a §10 — o campo de matéria na LISTA vem nulo; o
  vínculo correto está no DETALHE (`proposicoesAfetadas`), corroborado pelo id
  da votação que começa pelo id da proposição. Ver reforma abaixo.
- **Votos:** `tipoVoto` e a chave `deputado_` (com underscore final) são reais.
- **Deputados:** confirmou-se a §12 — a lista repete o id por filiação. Na
  legislatura 56, **1.073 linhas para 613 pessoas** (316 ids repetidos). Sem o
  dedup, contaríamos estados de filiação como se fossem pessoas.

A Metodologia foi **corroborada, não contradita**: cada afirmação da §10/§12
reproduziu-se ao vivo.

---

## Reforma do coletor de votações (§10, §5.2)

O coletor de votações vinha da documentação e **travava em QUEBRA** contra a
fonte real. Foi reformado (itens V1–V4 de `ANALISE-Metodologia-vs-Codigo.md`):

- **V1** — busca o DETALHE de cada votação e lê `proposicoesAfetadas`; a lista
  segue para o contrato barato. `proposicoes_` (campo fantasma) saiu dos
  críticos.
- **V2** — corrobora a matéria pelo prefixo do id da votação.
- **V3 — CORREÇÃO de comportamento anterior:** "Artigo 17" **não é** modalidade
  de voto. A §10 mediu que ele marca **quem presidiu** a sessão — excluído do
  placar, nunca posição nem ausência. Uma versão anterior deste código (e a
  versão anterior deste próprio documento) mapeava `Artigo 17 → obstrucao`, o
  que contradiz a autoridade. Agora ele vai para `ResultadoVotos.presidencia`,
  fora do enum de posição.
- **V4** — o placar vive no TEXTO da descrição (formatos distintos de plenário e
  comissão); é extraído por parsing e reconciliado contra a soma dos nominais
  (§5.2: soma == placar; votantes ≤ 513). Descrição sem número → placar `None`,
  nunca 0. O parser foi validado contra amostras vivas dos dois tipos.

**Miss no lookup não cria perfil inline — vai à quarentena.** A disciplina da
§6 permanece: sem o deputado ingerido, o voto vai à quarentena por
`integridade_referencial`. É por isso que deputados precedem votações.

**Regra 6 do contrato.** Votação declarada secreta que traz nominal → lote
inteiro à quarentena. Salvar "só alguns nominais de secreta" produz o índice
parcial que a regra existe para impedir.

---

## Coletor de deputados (§12, §5.3)

- **Dedup por id antes de qualquer contagem** — a disciplina central da §12.
- **Perfil + `id_externo`** (método `fonte_direta`, grau `direto`, §6).
- **UF/partido de mandato são temporais** e vão em `mandato_hint`, jamais como
  atributo atemporal do perfil (§12 D3). O schema confirma: `profiles` só tem
  `naturalidade_uf` (nascimento), não UF de mandato.
- **Enriquecimento por detalhe** — nome civil, nascimento, naturalidade (sinais
  de convergência da §5.3, PII interna da §3.5). Uma chamada de detalhe por
  pessoa deduplicada; falha pontual não derruba a rodada. `ultimoStatus`
  (temporal) é deliberadamente ignorado.

---

## Histórico de mandatos → `vinculo_temporal` (§4, §12 D4)

A camada temporal do parlamentar: versiona partido, UF e ocupação da cadeira por
período, para resolver todo atributo NA DATA DO FATO (um voto de 2016 resolve o
partido de 2016, não o atual). É o pré-requisito da camada ouro e do contrato de
resposta do Prometeus.

- **Snapshots → intervalos.** A fonte (`/deputados/{id}/historico`) dá pontos no
  tempo (posse, troca de partido, licença, fim de mandato), não períodos.
  `construir_vinculos` pareia snapshots consecutivos em `[início, próximo)` — a
  `vigencia` (daterange). Validado ao vivo: Danilo Forte, 23 snapshots → **10
  vínculos não sobrepostos**, linha do tempo PMDB→PSB→…→UNIÃO→PP.
- **Mandatos sem sobreposição (§5.2)** garantido por construção; provado por
  `conferir_sem_sobreposicao`. Duração nula descartada; transição sem data →
  quarentena (§12 D3/D5).
- **`partido_id` canônico fica None** neste passe; preserva-se
  `partido_sigla_fonte` (a verdade da fonte). Resolver o partido canônico é o
  coletor de `/partidos` + linhagem por curadoria (§4), etapa própria.
- **Suplente em exercício → quarentena.** A constraint `vinculo_suplente_coerente`
  exige o titular da cadeira, e descobrir de quem é a cadeira é cross-referência
  da §6.4. Dado ausente é melhor que dado errado (§1).
- **Fonte mais instável da Câmara (§12 D2)** — o retry trata a instabilidade; a
  coleta é por pessoa, e a falha de uma não derruba a rodada. Migration 0005 dá
  o alvo de upsert idempotente (reingerir atualiza, não duplica).

## Partidos canônicos e a resolução por sigla (§4)

O partido é também um `profile` (tipo='partido'), alvo estável do
`vinculo_temporal`. `camara/partidos.py` ingere os partidos ATUAIS da API
(`/partidos`) — a parte mecânica — e o vínculo resolve `partido_id` casando a
`partido_sigla_fonte` com a sigla atual.

**Fronteira de curadoria, declarada e honesta (§4).** Validado ao vivo: das
siglas na linha do tempo do Danilo Forte, PSB/PSDB/UNIÃO/PP resolvem; PMDB
(renomeado MDB), DEM (fundido em UNIÃO) e S.PART. (sem partido) ficam com
`partido_id` null, com a sigla-fonte preservada. Resolver siglas históricas e
linhagem de fusões exige `partido_sigla_historico` + `partido_linhagem` por
curadoria — uma fonte que a API não dá. Dado ausente é melhor que dado errado
(§1): não se chuta que PMDB "é" MDB sem a curadoria que o afirme.

## Coletor de tramitações (§11, §5.2)

Área D — a cadeia de despachos de cada proposição (`/proposicoes/{id}/tramitacoes`).

- **Sequência temporal monotônica (§5.2)** — identidade cruzada sobre a cadeia
  inteira, em `conferir_sequencia_monotonica`. Comparação **por data de
  calendário**, não por instante: a fonte viva (PL 736/2015) mostrou
  tramitações carimbadas às 00:00 (hora ausente), e comparar por instante
  gritava à toa numa reordenação intradiária benigna — o oposto de um monitor
  útil (§19). A `sequencia` é a ordem autoritativa; a data é que não pode
  recuar. Virou teste de regressão.
- **Ressalva bicameral (§11)** — o endpoint traz só a perna da Câmara; cada
  registro carrega `casa='camara'` para a regra de resposta declarar qual casa
  se observa.
- **Proveniência do texto (§11)** — `despacho` é texto de parte interessada
  (secretaria/relator); proveniência constante do campo, documentada.
- **O que a API não expõe:** não há par origem→destino por linha, então a
  identidade "destino de um despacho = origem do seguinte" não é verificável
  aqui — não foi inventada.

Persistido (`salvar_tramitacoes`, resolve `proposicao_id`) e wireado no
orquestrador (uma rodada por proposição aprovada).

## Persistência e orquestração

**`repositorio.py` — porta injetável.** O banco é injetado por `ClienteBanco`
(mesma disciplina do HTTP), então o mapeamento e a resolução de chaves são
testáveis sem Supabase. Cobre bronze (imutável, insert ignorando conflito),
`profiles`+`id_externo`, `proposicao`, `votacao` (resolve `proposicao_id`) e
`voto_nominal` (resolve `votacao_id`).

**O lookup de `id_externo` deixou de ser injetado e virou a tabela.**
`lookup_id_externo(banco)` fecha o ciclo que os coletores dependiam.

**Preservação de bronze completa (§3.1).** Lista, detalhe e votos de cada
votação são todos persistidos. O voto não tem id de fonte próprio — a
identidade é o par (votação, deputado), gravada como `id_na_fonte =
"{votação}:{deputado}"` via o parâmetro `id_na_fonte_de` de `salvar_bronze`.
Assim, para qualquer voto servido dá para chegar ao dado bruto que o produziu.

**Migration 0004 — placar nulável.** A persistência revelou o atrito: o V4
produz `None` quando não há placar no texto, mas a coluna era `int not null
default 0`. Gravar 0 fabricaria dado ("dado errado é pior que ausente", §1).
Correção em migration nova, nunca editando antiga (padrão da 0003).

**`orquestrador.py` — a ordem de FKs numa rodada.** Deputados → lookup real →
proposições → votações → votos nominais. Um teste de integração prova a
resolução de votos ponta a ponta, e, pela negativa, que sem deputados os votos
não resolvem — a dependência de ordem que o orquestrador existe para garantir.

---

## O que segue pendente

**Deploy (só falta pacote + credenciais).** O adaptador Supabase concreto
(`supabase_adapter.py`), o cliente HTTP real (`http.py`) e o entrypoint
(`run_ingestao.py`) já estão escritos e testados — o adaptador contra um duble
stateful e como drop-in do repositório; o HTTP com opener injetado. No deploy:
`pip install supabase`, definir `SUPABASE_URL`/`SUPABASE_SERVICE_KEY`, aplicar
as migrations 0001–0005 e rodar `run_ingestao.py`. O pacote `supabase` NÃO está
instalado neste ambiente (a pasta local `supabase/` induz falso-positivo em
`find_spec`; verificado por import real), por isso o import é tardio.

**Presidência (Artigo 17).** Computada em `ResultadoVotos.presidencia`, sem
coluna/tabela alvo ainda. Precisa de destino no schema para ser persistida.

**Linhagem de partidos (§4).** Os partidos ATUAIS já são canônicos e resolvem o
`partido_id` das siglas atuais. Falta a LINHAGEM: siglas históricas (PMDB→MDB) e
fusões (DEM/PSL→UNIÃO), em `partido_sigla_historico` + `partido_linhagem`, que a
API não fornece — é reconstrução por curadoria.

**Titular do suplente (§6.4).** Períodos de suplente em exercício vão à
quarentena hoje; resolver de quem é a cadeira é cross-referência própria.

**Comissões dos deputados (§12 D5).** Vínculos de comissão têm defeitos de
integridade próprios (sobreposição, duração nula, recriação por sessão).

**Camada ouro: pronta (migration 0006).** As três camadas estão de pé —
bronze (cru), prata (tratado) e ouro (servido). As views públicas
(`parlamentar_publico`, `votacao_publica`, `voto_nominal_publico`, …) embutem
proveniência e frescor e **excluem PII** (§3.5): a view é a fronteira, porque
RLS é por linha e não corta coluna. É a camada — e só ela — que o app e o
Prometeus leem; nada ao vivo da fonte. Falta: as telas que a consomem
(Onda 1.5) e as views de agregação/IA (Onda 2).
