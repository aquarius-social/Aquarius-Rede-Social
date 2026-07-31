-- =============================================================================
-- Aquarius · Onda 1 · Área F — Emendas parlamentares (execução orçamentária, §13)
-- =============================================================================
-- O DINHEIRO das emendas NÃO está na API da Câmara — vive na execução
-- orçamentária federal, cuja fonte é a API de Emendas do Portal da Transparência
-- (exige chave pessoal `chave-api-dados`). Campos verificados contra o dado real
-- baixado (emendas_2024.json, 6990 registros — bate com a §13).
--
-- DISCIPLINAS DA §13 gravadas na estrutura:
--   - ESTÁGIOS ORÇAMENTÁRIOS separados e NUNCA somados: empenhado, liquidado,
--     pago (e os restos). Colunas próprias; identidade de ordem em §5.2
--     (empenhado ≥ liquidado ≥ pago) verificada no portão.
--   - EMENDA AO ORÇAMENTO ≠ emenda ao texto (proposição acessória). Esta tabela
--     é só a orçamentária.
--   - AUTORIA pelo identificador embutido no `codigoEmenda` (§6.3): guarda-se
--     `autor_codigo` (o meio do código) para resolver ao perfil via id_externo
--     (sistema='autor_orcamentario'). `autor_profile_id` fica null enquanto a
--     tabela de correspondência (curadoria, mapa_autores) não for carregada —
--     furo conhecido declarado, não invenção.
-- =============================================================================

create table emenda (
  id                    uuid primary key default gen_random_uuid(),

  -- Código da emenda na fonte. Único por exercício; contém o autor embutido.
  codigo_emenda         text not null,
  ano                   int not null,
  tipo                  text,
  numero                text,

  -- Autoria (§6.3). Nome como veio da fonte + código embutido; perfil resolvido
  -- depois por curadoria (id_externo sistema='autor_orcamentario').
  autor_nome            text,
  autor_codigo          text,
  autor_profile_id      uuid references profiles(id),

  localidade_gasto      text,
  funcao                text,
  subfuncao             text,

  -- Estágios orçamentários. NUNCA some entre si (§13, regra de resposta).
  valor_empenhado       numeric(18,2),
  valor_liquidado       numeric(18,2),
  valor_pago            numeric(18,2),
  valor_resto_inscrito  numeric(18,2),
  valor_resto_cancelado numeric(18,2),
  valor_resto_pago      numeric(18,2),

  -- Proveniência (§3.1).
  source                text not null,
  source_url            text,
  synced_at             timestamptz not null default now(),

  bronze_origem_id      uuid references bronze_registro(id),

  constraint emenda_unica unique (codigo_emenda)
);

create index emenda_ano_idx    on emenda (ano);
create index emenda_autor_idx  on emenda (autor_profile_id) where autor_profile_id is not null;
create index emenda_funcao_idx on emenda (funcao);

comment on table emenda is
  'Execução orçamentária das emendas parlamentares (Área F, §13). Estágios jamais somados.';
comment on column emenda.autor_profile_id is
  'Perfil do autor. Null até a curadoria carregar o mapa (id_externo autor_orcamentario, §6.3).';

alter table emenda enable row level security;

-- -----------------------------------------------------------------------------
-- Camada ouro — emenda_publica
-- -----------------------------------------------------------------------------
create view emenda_publica as
select
  id, codigo_emenda, ano, tipo, numero,
  autor_nome, autor_profile_id,
  localidade_gasto, funcao, subfuncao,
  valor_empenhado, valor_liquidado, valor_pago,
  valor_resto_inscrito, valor_resto_cancelado, valor_resto_pago,
  source, source_url, synced_at
from emenda;

grant select on emenda_publica to anon, authenticated;

comment on view emenda_publica is
  'Camada ouro. Emendas por estágio orçamentário — o consumidor jamais soma estágios (§13).';
