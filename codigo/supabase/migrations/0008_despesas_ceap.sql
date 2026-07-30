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
