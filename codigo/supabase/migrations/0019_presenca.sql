-- =============================================================================
-- Aquarius · Onda 1 · Presença — Área E (frequência em sessões do Plenário)
-- =============================================================================
-- A última área de atividade sem coletor. Presença = comparecimento dos
-- parlamentares às SESSÕES DELIBERATIVAS do Plenário (§11/§4).
--
-- Fonte (Câmara, verificada ao vivo 2026-09-22): `/eventos?codTipoEvento=110,204`
-- (tipos "Sessão Deliberativa") filtrando `orgao='PLEN'` → a lista de sessões;
-- `/eventos/{id}/deputados` → os PRESENTES em cada sessão (varia 465..489 de 513,
-- é presença real). AUSENTE = fora da lista. A fonte NÃO traz "ausência
-- justificada" — `justificadas` fica null (dado ausente é melhor que inventado,
-- §1); entra num passe futuro de outra fonte.
--
-- Bicameral: só a CÂMARA neste passe (a fonte do Senado exige pesquisa à parte);
-- a tabela já é `casa`-agnóstica para o Senado entrar depois sem migration nova.
--
-- Identidade resolvida na DATA da sessão (§4): o id do deputado na fonte resolve
-- a PESSOA (perfil) via id_externo; o partido-da-época sai do vínculo, como nos
-- votos. Ex-parlamentares entram normalmente (perfil inativo é fato, não some).
-- =============================================================================

-- Sessão deliberativa (portadora de presença). Uma tabela para as duas casas.
create table sessao (
  id          uuid primary key default gen_random_uuid(),
  casa        casa_legislativa not null,
  id_fonte    text not null,        -- id do evento/sessão na fonte

  tipo        text,                 -- "Sessão Deliberativa"
  data_hora   timestamp,            -- hora de parede de Brasília (como `evento`)
  orgao_sigla text,                 -- 'PLEN' (plenário)

  source      text not null,
  source_url  text,
  synced_at   timestamptz not null default now(),
  criado_em   timestamptz not null default now(),

  constraint sessao_unica unique (casa, id_fonte)
);

create index sessao_data_idx on sessao (data_hora desc);

comment on table sessao is
  'Sessões deliberativas do Plenário (portadoras de presença). Bicameral por '
  '`casa`; Área E. data_hora sem fuso = hora de parede de Brasília.';


-- Presença: um registro por parlamentar PRESENTE numa sessão (a fonte lista os
-- presentes; ausência = ausência de linha). `presente` fica explícito para o dia
-- em que uma fonte trouxer ausências/justificativas na mesma tabela.
create table presenca (
  id         uuid primary key default gen_random_uuid(),
  sessao_id  uuid not null references sessao(id) on delete cascade,
  perfil_id  uuid not null references profiles(id),
  presente   boolean not null default true,

  source     text not null,
  source_url text,
  synced_at  timestamptz not null default now(),

  constraint presenca_unica unique (sessao_id, perfil_id)
);

create index presenca_perfil_idx on presenca (perfil_id);
create index presenca_sessao_idx on presenca (sessao_id);

comment on table presenca is
  'Comparecimento de um parlamentar a uma sessão (linha = presente). Ausência = '
  'sem linha; ausência justificada não vem desta fonte (§1).';


-- -----------------------------------------------------------------------------
-- presenca_publica — camada ouro: frequência agregada por parlamentar
-- -----------------------------------------------------------------------------
-- `convocadas` = sessões da casa realizadas DENTRO do mandato do parlamentar
-- (vínculo temporal §4) — assim o suplente que assumiu no meio não é penalizado
-- por sessões anteriores à posse. `percentual_presenca` = presenças/convocadas.
-- `justificadas` é null (não disponível nesta fonte). É view de FATO (não filtra
-- por vigência): o Prometeus lê a frequência de ex-parlamentares também.
create view presenca_publica as
with pres as (
  select pr.perfil_id, s.casa,
         count(*)               as presencas,
         max(pr.synced_at)      as synced_at
  from presenca pr
  join sessao s on s.id = pr.sessao_id
  where pr.presente
  group by pr.perfil_id, s.casa
),
conv as (
  select vt.profile_id as perfil_id, vt.casa,
         count(distinct s.id) as convocadas
  from vinculo_temporal vt
  join sessao s
    on s.casa = vt.casa
   and s.data_hora is not null
   and s.data_hora::date <@ vt.vigencia
  group by vt.profile_id, vt.casa
)
select
  pf.id    as parlamentar_id,
  pf.nome  as parlamentar_nome,
  pf.slug  as parlamentar_slug,
  c.casa,
  coalesce(p.presencas, 0) as presencas,
  c.convocadas,
  null::int                as justificadas,   -- não disponível nesta fonte (§1)
  case when c.convocadas > 0
       then round(100.0 * coalesce(p.presencas, 0) / c.convocadas, 1)
       else null end       as percentual_presenca,
  'camara.presenca'                            as source,
  'https://dadosabertos.camara.leg.br/api/v2'  as source_url,
  coalesce(p.synced_at, now())                 as synced_at
from conv c
join profiles pf on pf.id = c.perfil_id
left join pres p on p.perfil_id = c.perfil_id and p.casa = c.casa
where pf.tipo = 'parlamentar' and c.convocadas > 0;

grant select on presenca_publica to anon, authenticated;

comment on view presenca_publica is
  'Camada ouro. Frequência por parlamentar: presenças/convocadas/percentual em '
  'sessões deliberativas do Plenário. Convocadas ajustadas ao mandato (§4). '
  'justificadas=null (fora desta fonte). View de fato: inclui ex-parlamentares.';
