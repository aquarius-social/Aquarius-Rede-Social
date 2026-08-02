-- =============================================================================
-- Aquarius · Onda 1 · Eventos — agenda legislativa bicameral (Câmara + Senado)
-- =============================================================================
-- Primeira área NOVA (nenhuma casa tinha): a agenda de eventos legislativos —
-- sessões do plenário, reuniões e audiências de comissão. Uma tabela `evento`
-- serve as duas casas (`casa`), como proposicao/votacao/discurso.
--
-- Fontes: Câmara `/eventos?dataInicio&dataFim`; Senado `/comissao/agenda/mes/
-- {YYYYMM}` (agenda de reuniões das comissões). Estruturas diferentes, MESMA
-- prata (o coletor de cada casa normaliza).
--
-- `data_hora_*` é `timestamp` SEM fuso (não timestamptz): as fontes entregam a
-- hora LOCAL de Brasília sem offset, e para uma AGENDA a hora de parede é o que
-- importa — convertê-la para UTC deslocaria o evento em 3h. Decisão deliberada
-- desta tabela nova.
--
-- `orgao_profile_id` liga ao perfil da comissão (tipo='comissao') quando o slug
-- reconstruído casa; plenário e órgãos não-ingeridos ficam null (honesto).
-- =============================================================================

create table evento (
  id               uuid primary key default gen_random_uuid(),
  casa             casa_legislativa not null,
  id_fonte         text not null,

  tipo             text,             -- descricaoTipo (Câmara) / tipo de reunião (Senado)
  titulo           text,
  data_hora_inicio timestamp,
  data_hora_fim    timestamp,
  situacao         text,             -- Agendada / Realizada / Cancelada

  orgao_sigla      text,
  orgao_nome       text,
  orgao_profile_id uuid references profiles(id),

  local            text,
  url              text,

  source           text not null,
  source_url       text,
  synced_at        timestamptz not null default now(),
  criado_em        timestamptz not null default now(),

  constraint evento_unico unique (casa, id_fonte)
);

create index evento_data_idx  on evento (data_hora_inicio desc);
create index evento_orgao_idx on evento (orgao_profile_id) where orgao_profile_id is not null;

comment on table evento is
  'Agenda legislativa das duas casas (sessões, reuniões, audiências). Área nova, '
  'bicameral por `casa`. data_hora sem fuso = hora de parede de Brasília.';


-- -----------------------------------------------------------------------------
-- evento_publico — camada ouro (sem PII; eventos são públicos)
-- -----------------------------------------------------------------------------
create view evento_publico as
select
  e.id,
  e.casa,
  e.tipo,
  e.titulo,
  e.data_hora_inicio,
  e.data_hora_fim,
  e.situacao,
  e.orgao_sigla,
  e.orgao_nome,
  e.orgao_profile_id,
  e.local,
  e.url,
  e.source, e.source_url, e.synced_at
from evento e;

grant select on evento_publico to anon, authenticated;

comment on view evento_publico is
  'Camada ouro. Agenda legislativa das duas casas, por órgão (§ bicameral).';
