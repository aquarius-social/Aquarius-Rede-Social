-- =============================================================================
-- Aquarius · deploy_all.sql — schema completo para o PRIMEIRO provisionamento
-- =============================================================================
-- Concatenação, NA ORDEM, de TODAS as migrations, envolta numa transação:
-- se qualquer statement falhar, TUDO é desfeito (nada de schema pela metade).
-- Cole no SQL Editor do Supabase e rode uma vez. Mudanças depois = migration nova.
-- Gerado de: 0001_identidade.sql, 0002_camadas_civicas.sql, 0003_votacao_nominal.sql, 0004_placar_nao_extraido.sql, 0005_vinculo_upsert.sql, 0006_camada_ouro.sql, 0007_ouro_coletivos.sql, 0008_despesas_ceap.sql
-- =============================================================================

begin;



-- >>> 0001_identidade.sql >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
-- =============================================================================
-- Aquarius · Onda 0 · Fundação de identidade
-- =============================================================================
-- Implementa o modelo relacional da seção 4 da Metodologia de Dados (jul/2026).
--
-- Princípio que governa este arquivo (seção 6):
--   "Se a identidade não estiver resolvida, o cruzamento atribui o dado ao
--    parlamentar errado, e a qualidade das demais camadas deixa de importar."
--
-- Duas regras estruturais herdadas da Metodologia:
--   1. Identificador externo NUNCA é chave primária (seção 4).
--   2. Toda aresta carrega período de validade — um voto de 2021 resolve o
--      partido de 2021, não o atual (seção 4 e modo de falha "atributo
--      resolvido no presente", Tabela 9).
--
-- CONFERIR CONTRA A API REAL antes de ir a produção: os nomes de campo de
-- origem marcados com [verificar] foram derivados da prosa da Metodologia, não
-- de consulta à interface viva. A própria Metodologia exige verificação por
-- consulta real, com amostra e data registradas.
-- =============================================================================

create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";
-- btree_gist dá ao GiST classes de operador para tipos escalares (uuid, enum),
-- necessárias nas constraints `exclude using gist` de vinculo_temporal e
-- partido_sigla_historico, que combinam `profile_id/partido_id with =` (uuid) e
-- `casa with =` (enum) com `vigencia with &&` (daterange). Sem ela: erro 42704.
create extension if not exists "btree_gist";

-- -----------------------------------------------------------------------------
-- Domínios e enums
-- -----------------------------------------------------------------------------

-- Tipos de perfil.
--
-- Nota de projeto: a Metodologia define `profiles` como "o identificador próprio
-- do Aquarius para cada pessoa". A Concepção do Produto amplia o conceito para
-- toda entidade seguível ("Partidos, comissões e frentes são o mesmo objeto").
-- Conciliamos: `profiles` é a tabela mãe de tudo que se pode seguir; a
-- resolução de identidade por convergência (id_externo, vinculo_temporal)
-- aplica-se apenas a perfis de pessoa natural, hoje `parlamentar`.
create type profile_tipo as enum (
  'parlamentar',   -- pessoa natural com mandato
  'partido',
  'bloco',
  'comissao',
  'frente',
  'orgao'
);

create type casa_legislativa as enum ('camara', 'senado', 'congresso');

-- Grau de confiança de uma ligação de identidade (seção 5.3).
-- A escala não é opinião: decorre do número de sinais INDEPENDENTES que
-- convergiram. Ver services/ingestao/resolucao/resolvedor.py.
create type grau_confianca as enum (
  'direto',        -- 2+ sinais independentes  -> afirmação direta
  'com_ressalva',  -- 1 sinal isolado          -> afirmação com ressalva
  'recusado'       -- sinais contraditórios    -> recusa, divergência exposta
);

-- Origem do identificador externo.
create type sistema_externo as enum (
  'camara',              -- id de deputado na Câmara
  'senado',              -- código de parlamentar no Senado
  'autor_orcamentario'   -- código de autor embutido no código da emenda (seção 6.3)
);

-- Como a ligação foi estabelecida. Registrar o método é o que permite
-- reprocessar quando a regra muda (seção 3.4: a versão da regra de tratamento
-- integra a chave de invalidação).
create type metodo_ligacao as enum (
  'fonte_direta',        -- a própria fonte declarou o identificador
  'convergencia',        -- resolvido pelo procedimento da seção 5.3
  'conferencia_humana',  -- resíduo conferido por pessoa (seção 6.3)
  'curadoria'            -- linhagem partidária reconstruída (seção 4)
);

create type ocupacao_cadeira as enum ('titular', 'suplente_em_exercicio', 'licenciado');


-- -----------------------------------------------------------------------------
-- profiles — a tabela mãe
-- -----------------------------------------------------------------------------
-- Existe para dar um alvo único e estável a todas as arestas polimórficas do
-- produto: follow, notification, engagement_event e o vínculo post↔perfil.
--
-- Motivo concreto: no protótipo, o identificador 'p1' designa simultaneamente a
-- Comissão de Educação e uma deputada, porque cada tipo de entidade tem seu
-- próprio espaço de identificadores. Uma chave global elimina a classe inteira
-- desse defeito.
create table profiles (
  id              uuid primary key default gen_random_uuid(),
  tipo            profile_tipo not null,

  -- Nome de exibição. Para parlamentar é o nome parlamentar (nome de urna).
  nome            text not null,
  -- Sigla, quando aplicável (PT, CCJC, FPME). Não é chave.
  sigla           text,
  slug            text not null,

  -- Nome civil. Restrito à camada interna de resolução: a seção 3.5 determina
  -- que nome civil, data de nascimento e naturalidade "permanecem restritos à
  -- camada interna de resolução, sem integrar respostas".
  nome_civil      text,
  data_nascimento date,
  naturalidade_municipio text,
  naturalidade_uf        char(2),

  foto_url        text,
  ativo           boolean not null default true,

  -- Proveniência (convenção transversal: seção 3.1, camada bronze).
  source          text not null,
  source_url      text,
  synced_at       timestamptz not null default now(),

  criado_em       timestamptz not null default now(),
  atualizado_em   timestamptz not null default now(),

  constraint profiles_slug_unico unique (slug),

  -- Atributos de pessoa natural só fazem sentido em perfil de pessoa.
  constraint profiles_pessoa_natural check (
    tipo = 'parlamentar'
    or (nome_civil is null and data_nascimento is null
        and naturalidade_municipio is null and naturalidade_uf is null)
  )
);

create index profiles_tipo_idx  on profiles (tipo) where ativo;
create index profiles_nome_idx  on profiles using gin (to_tsvector('portuguese', nome));
create index profiles_sigla_idx on profiles (tipo, sigla) where sigla is not null;

comment on table profiles is
  'Tabela mãe de toda entidade seguível. Metodologia de Dados, seção 4.';
comment on column profiles.nome_civil is
  'PII restrita à camada de resolução. Nunca integra resposta servida (seção 3.5).';


-- -----------------------------------------------------------------------------
-- id_externo — correspondência para os identificadores das fontes
-- -----------------------------------------------------------------------------
-- Seção 4: "tabela de correspondência do perfil para os identificadores da
-- Câmara, do Senado e o código de autor da execução orçamentária, com o método
-- e o grau de confiança de cada ligação."
--
-- Guardar o grau é o que permite ao contrato de resposta (seção 20, regra 2)
-- "declarar a base da atribuição quando o vínculo não for direto".
create table id_externo (
  id              uuid primary key default gen_random_uuid(),
  profile_id      uuid not null references profiles(id) on delete cascade,
  sistema         sistema_externo not null,
  identificador   text not null,

  metodo          metodo_ligacao not null,
  grau            grau_confianca not null,

  -- Quais sinais sustentaram a ligação. Ex.: {nome_civil, data_nascimento,
  -- naturalidade}. Guardado para auditoria e para reprocessamento seletivo.
  sinais          text[] not null default '{}',
  -- Quando grau = 'recusado', a divergência que causou a recusa. A seção 5.3 é
  -- explícita: "sinais contraditórios produzem recusa com a divergência
  -- exposta, nunca escolha pelo mais provável".
  divergencia     text,

  -- Versão da regra que produziu esta ligação (seção 3.4).
  versao_regra    text not null,
  -- Marcado quando o resolvedor recusou automatizar e mandou para pessoa
  -- (seção 6.3: doze linhas em seiscentas e vinte e oito, na primeira execução).
  pendente_conferencia boolean not null default false,

  resolvido_em    timestamptz not null default now(),

  -- Um identificador de uma fonte aponta para no máximo um perfil.
  constraint id_externo_unico unique (sistema, identificador),
  -- Recusa exige divergência declarada; o contrário também.
  constraint id_externo_recusa_declarada check (
    (grau = 'recusado') = (divergencia is not null)
  ),
  -- Grau 'direto' exige pelo menos dois sinais (seção 5.3).
  constraint id_externo_grau_coerente check (
    grau <> 'direto' or array_length(sinais, 1) >= 2
    or metodo in ('fonte_direta', 'conferencia_humana')
  )
);

create index id_externo_profile_idx   on id_externo (profile_id);
create index id_externo_pendente_idx  on id_externo (pendente_conferencia)
  where pendente_conferencia;


-- -----------------------------------------------------------------------------
-- partido — canônico, com linhagem
-- -----------------------------------------------------------------------------
-- Seção 4: "a fonte preserva o identificador no renome, mas apaga as origens
-- nas fusões, e a linhagem é reconstruída por curadoria."
create table partido (
  id             uuid primary key default gen_random_uuid(),
  profile_id     uuid not null references profiles(id) on delete cascade,
  sigla_atual    text not null,
  nome_atual     text not null,
  numero_urna    int,
  fundacao       date,
  extincao       date,

  source         text not null,
  source_url     text,
  synced_at      timestamptz not null default now(),

  constraint partido_profile_unico unique (profile_id)
);

-- Histórico de siglas: renome preserva a identidade da agremiação.
create table partido_sigla_historico (
  id           uuid primary key default gen_random_uuid(),
  partido_id   uuid not null references partido(id) on delete cascade,
  sigla        text not null,
  nome         text not null,
  vigencia     daterange not null,
  constraint partido_sigla_sem_sobreposicao exclude using gist (
    partido_id with =,
    vigencia   with &&
  )
);

-- Linhagem: fusões e incorporações, reconstruídas por curadoria.
create table partido_linhagem (
  id             uuid primary key default gen_random_uuid(),
  sucessor_id    uuid not null references partido(id) on delete cascade,
  antecessor_id  uuid not null references partido(id) on delete cascade,
  tipo_evento    text not null check (tipo_evento in ('fusao','incorporacao','renome','cisao')),
  data_evento    date not null,
  metodo         metodo_ligacao not null default 'curadoria',
  fonte_curadoria text,
  constraint partido_linhagem_sem_autoref check (sucessor_id <> antecessor_id),
  constraint partido_linhagem_unica unique (sucessor_id, antecessor_id, data_evento)
);


-- -----------------------------------------------------------------------------
-- vinculo_temporal — a aresta com validade
-- -----------------------------------------------------------------------------
-- Seção 4: "versiona partido, unidade federativa e ocupação da cadeira por
-- período: um voto de 2021 resolve o partido de 2021, não o atual. A ocupação
-- registra também o suplente em exercício, porque voto, despesa e discurso de
-- uma janela pertencem a quem ocupava o assento."
--
-- É a defesa estrutural contra dois modos de falha da Tabela 9:
--   · "Atributo resolvido no presente" -> voto antigo atribuído ao partido atual
--   · "Ausência lida como negação"     -> exige janela, não instante
create table vinculo_temporal (
  id            uuid primary key default gen_random_uuid(),
  profile_id    uuid not null references profiles(id) on delete cascade,

  casa          casa_legislativa not null,
  legislatura   int,
  uf            char(2) not null,
  partido_id    uuid references partido(id),
  -- Sigla como veio da fonte, no momento do fato. Preservada mesmo quando o
  -- partido canônico foi resolvido: a fonte é a verdade sobre o que publicou.
  partido_sigla_fonte text,

  ocupacao      ocupacao_cadeira not null default 'titular',
  -- Quando ocupacao = 'suplente_em_exercicio', de quem é a cadeira.
  titular_profile_id uuid references profiles(id),

  vigencia      daterange not null,

  source        text not null,
  source_url    text,
  synced_at     timestamptz not null default now(),

  constraint vinculo_suplente_coerente check (
    (ocupacao = 'suplente_em_exercicio') = (titular_profile_id is not null)
  ),
  constraint vinculo_sem_autoref check (
    titular_profile_id is null or titular_profile_id <> profile_id
  ),
  -- Uma pessoa não ocupa duas cadeiras na mesma casa ao mesmo tempo.
  constraint vinculo_sem_sobreposicao exclude using gist (
    profile_id with =,
    casa       with =,
    vigencia   with &&
  )
);

create index vinculo_profile_idx  on vinculo_temporal (profile_id);
create index vinculo_vigencia_idx on vinculo_temporal using gist (vigencia);
create index vinculo_partido_idx  on vinculo_temporal (partido_id);

comment on table vinculo_temporal is
  'Partido, UF e ocupação da cadeira versionados por período. Resolver sempre na data do fato, nunca no presente (Metodologia, seção 4 e Tabela 9).';


-- -----------------------------------------------------------------------------
-- registro_fonte — o catálogo de fontes e o teste de contrato
-- -----------------------------------------------------------------------------
-- Seção 2 (matriz de fontes) e seção 19 (monitoramento de contrato).
create table registro_fonte (
  id                uuid primary key default gen_random_uuid(),
  chave             text not null unique,     -- ex.: 'camara.deputados'
  nome              text not null,
  base_url          text not null,
  area              text not null,            -- A..I, conforme a Parte II
  -- Classe de volatilidade governa cadência de coleta E política de cache (3.3).
  volatilidade      text not null check (volatilidade in ('imutavel','lenta','diaria','continua')),
  cadencia_horas    int not null,
  -- Janela móvel: deve ser maior que a maior defasagem observada na área.
  -- Verificou-se votação registrada catorze dias após a sessão (seção 3.3).
  janela_movel_dias int not null,
  -- Consulta cujo resultado se sabe NÃO vazio. Sem canário, vazio é ambíguo,
  -- pois a ausência pode ser legítima (seção 19).
  canario_path      text,
  canario_validado  boolean not null default false,
  ativo             boolean not null default true,
  criado_em         timestamptz not null default now(),

  -- "os canários são validados antes de entrar em regime, pois monitor que
  --  grita à toa é monitor ignorado" (seção 19).
  constraint fonte_canario_validado_para_ativar check (
    not ativo or canario_path is null or canario_validado
  )
);


-- -----------------------------------------------------------------------------
-- quarentena — o que não passou no portão
-- -----------------------------------------------------------------------------
-- Seção 3.1: "O que viola um portão vai à quarentena com o motivo registrado,
-- e não adiante."
create table quarentena (
  id            uuid primary key default gen_random_uuid(),
  fonte_chave   text not null references registro_fonte(chave),
  camada        text not null check (camada in ('bronze','prata','ouro')),
  dimensao      text not null check (dimensao in (
                  'completude','precisao','consistencia',
                  'integridade_referencial','tempestividade','unicidade')),
  motivo        text not null,
  -- O registro exato que falhou, como veio da fonte.
  payload       jsonb not null,
  -- Resumo criptográfico do lote, para detectar edição feita no lugar — a
  -- contagem não detecta (seção 3.4 e estudo da seção 8).
  hash_lote     text,
  resolvido     boolean not null default false,
  criado_em     timestamptz not null default now()
);

create index quarentena_aberta_idx on quarentena (fonte_chave, dimensao)
  where not resolvido;


-- -----------------------------------------------------------------------------
-- RLS — negar por padrão
-- -----------------------------------------------------------------------------
-- Dado cívico é público por natureza, mas os campos de PII da camada de
-- resolução não são. A política de leitura pública vive na migration da camada
-- servida (ouro); aqui, nada é legível por cliente anônimo.
alter table profiles              enable row level security;
alter table id_externo            enable row level security;
alter table partido               enable row level security;
alter table partido_sigla_historico enable row level security;
alter table partido_linhagem      enable row level security;
alter table vinculo_temporal      enable row level security;
alter table registro_fonte        enable row level security;
alter table quarentena            enable row level security;

-- Sem policy = sem acesso. O serviço de ingestão usa a service role, que
-- ignora RLS por desenho.


-- >>> 0002_camadas_civicas.sql >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
-- =============================================================================
-- Aquarius · Onda 1 · Camadas bronze e prata para o núcleo cívico
-- =============================================================================
-- Esta migration implementa as três camadas da seção 3.1 da Metodologia para
-- as primeiras áreas atacadas (Área B — proposições, Área C — votações,
-- Área D — tramitações).
--
--   Bronze — cópia exata do que a fonte devolveu, imutável, com resumo
--            criptográfico. Auditoria de origem.
--   Prata  — normalizado, tipado, com FK para profiles. É o que o produto lê.
--   Ouro   — projeções específicas (rankings, agregados) — vive em views.
--
-- A tabela bronze é única (JSONB polimórfico), a tabela prata tem shape
-- estrito por entidade. Motivo: bronze existe para preservar, prata para
-- consumir com segurança.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- BRONZE — payload imutável
-- -----------------------------------------------------------------------------

create table bronze_registro (
  id            uuid primary key default gen_random_uuid(),

  -- Chave da fonte: 'camara.proposicoes', 'camara.votacoes', etc.
  -- Referencia registro_fonte.chave sem constraint dura: uma coleta pode
  -- preceder o registro formal da fonte no catálogo, e desligar isso não
  -- justifica derrubar dado bruto.
  fonte         text not null,

  -- URL efetiva da requisição, para reprodução.
  fonte_url     text not null,

  -- ID do item na fonte, extraído do payload no momento da inserção.
  -- É o que sustenta dedup por conteúdo (seção 5.4).
  id_na_fonte   text not null,

  payload       jsonb not null,

  -- Resumo criptográfico do payload canonizado. Igualdade de hash entre
  -- coletas do mesmo id = repetição; desigualdade = edição retroativa.
  -- É o instrumento que detectou edição feita no lugar em despesas.
  hash_conteudo text not null,

  coletado_em   timestamptz not null default now(),

  -- Uma coleta é um evento, não um estado. Nunca sobrescrever bronze:
  -- coleta nova do mesmo id gera linha nova, e é o histórico dessa cadeia
  -- que sustenta a comparação temporal (Nível 3, seção 5.4).
  constraint bronze_unico_por_coleta unique (fonte, id_na_fonte, hash_conteudo)
);

create index bronze_por_fonte_id_data on bronze_registro (fonte, id_na_fonte, coletado_em desc);
create index bronze_por_hash on bronze_registro (fonte, hash_conteudo);

comment on table bronze_registro is
  'Camada bronze — preservação imutável, com hash por lançamento para detectar edição retroativa (Metodologia, seções 3.1 e 3.4).';


-- -----------------------------------------------------------------------------
-- PRATA — proposicao (Área B)
-- -----------------------------------------------------------------------------

create type proposicao_tipo as enum (
  'PL', 'PEC', 'MP', 'PLP', 'PDL'
  -- Outros tipos que a Câmara publica ('REQ', 'INC', etc.) são decisão de
  -- escopo do produto. Adicionar aqui exige verificar impacto na UI, não
  -- só ampliar o enum.
);

create table proposicao (
  id                uuid primary key default gen_random_uuid(),

  -- Discriminação por casa: a mesma proposição pode ser tramitada nas duas
  -- casas com identificadores próprios (ver Junção bicameral, seção 17).
  casa_origem       casa_legislativa not null,
  id_na_fonte       text not null,

  tipo              proposicao_tipo not null,
  numero            int not null,
  ano               int not null,

  -- Rótulo de exibição, derivado. Guardado para busca textual e para não
  -- montar em toda leitura.
  identificador     text not null,

  ementa            text not null,
  tema              text,
  situacao          text,

  orgao_perfil_id   uuid references profiles(id),
  data_apresentacao date not null,

  inteiro_teor_url          text,
  inteiro_teor_tem_texto    boolean,

  tem_resumo_ia     boolean not null default false,

  -- Proveniência (convenção transversal, seção 3.1).
  source            text not null,
  source_url        text,
  synced_at         timestamptz not null default now(),

  -- Última coleta bronze que originou este estado, para rastreabilidade.
  bronze_origem_id  uuid references bronze_registro(id),

  criado_em         timestamptz not null default now(),
  atualizado_em     timestamptz not null default now(),

  constraint proposicao_unica_por_casa unique (casa_origem, id_na_fonte),
  constraint proposicao_numero_positivo check (numero > 0),
  constraint proposicao_ano_razoavel check (ano between 1988 and 2100)
);

create index proposicao_data_idx  on proposicao (data_apresentacao desc);
create index proposicao_tema_idx  on proposicao (tema) where tema is not null;
create index proposicao_busca_idx on proposicao using gin (to_tsvector('portuguese', ementa));


-- -----------------------------------------------------------------------------
-- PRATA — votacao e voto nominal (Área C)
-- -----------------------------------------------------------------------------

create type voto_tipo as enum ('sim', 'nao', 'abstencao', 'obstrucao', 'ausente');

create table votacao (
  id              uuid primary key default gen_random_uuid(),
  casa            casa_legislativa not null,
  id_na_fonte     text not null,
  proposicao_id   uuid references proposicao(id),

  titulo          text not null,
  data_hora       timestamptz not null,
  resultado       text not null,

  -- Contadores agregados, como a fonte publica. NÃO devem ser somados a
  -- partir dos nominais em produção: os totais oficiais são o fato; os
  -- nominais podem estar incompletos por motivos legítimos (voto secreto).
  sim             int not null default 0,
  nao             int not null default 0,
  abstencao       int not null default 0,

  -- Voto secreto não tem nominal. A regra 6 do contrato de resposta obriga
  -- a expor exclusões estruturais junto de qualquer índice que as sofra —
  -- um ranking de fidelidade partidária que ignore votações secretas está
  -- errado e precisa dizer isso.
  secreta         boolean not null default false,

  source          text not null,
  source_url      text,
  synced_at       timestamptz not null default now(),

  bronze_origem_id uuid references bronze_registro(id),

  constraint votacao_unica_por_casa unique (casa, id_na_fonte),
  constraint votacao_contadores_nao_negativos check (
    sim >= 0 and nao >= 0 and abstencao >= 0
  ),
  constraint votacao_secreta_sem_nominais check (
    -- Enforcement operacional acontece na inserção de voto_nominal (trigger
    -- opcional). Aqui só documentamos a intenção.
    true
  )
);

create index votacao_data_idx  on votacao (data_hora desc);
create index votacao_pl_idx    on votacao (proposicao_id) where proposicao_id is not null;

create table voto_nominal (
  votacao_id           uuid not null references votacao(id) on delete cascade,
  perfil_id            uuid not null references profiles(id),
  voto                 voto_tipo not null,

  -- Partido no momento do voto, não o atual. É a defesa contra o modo de
  -- falha "atributo resolvido no presente" (Tabela 9): voto de 2021 resolve
  -- o partido de 2021. Se o vínculo temporal já tem essa informação, este
  -- campo é redundância deliberada para auditoria e para produtos que leem
  -- diretamente esta tabela sem juntar vinculo_temporal.
  partido_sigla_na_epoca text,

  -- Grau da atribuição do voto a este perfil. A regra 2 do contrato de
  -- resposta obriga a declarar a base quando o vínculo não for direto.
  grau_atribuicao      grau_confianca not null default 'direto',

  synced_at            timestamptz not null default now(),

  primary key (votacao_id, perfil_id)
);


-- -----------------------------------------------------------------------------
-- PRATA — tramitacao (Área D)
-- -----------------------------------------------------------------------------

create table tramitacao (
  id             uuid primary key default gen_random_uuid(),
  proposicao_id  uuid not null references proposicao(id) on delete cascade,
  sequencia      int not null,
  data_hora      timestamptz not null,
  orgao_sigla    text,
  descricao      text not null,
  despacho       text,

  source         text not null,
  source_url     text,
  synced_at      timestamptz not null default now(),

  bronze_origem_id uuid references bronze_registro(id),

  constraint tramitacao_unica_por_seq unique (proposicao_id, sequencia)
);

create index tramitacao_por_data_idx on tramitacao (proposicao_id, data_hora);


-- -----------------------------------------------------------------------------
-- RLS — negar por padrão
-- -----------------------------------------------------------------------------
-- Dado cívico é público. Mesmo assim, a política de leitura pública vive
-- na migration de camada servida (ouro) — aqui expomos só via service role.

alter table bronze_registro enable row level security;
alter table proposicao      enable row level security;
alter table votacao         enable row level security;
alter table voto_nominal    enable row level security;
alter table tramitacao      enable row level security;

comment on schema public is
  'Nada aqui é legível anonimamente. Leitura pública vive em views ouro.';


-- >>> 0003_votacao_nominal.sql >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
-- =============================================================================
-- Aquarius · Onda 1 · Correção: distinguir nominal de secreta em votacao
-- =============================================================================
-- Motivo: leitura do modelo Django do Parlametria (leggo-backend) revelou que
-- o binário secreta/não-secreta que estávamos usando estava incompleto.
-- Existem TRÊS estados legítimos, não dois:
--
--   secreta = true                    → sem nominais (design constitucional)
--   nominal = false, secreta = false  → simbólica ou por acordo, sem nominais
--   nominal = true                    → deve trazer nominais
--
-- Sem esta distinção, uma votação simbólica que chega sem nominais é lida
-- como falha de integridade referencial — e votação simbólica é a MAIORIA
-- das votações da Câmara. Falso positivo em escala.
--
-- Não editamos a migration 0001/0002: o histórico é imutável. Novas
-- correções vêm em migrations novas.
-- =============================================================================

alter table votacao
  add column nominal boolean;

comment on column votacao.nominal is
  'True: nominal, deve ter voto_nominal. False: simbólica/por acordo, sem nominais. Null: não inferido pela fonte (heurística falhou). Ver Parlametria leggo-backend api/model/votacao.py como referência de que este campo é necessário.';

-- Coerência entre secreta e nominal: uma votação secreta não pode ser
-- simultaneamente declarada nominal. Se a fonte publicar essa combinação,
-- o portão da camada prata já recusa; aqui só documentamos a invariante.
alter table votacao
  add constraint votacao_secreta_nao_e_nominal
  check (not (secreta = true and nominal = true));


-- >>> 0004_placar_nao_extraido.sql >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
-- =============================================================================
-- Aquarius · Onda 1 · Placar da votação como "não extraído" (nullable)
-- =============================================================================
-- Motivo: a Metodologia §10 estabelece que o placar declarado vive no TEXTO da
-- descrição da votação (formatos distintos entre plenário e comissão), extraído
-- por parsing. Quando a descrição é narrativa e não traz número, NÃO há placar.
--
-- As colunas sim/nao/abstencao nasceram `int not null default 0` (migration
-- 0002). Contra a fonte real, isso força 0 onde o valor é DESCONHECIDO — e
-- "dado errado é pior que dado ausente" (Metodologia, seção 1). Tornar as
-- colunas nuláveis deixa o banco representar honestamente "não extraído".
--
-- `resultado` idem: votação sem aprovação declarada tem resultado desconhecido;
-- `text not null` obrigava a inventar um rótulo.
--
-- A check `votacao_contadores_nao_negativos` permanece: em Postgres, comparação
-- com NULL resulta em NULL (não viola), então nulo passa e negativo continua
-- barrado. Não editamos 0002 — o histórico é imutável (padrão da 0003).
-- =============================================================================

alter table votacao alter column sim       drop not null;
alter table votacao alter column sim       drop default;
alter table votacao alter column nao       drop not null;
alter table votacao alter column nao       drop default;
alter table votacao alter column abstencao drop not null;
alter table votacao alter column abstencao drop default;
alter table votacao alter column resultado drop not null;

comment on column votacao.sim is
  'Placar declarado (do texto da descrição, §10). NULL = não extraído; nunca 0 por ausência.';
comment on column votacao.nao is
  'Placar declarado (do texto da descrição, §10). NULL = não extraído.';
comment on column votacao.abstencao is
  'Placar declarado (do texto da descrição, §10). NULL = não extraído.';
comment on column votacao.resultado is
  'aprovada | rejeitada, derivado de aprovacao. NULL quando a fonte não declara.';


-- >>> 0005_vinculo_upsert.sql >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
-- =============================================================================
-- Aquarius · Onda 1 · Alvo de upsert idempotente para vinculo_temporal
-- =============================================================================
-- Motivo: a ingestão do histórico de mandatos (§12 D4) reconstrói os vínculos
-- temporais a cada rodada. Sem uma chave de conflito, re-rodar duplicaria os
-- vínculos. A `vinculo_sem_sobreposicao` (exclusion) impede SOBREPOSIÇÃO, mas
-- não é alvo de ON CONFLICT — o upsert precisa de uma constraint única.
--
-- (profile_id, casa, vigencia) identifica um vínculo: a mesma pessoa, na mesma
-- casa, com a mesma vigência exata, é o mesmo mandato — reingerir atualiza,
-- não duplica. daterange tem operador de igualdade btree, então serve a uma
-- unique constraint.
--
-- Não editamos migrations anteriores: correção vem em migration nova (padrão
-- que a 0003 estabeleceu).
-- =============================================================================

alter table vinculo_temporal
  add constraint vinculo_temporal_unico unique (profile_id, casa, vigencia);

comment on constraint vinculo_temporal_unico on vinculo_temporal is
  'Alvo de upsert da ingestão do histórico de mandatos (§12 D4). Reingestão do mesmo período atualiza em vez de duplicar.';


-- >>> 0006_camada_ouro.sql >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
-- =============================================================================
-- Aquarius · Onda 1 · Camada OURO — a projeção servida (Metodologia §3.1)
-- =============================================================================
-- A terceira camada do pipeline. Bronze é o cru imutável; prata é o tratado e
-- qualificado; OURO é "o modelo consumível pelo oráculo, com rótulos de
-- proveniência, completude e frescor embutidos". É esta camada — e SÓ ela — que
-- o app público e o Prometeus leem. Nada é consultado ao vivo na fonte.
--
-- Implementada como VIEWS sobre a prata. Duas decisões deliberadas:
--
--   1. DUAS FRONTEIRAS DE PII (Metodologia §3.5). Nome civil, data de nascimento
--      e naturalidade "permanecem restritos à camada interna de resolução, sem
--      integrar respostas". RLS é por LINHA, não por coluna — não consegue
--      esconder uma coluna. Então a fronteira é a VIEW: ela seleciona apenas as
--      colunas públicas, e a PII simplesmente não é projetada. Toda view aqui é
--      auditável por inspeção: se uma coluna de PII não aparece no SELECT, ela
--      não vaza. É a razão de a camada servida ser uma projeção curada, não a
--      tabela crua.
--
--   2. VIEW COMO PORTA DE LEITURA PÚBLICA. As tabelas de prata têm RLS ligada e
--      SEM policy — ou seja, negam leitura a quem não é service role. As views
--      abaixo rodam com o privilégio do dono (comportamento padrão, "security
--      definer") e recebem GRANT SELECT para `anon` e `authenticated`. Assim o
--      público lê exatamente as colunas curadas, e nunca as tabelas cruas.
--      A ingestão (service role) continua escrevendo nas tabelas normalmente.
--
-- Proveniência + frescor: toda view carrega source/source_url/synced_at. O
-- `synced_at` é o frescor — a última vez que a fonte foi relida para aquela linha.
--
-- Correção vem em migration nova (padrão da 0003). Este arquivo não altera nada
-- da prata; só projeta.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- parlamentar_publico — perfil de parlamentar, SEM PII
-- -----------------------------------------------------------------------------
-- Partido/UF são resolvidos NA DATA DE HOJE: o vínculo temporal vigente agora
-- (§4, "resolver na data do fato"). Para o partido de um voto antigo, use
-- `voto_nominal_publico.partido_sigla_na_epoca`, não este.
create view parlamentar_publico as
select
  p.id,
  p.nome,                                   -- nome parlamentar (de urna), público
  p.slug,
  p.foto_url,
  p.ativo,
  vt.uf                                      as uf_atual,
  vt.legislatura,
  vt.ocupacao                                as ocupacao_atual,
  coalesce(pa.sigla_atual, vt.partido_sigla_fonte) as partido_sigla_atual,
  pa.id                                      as partido_id,
  -- Proveniência e frescor
  p.source, p.source_url, p.synced_at
from profiles p
left join lateral (
  select v.*
  from vinculo_temporal v
  where v.profile_id = p.id
    and v.casa = 'camara'
    and v.vigencia @> current_date          -- o vínculo vigente hoje
  order by lower(v.vigencia) desc
  limit 1
) vt on true
left join partido pa on pa.id = vt.partido_id
where p.tipo = 'parlamentar' and p.ativo;
-- NB: PII de `profiles` (nome_civil, data_nascimento, naturalidade_*) NÃO é
-- projetada — de propósito (§3.5).


-- -----------------------------------------------------------------------------
-- partido_publico — perfil de partido canônico
-- -----------------------------------------------------------------------------
create view partido_publico as
select
  pf.id,
  pf.nome,
  pf.slug,
  pf.foto_url,
  pf.ativo,
  pa.sigla_atual,
  pa.nome_atual,
  pa.numero_urna,
  pf.source, pf.source_url, pf.synced_at
from profiles pf
join partido pa on pa.profile_id = pf.id
where pf.tipo = 'partido';


-- -----------------------------------------------------------------------------
-- proposicao_publica — projetos de lei e afins
-- -----------------------------------------------------------------------------
create view proposicao_publica as
select
  id,
  casa_origem,
  identificador,
  tipo,
  numero,
  ano,
  ementa,
  tema,
  situacao,
  data_apresentacao,
  inteiro_teor_url,
  inteiro_teor_tem_texto,
  tem_resumo_ia,
  source, source_url, synced_at
from proposicao;


-- -----------------------------------------------------------------------------
-- votacao_publica — votação com a matéria já resolvida
-- -----------------------------------------------------------------------------
-- Placar (sim/nao/abstencao) pode ser NULL quando ainda não extraído do texto
-- (§10, V4) — NULL é "não extraído", nunca zero. `nominal`/`secreta` indicam a
-- completude esperada dos votos individuais.
create view votacao_publica as
select
  vo.id,
  vo.casa,
  vo.data_hora,
  vo.titulo,
  vo.resultado,
  vo.sim,
  vo.nao,
  vo.abstencao,
  vo.secreta,
  vo.nominal,
  pr.id            as proposicao_id,
  pr.identificador as proposicao_identificador,
  pr.ementa        as proposicao_ementa,
  vo.source, vo.source_url, vo.synced_at
from votacao vo
left join proposicao pr on pr.id = vo.proposicao_id;


-- -----------------------------------------------------------------------------
-- voto_nominal_publico — como cada parlamentar votou
-- -----------------------------------------------------------------------------
-- Aqui o partido é o DA ÉPOCA do voto (§4), não o atual — vem do snapshot que a
-- fonte fez no momento. A presidência (Artigo 17) não está aqui: não é posição.
create view voto_nominal_publico as
select
  vn.votacao_id,
  vo.data_hora        as votacao_data_hora,
  pf.id               as parlamentar_id,
  pf.nome             as parlamentar_nome,
  pf.slug             as parlamentar_slug,
  vn.voto,
  vn.partido_sigla_na_epoca,
  vn.grau_atribuicao,
  vn.synced_at
from voto_nominal vn
join votacao vo  on vo.id = vn.votacao_id
join profiles pf on pf.id = vn.perfil_id;


-- -----------------------------------------------------------------------------
-- tramitacao_publica — a cadeia de despachos de cada matéria
-- -----------------------------------------------------------------------------
-- `despacho` é texto de parte interessada (secretaria/relator, §11) — o
-- consumidor jamais o lê como narração neutra.
create view tramitacao_publica as
select
  id,
  proposicao_id,
  sequencia,
  data_hora,
  orgao_sigla,
  descricao,
  despacho,
  source, source_url, synced_at
from tramitacao;


-- -----------------------------------------------------------------------------
-- Leitura pública: só as views curadas, nunca as tabelas de prata.
-- -----------------------------------------------------------------------------
grant select on
  parlamentar_publico,
  partido_publico,
  proposicao_publica,
  votacao_publica,
  voto_nominal_publico,
  tramitacao_publica
to anon, authenticated;

comment on view parlamentar_publico is
  'Camada ouro. Perfil de parlamentar SEM PII (§3.5); partido/UF na data de hoje (§4).';
comment on view voto_nominal_publico is
  'Camada ouro. Voto individual com o partido DA ÉPOCA (§4), não o atual.';


-- >>> 0007_ouro_coletivos.sql >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
-- =============================================================================
-- Aquarius · Onda 1 · Camada ouro — perfis coletivos (comissão, frente)
-- =============================================================================
-- Estende a camada ouro (0006) para os perfis coletivos populados pelo coletor
-- `coletivos.py`. Mesma disciplina: projeção curada sobre `profiles`, com
-- proveniência/frescor, servida a anon/authenticated. Perfis coletivos não têm
-- PII (não são pessoa natural), mas seguem a regra de ler só do ouro.
--
-- Correção vem em migration nova (padrão da 0003).
-- =============================================================================

create view comissao_publica as
select
  id, nome, sigla, slug, ativo,
  source, source_url, synced_at
from profiles
where tipo = 'comissao' and ativo;

create view frente_publica as
select
  id, nome, slug, ativo,
  source, source_url, synced_at
from profiles
where tipo = 'frente' and ativo;

grant select on comissao_publica, frente_publica to anon, authenticated;

comment on view comissao_publica is
  'Camada ouro. Comissões (perfil polimórfico tipo=comissao).';
comment on view frente_publica is
  'Camada ouro. Frentes parlamentares (perfil polimórfico tipo=frente).';


-- >>> 0008_despesas_ceap.sql >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
-- =============================================================================
-- Aquarius · Onda 1 · Área A — Despesas / Cota Parlamentar (CEAP), §8
-- =============================================================================
-- Prata da cota parlamentar: cada linha é um documento de ressarcimento de um
-- parlamentar. Dado público de transparência (a fonte publica fornecedor e
-- valor abertamente) — não há PII do parlamentar aqui.
--
-- Identidade interna (§5.2): valor do documento menos a glosa é igual ao
-- líquido. O portão da prata já quarentena o que viola; o CHECK abaixo é
-- defesa em profundidade (numeric é exato, então não há risco de ruído por
-- ponto flutuante). Aprovados pelo portão sempre passam o check.
-- =============================================================================

create table despesa (
  id             uuid primary key default gen_random_uuid(),
  perfil_id      uuid not null references profiles(id) on delete cascade,

  ano            int not null,
  mes            int not null,

  tipo_despesa   text,
  tipo_documento text,
  cod_documento  bigint,          -- 0 na fonte = sem documento → gravado como null
  cod_lote       bigint,
  num_documento  text,
  num_ressarcimento text,
  parcela        int,
  data_documento date,

  valor_documento numeric(14,2),
  valor_glosa     numeric(14,2),
  valor_liquido   numeric(14,2),

  fornecedor_nome     text,
  fornecedor_cnpj_cpf text,       -- público (transparência da CEAP)
  url_documento       text,

  source         text not null,
  source_url     text,
  synced_at      timestamptz not null default now(),

  -- §5.2: documento - glosa = líquido (defesa em profundidade)
  constraint despesa_identidade_valor check (
    valor_documento is null or valor_glosa is null or valor_liquido is null
    or valor_documento - valor_glosa = valor_liquido
  ),
  -- Idempotência: cod_documento é o id global do documento na Câmara; parcela
  -- distingue parcelas. cod_documento null (sem documento) não colide (nulls
  -- são distintos em unique).
  constraint despesa_unica unique (perfil_id, cod_documento, parcela)
);

create index despesa_perfil_idx    on despesa (perfil_id, ano, mes);
create index despesa_fornecedor_idx on despesa (fornecedor_cnpj_cpf);

alter table despesa enable row level security;

comment on table despesa is
  'Cota parlamentar (CEAP), Área A §8. Identidade §5.2: documento - glosa = líquido.';


-- -----------------------------------------------------------------------------
-- Camada ouro — despesa_publica
-- -----------------------------------------------------------------------------
create view despesa_publica as
select
  d.id,
  d.perfil_id,
  pf.nome  as parlamentar_nome,
  pf.slug  as parlamentar_slug,
  d.ano,
  d.mes,
  d.tipo_despesa,
  d.data_documento,
  d.valor_documento,
  d.valor_glosa,
  d.valor_liquido,
  d.fornecedor_nome,
  d.fornecedor_cnpj_cpf,
  d.url_documento,
  d.source, d.source_url, d.synced_at
from despesa d
join profiles pf on pf.id = d.perfil_id;

grant select on despesa_publica to anon, authenticated;

comment on view despesa_publica is
  'Camada ouro. Despesas da cota parlamentar (CEAP) por parlamentar (§8).';


commit;
