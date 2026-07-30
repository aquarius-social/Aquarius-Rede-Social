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
