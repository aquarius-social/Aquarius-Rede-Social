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
