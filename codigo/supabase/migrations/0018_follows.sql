-- 0018: grafo de "seguir" do usuário final — parlamentares, partidos, comissões,
-- frentes e temas. São dados do USUÁRIO (não cívicos): a RLS restringe cada linha
-- ao seu dono (o app escreve como `authenticated`, não via service_role).
-- Unifica o que antes vivia solto em user_metadata.prefs (temas/partidos).

create table if not exists follows (
  user_id    uuid        not null references auth.users(id) on delete cascade,
  tipo       text        not null
             check (tipo in ('parlamentar','partido','comissao','frente','tema')),
  ref_id     text        not null,   -- id/uuid da entidade, ou sigla (partido) ou slug (tema)
  rotulo     text,                   -- snapshot de exibição (nome/sigla) p/ listar sem join
  meta       jsonb,                  -- extras opcionais de exibição (ex.: {sigla, uf})
  criado_em  timestamptz not null default now(),
  primary key (user_id, tipo, ref_id)
);

alter table follows enable row level security;

-- Cada usuário só enxerga e mexe nos próprios follows.
drop policy if exists follows_le_proprios on follows;
create policy follows_le_proprios on follows
  for select using (user_id = auth.uid());

drop policy if exists follows_insere_proprios on follows;
create policy follows_insere_proprios on follows
  for insert with check (user_id = auth.uid());

drop policy if exists follows_atualiza_proprios on follows;
create policy follows_atualiza_proprios on follows
  for update using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists follows_apaga_proprios on follows;
create policy follows_apaga_proprios on follows
  for delete using (user_id = auth.uid());

create index if not exists follows_user_tipo_idx on follows (user_id, tipo);

grant select, insert, update, delete on follows to authenticated;

comment on table follows is
  'Grafo de "seguir" do usuario final (parlamentar/partido/comissao/frente/tema). '
  'RLS por dono. Fonte unica das preferencias de acompanhamento do app.';
