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
