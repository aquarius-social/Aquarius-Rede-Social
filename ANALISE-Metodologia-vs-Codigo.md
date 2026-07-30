# Análise — Metodologia de Dados × Código atual

Documento de referência. Produzido em **2026-07-29** como fechamento do
Passo 2 do `ESTADO_ATUAL.md` (confirmar os `[verificar]` contra a API real).

Autoridade: `Aquarius_Metodologia_de_Dados.docx` (jul/2026) é, por decisão
travada no `CLAUDE.md`, a autoridade máxima sobre a camada de dados. Onde o
código diverge dela, **corrige-se o código** — salvo erro comprovado na
Metodologia (nenhum encontrado, ver abaixo).

## Método desta verificação

Os coletores foram conferidos contra a **API viva** da Câmara
(`dadosabertos.camara.leg.br/api/v2`) em 2026-07-29, e o resultado cruzado
com a Metodologia. Amostras usadas:

- Proposição `2641717` (lista + detalhe).
- Votação simbólica `996958-88` (lista vazia de votos, com sucesso).
- Votação nominal `2369594-8` (371 votos individuais).
- Deputado `204379` (lista + detalhe).

**A Metodologia foi corroborada, não contradita.** Tudo que a §10 afirma
sobre votações reproduziu-se ao vivo: campo de proposição da lista nulo,
vínculo correto em `proposicoesAfetadas` no detalhe, id da votação começando
pelo id da proposição, lista de votos vazia em simbólica, e o registro
"Artigo 17" como marca de quem presidiu. Nenhum erro na Metodologia.

---

## Rota escolhida

**Rota A — consertar VOTAÇÕES primeiro**, depois seguir para deputados.
Motivo: o item V1 abaixo trava o coletor de votações em `QUEBRA` contra a
API real; corrigir deixa o pipeline de votações correto ponta a ponta antes
de avançar.

**Progresso (2026-07-29):** V1, V2, V3 e V4 **implementados e testados** (suíte
em 90 testes, verde). O parser de placar (V4) foi validado contra amostras
**vivas** de plenário e de comissão — não só fixtures. Cobre o formato de
plenário e três sub-formatos de comissão; frase de comissão nova e não vista
devolve placar parcial ou `None` (degradação honesta, §1). "Quórum" não é lido
como total. Reconciliação §5.2 (soma dos nominais == placar; votantes ≤ 513)
roda na `rodada_votacoes` e expõe divergências em `placar_violacoes`.

---

## VOTAÇÕES — Metodologia × código (§9, §10, §5.2, §19)

| # | Metodologia (autoridade) | Código atual | Ação |
|---|---|---|---|
| V1 | Vínculo à matéria vem do **detalhe**, campo `proposicoesAfetadas`; a lista traz o campo nulo em toda a amostra (§10) | `coletar_bronze_votacoes` só chama a **lista** (`votacoes.py:102`); o gate exige o campo crítico `proposicoes_`, que não existe → `canario.py:104` gera **QUEBRA** em toda execução real | Passar a buscar o **detalhe** de cada votação e ler `proposicoesAfetadas`; remover `proposicoes_` de `CAMPOS_CRITICOS_VOTACAO` (`votacoes.py:54`) |
| V2 | Corroborar a matéria pelo **id da votação, que começa pelo id da proposição** (§10) — confirmado: `996958-88`→`996958`, `2369594-8`→`2369594` | Não usa | Check de consistência: prefixo do id da votação == id da proposição afetada; divergência é violação |
| V3 | **Artigo 17 = registro de quem presidiu a sessão**; excluído do placar; "nunca se conta como posição nem como ausência" (§10) | `MAPA_VOTO["Artigo 17"] = "obstrucao"` (`votacoes.py:73`) — trata como modalidade de voto | **CONFLITO resolvido a favor da Metodologia** (decisão do usuário): mapear para um marcador "presidiu", fora do enum de posição e fora do placar |
| V4 | Placar declarado vive **no texto da `descricao`**, em dois formatos (plenário ≠ comissão), extraído por parsing; reconciliar com a soma dos nominais (§10, §5.2) | `transformar_votacao` lê `payload["sim"/"nao"/"abstencao"]` (`votacoes.py:163-165`), campos ausentes na lista real → sempre `0`; `_contadores_coerentes` passa trivialmente | Parsear o placar da `descricao`; identidade interna §5.2: **soma dos nominais == placar** e **votantes ≤ 513** |
| V5 | Simbólica → lista de votos **vazia com sucesso** = vazio legítimo; "só um canário nominal distingue de falha" (§10, §19) | Já trata simbólica sem nominais como caso normal, não como falha referencial (`votacoes.py:154+`) — **OK** | Manter; garantir que o **canário** use uma votação **nominal** conhecida (não simbólica) |
| V6 | Os ~32 "objetos possíveis" (`objetosPossiveis`) são de teor procedimental e servem a contexto, **nunca à atribuição do voto** (§10) | Não lê `objetosPossiveis` — **OK** | Nenhuma; se um dia usar, não atribuir voto por eles |
| V7 | O endpoint `/votos` **rejeita os parâmetros de paginação** e vem íntegro numa resposta (§10) | Assumido no código — **OK** | Confirmar que `coletar_bronze_votos` não pagina |
| V8 | Classificar cada votação por **etapa (mérito × procedimento)**; o oráculo responde pelo voto de mérito (§10) | Não classifica | Downstream (contrato de resposta); registrar a etapa já na camada prata para não reprocessar |

## DEPUTADOS / Parlamentares — desenho conforme Metodologia (§12, §5.2, §6)

**Progresso (2026-07-29):** implementado em `camara/deputados.py` — D1 (dedup por
id), D3 (UF/partido como `mandato_hint`, não atributo do perfil), D6 (`id_externo`
fonte_direta/direto) **e o enriquecimento por detalhe** (nome civil, nascimento,
naturalidade — sinais §5.3; `ultimoStatus` temporal ignorado; falha pontual do
detalhe tolerada). Tudo testado (107 testes) e validado ao vivo (leg. 56:
1.073 linhas → 613 pessoas; PII conferida em deputado real). Pendentes como
etapas próprias: D2/D4 (histórico + `vinculo_temporal`) e D5 (comissões).
Tabela original abaixo.

| # | Metodologia (autoridade) | Ação no coletor a criar |
|---|---|---|
| D1 | A listagem por legislatura repete o mesmo id **uma vez por filiação** vigente; linhas = estados de filiação, não pessoas (§12) | **Deduplicar por `id` antes de qualquer contagem**; popular `profiles` uma vez por pessoa |
| D2 | O histórico de transições é **a fonte menos disponível de todas** (alterna resposta/falha, timeout ~15s) (§12) | Coletar em **lote com retry**, persistir permanente, **nunca consultar ao vivo**; se falhar, vale a versão anterior com data declarada |
| D3 | Todo atributo resolvido **na data do fato** (partido/UF de então) (§12, princípio 6 do CLAUDE.md) | Não achatar `ultimoStatus` como verdade atemporal; mandato/filiação é etapa própria — **não popular `vinculo_temporal` no 1º passe** |
| D4 | Identidades internas §5.2: mandatos sem sobreposição; filiação sem lacuna não declarada; toda transição com data | Verificadores do portão prata para o histórico (quando ingerido) |
| D5 | Comissões: sobreposições, intervalos nulos, recriação por sessão; consulta sem janela devolve só os vínculos correntes (§12) | Fora do 1º passe; documentar como etapa posterior |
| D6 | Vínculo por **identificador embutido**, com grau declarado (§6) | `id_externo` (sistema='camara') — já é o padrão dos outros coletores |

### Referência de campos da API viva (deputados, 2026-07-29)

- **Lista** `GET /deputados`: `id`, `nome`, `siglaPartido`, `uriPartido`, `siglaUf`, `idLegislatura`, `urlFoto`, `email`.
- **Detalhe** `GET /deputados/{id}`: `cpf`, `nomeCivil`, `dataNascimento`, `dataFalecimento`, `escolaridade`, `sexo`, `ufNascimento`, `municipioNascimento`, `redeSocial`, `urlWebsite`, e o aninhado **`ultimoStatus`** (partido/UF/situação correntes — resolver na data, ver D3).

---

## Achados que NÃO são divergência (registro)

- Proposições: os 6 campos críticos batem na lista; `statusProposicao` e
  `uriAutores` existem no detalhe. `dataApresentacao` vem como datetime com
  precisão de minuto (`2026-07-29T15:57`); o código guarda a string crua
  (`proposicoes.py:145`) — não quebra, fica por normalizar.
- Votos: `tipoVoto` e a chave `deputado_` (com underscore final) são reais na
  API; `CAMPOS_CRITICOS_VOTO` está correto. `deputado_.id` resolve por
  `id_externo`.
- O marcador `[verificar]` de `_nominal` (`votacoes.py:216`): a premissa se
  confirma — a Câmara não publica booleano de "nominal" no objeto da votação.
  A heurística sobre `descricao` segue justificada.

## Disciplina do contrato (§19) — os quatro estados

Ao mexer no gate de votações, preservar a distinção:
**Falha** (fonte muda ou canário não-vazio volta vazio) · **Instabilidade**
(falha e recupera na retentativa, registrar código) · **Quebra** (campo
crítico sumiu, suspende a área) · **Alerta** (campo novo / descontinuação,
leitura humana). Confundir Falha com vazio legítimo (V5) é o erro que a §10
alerta explicitamente.
