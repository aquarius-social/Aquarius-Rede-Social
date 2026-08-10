-- 0017: RBAC do console admin — membros e papéis + helper is_admin().
-- Escrita só pelo service_role (gestão de equipe via server action privilegiada).
-- is_admin() serve de guarda para a RLS das tabelas privilegiadas futuras
-- (editorial, audit_log, feature_flags, etc.).

create table if not exists admin_roles (
  user_id    uuid primary key references auth.users(id) on delete cascade,
  papel      text not null default 'operador'
             check (papel in ('superadmin','editor_chefe','editor','moderador',
                              'analista_daas','auditor','operador','visualizador')),
  criado_em  timestamptz not null default now()
);

alter table admin_roles enable row level security;

-- Cada admin lê a PRÓPRIA linha (o console usa isso para saber que é admin e o papel).
drop policy if exists admin_le_propria on admin_roles;
create policy admin_le_propria on admin_roles
  for select using (user_id = auth.uid());
-- Sem policy de insert/update/delete → negado a anon/authenticated; escrita via service_role.

create or replace function is_admin() returns boolean
  language sql stable security definer set search_path = public as $$
  select exists (select 1 from admin_roles where user_id = auth.uid());
$$;

grant select on admin_roles to authenticated;
grant execute on function is_admin() to authenticated, anon;

comment on table admin_roles is
  'Membros do console admin e seus papeis (RBAC). Escrita via service_role. '
  'is_admin() e guarda para a RLS das tabelas privilegiadas futuras.';
