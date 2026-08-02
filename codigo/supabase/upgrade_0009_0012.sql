-- =============================================================================
-- Aquarius · upgrade_0009_0012.sql — INCREMENTAL para banco que já tem 0001-0008
-- =============================================================================
-- Aplica SÓ as migrations novas (emendas, view bicameral, discursos, eventos),
-- na ordem, numa transação. Cole no SQL Editor do Supabase e rode UMA vez.
-- Se o banco ainda NÃO tem schema nenhum, use deploy_all.sql em vez deste.
-- =============================================================================

begin;



-- >>> 0009_emendas.sql >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
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


-- >>> 0010_senado.sql >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
-- =============================================================================
-- Aquarius · Onda 1 · Senado — parlamentar_publico bicameral (§17)
-- =============================================================================
-- Contexto: o coletor de senadores (Área I) grava senadores na MESMA tabela
-- polimórfica `profiles` (tipo='parlamentar'), com `id_externo` (sistema='senado')
-- e `vinculo_temporal` (casa='senado'). Nenhuma tabela nova é necessária — a
-- fundação da Onda 0 já previa as duas casas (enums `casa_legislativa` e
-- `sistema_externo` incluem 'senado').
--
-- O que PRECISA mudar: a view ouro `parlamentar_publico` (migration 0006)
-- resolvia o vínculo vigente com `v.casa = 'camara'` fixo — um senador apareceria
-- SEM partido/UF. Aqui o vínculo vigente passa a ser o de QUALQUER casa (uma
-- pessoa ocupa uma cadeira por vez; o vínculo vigente hoje determina a casa
-- atual), e projeta-se `casa_atual` para o app distinguir deputado de senador.
--
-- Correção por migration NOVA (CLAUDE.md, regra 5): não se edita a 0006.
-- =============================================================================

-- CREATE OR REPLACE preserva as colunas existentes (mesma ordem/nome/tipo) e só
-- ACRESCENTA `casa_atual` ao fim — exigência do Postgres para replace de view.
create or replace view parlamentar_publico as
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
  p.source, p.source_url, p.synced_at,
  vt.casa                                    as casa_atual   -- << nova coluna
from profiles p
left join lateral (
  select v.*
  from vinculo_temporal v
  where v.profile_id = p.id
    and v.vigencia @> current_date          -- o vínculo vigente hoje, qualquer casa
  order by lower(v.vigencia) desc
  limit 1
) vt on true
left join partido pa on pa.id = vt.partido_id
where p.tipo = 'parlamentar' and p.ativo;

comment on view parlamentar_publico is
  'Camada ouro. Perfil de parlamentar SEM PII (§3.5); partido/UF/casa na data de '
  'hoje (§4). Bicameral: `casa_atual` distingue câmara de senado (§17).';


-- >>> 0011_discursos.sql >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
-- =============================================================================
-- Aquarius · Onda 1 · Discursos — bicameral (Câmara + Senado)
-- =============================================================================
-- Uma tabela `discurso` serve as DUAS casas (a coluna `casa` distingue). O
-- discurso da Câmara não tem id próprio na fonte — sua identidade é o par
-- (deputado, dataHoraInicio), gravado como `id_fonte` composto; o do Senado tem
-- `CodigoPronunciamento`. A unicidade é (casa, id_fonte).
--
-- Princípio inegociável (CLAUDE.md): todo item servido cita fonte oficial —
-- `url_texto` é o link do inteiro teor na fonte, e `source`/`source_url`/
-- `synced_at` são a proveniência §3.1. A transcrição integral NÃO é copiada
-- (pode ter milhares de caracteres); guarda-se o resumo + a flag `tem_transcricao`
-- + a URL, no mesmo espírito de `proposicao.inteiro_teor_url` (0002).
--
-- PII (§3.5): a view ouro projeta só o nome PARLAMENTAR (público), nunca a PII
-- de `profiles`.
-- =============================================================================

create table discurso (
  id              uuid primary key default gen_random_uuid(),
  -- Quem discursou. Resolvido por id_externo (camara/senado) antes de gravar
  -- (§6, integridade referencial) — nada entra ancorado só num id de fonte.
  profile_id      uuid not null references profiles(id) on delete cascade,
  casa            casa_legislativa not null,
  -- Câmara: '{deputado}:{dataHoraInicio}' (o discurso não tem id próprio, como
  -- o voto). Senado: CodigoPronunciamento.
  id_fonte        text not null,

  data            date,
  tipo            text,                 -- tipoDiscurso / TipoUsoPalavra.Descricao
  sumario         text,                 -- sumario / TextoResumo
  keywords        text,                 -- keywords / Indexacao (string da fonte)
  url_texto       text,                 -- inteiro teor na fonte (citação obrigatória)
  url_video       text,                 -- só Câmara
  url_audio       text,
  tem_transcricao boolean not null default false,

  source          text not null,
  source_url      text,
  synced_at       timestamptz not null default now(),
  criado_em       timestamptz not null default now(),

  constraint discurso_unico unique (casa, id_fonte)
);

create index discurso_profile_idx on discurso (profile_id);
create index discurso_data_idx    on discurso (data desc);

comment on table discurso is
  'Discursos/pronunciamentos das duas casas (Área G, §13). Identidade composta na '
  'Câmara (deputado:dataHoraInicio); CodigoPronunciamento no Senado.';


-- -----------------------------------------------------------------------------
-- discurso_publico — camada ouro, SEM PII
-- -----------------------------------------------------------------------------
create view discurso_publico as
select
  d.id,
  d.casa,
  d.data,
  d.tipo,
  d.sumario,
  d.keywords,
  d.url_texto,
  d.url_video,
  d.url_audio,
  d.tem_transcricao,
  p.id    as parlamentar_id,
  p.nome  as parlamentar_nome,          -- nome parlamentar (de urna), público
  p.slug  as parlamentar_slug,
  d.source, d.source_url, d.synced_at
from discurso d
join profiles p on p.id = d.profile_id
where p.tipo = 'parlamentar';

grant select on discurso_publico to anon, authenticated;

comment on view discurso_publico is
  'Camada ouro. Discursos das duas casas por parlamentar, SEM PII (§3.5). '
  'url_texto é a citação da fonte oficial.';


-- >>> 0012_eventos.sql >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
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


commit;
