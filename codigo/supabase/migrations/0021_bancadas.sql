-- =============================================================================
-- Aquarius · §6.3/§13 — bancadas estaduais como PERFIL COLETIVO (emenda de bancada, RP7)
-- =============================================================================
-- Depende da 0020 (valor de enum 'bancada' já commitado numa migration anterior).
--
-- INVARIANTE ANTI-DUPLICIDADE (o ponto crítico): cada emenda tem UM dono só
-- (autor_profile_id) — uma pessoa OU uma bancada, conjuntos DISJUNTOS. A emenda de
-- bancada pertence à bancada e JAMAIS é somada ao total individual de um membro.
-- Na página do membro ela aparece por JOIN (composição por UF) — exibição, não cópia.
--
-- Idempotente: ON CONFLICT DO NOTHING / WHERE ... IS NULL / CREATE OR REPLACE.
-- =============================================================================

-- 1) Um perfil por bancada estadual (26 estados + DF).
insert into profiles (tipo, nome, sigla, slug, source, source_url, ativo)
select 'bancada'::profile_tipo, v.nome, v.uf, v.slug,
       'transparencia.emendas', 'https://api.portaldatransparencia.gov.br/api-de-dados', true
from (values
  ('Bancada do Acre','AC','bancada-ac'),
  ('Bancada de Alagoas','AL','bancada-al'),
  ('Bancada do Amazonas','AM','bancada-am'),
  ('Bancada do Amapá','AP','bancada-ap'),
  ('Bancada da Bahia','BA','bancada-ba'),
  ('Bancada do Ceará','CE','bancada-ce'),
  ('Bancada do Distrito Federal','DF','bancada-df'),
  ('Bancada do Espírito Santo','ES','bancada-es'),
  ('Bancada de Goiás','GO','bancada-go'),
  ('Bancada do Maranhão','MA','bancada-ma'),
  ('Bancada de Mato Grosso','MT','bancada-mt'),
  ('Bancada de Mato Grosso do Sul','MS','bancada-ms'),
  ('Bancada de Minas Gerais','MG','bancada-mg'),
  ('Bancada do Pará','PA','bancada-pa'),
  ('Bancada da Paraíba','PB','bancada-pb'),
  ('Bancada do Paraná','PR','bancada-pr'),
  ('Bancada de Pernambuco','PE','bancada-pe'),
  ('Bancada do Piauí','PI','bancada-pi'),
  ('Bancada do Rio de Janeiro','RJ','bancada-rj'),
  ('Bancada do Rio Grande do Norte','RN','bancada-rn'),
  ('Bancada do Rio Grande do Sul','RS','bancada-rs'),
  ('Bancada de Rondônia','RO','bancada-ro'),
  ('Bancada de Roraima','RR','bancada-rr'),
  ('Bancada de São Paulo','SP','bancada-sp'),
  ('Bancada de Santa Catarina','SC','bancada-sc'),
  ('Bancada de Sergipe','SE','bancada-se'),
  ('Bancada do Tocantins','TO','bancada-to')
) as v(nome, uf, slug)
on conflict (slug) do nothing;

-- 2) Ligação código de autor orçamentário (71xx) -> perfil da bancada.
--    metodo='fonte_direta' + grau='direto': o código 71xx identifica a bancada de
--    forma determinística (não é casamento de nome). Passa em id_externo_grau_coerente.
insert into id_externo (profile_id, sistema, identificador, metodo, grau, sinais, versao_regra, pendente_conferencia)
select p.id, 'autor_orcamentario', m.cod, 'fonte_direta', 'direto',
       ARRAY['codigo_orcamentario'], 'transparencia.v1', false
from (values
  ('7102','bancada-ac'),('7103','bancada-al'),('7104','bancada-am'),('7105','bancada-ap'),
  ('7106','bancada-ba'),('7107','bancada-ce'),('7108','bancada-df'),('7109','bancada-es'),
  ('7110','bancada-go'),('7111','bancada-ma'),('7112','bancada-mt'),('7113','bancada-ms'),
  ('7114','bancada-mg'),('7115','bancada-pa'),('7116','bancada-pb'),('7117','bancada-pr'),
  ('7118','bancada-pe'),('7119','bancada-pi'),('7120','bancada-rj'),('7121','bancada-rn'),
  ('7122','bancada-rs'),('7123','bancada-ro'),('7124','bancada-rr'),('7125','bancada-sp'),
  ('7126','bancada-sc'),('7127','bancada-se'),('7128','bancada-to')
) as m(cod, slug)
join profiles p on p.slug = m.slug
on conflict (sistema, identificador) do nothing;

-- 3) Backfill: emendas de bancada sem autor -> a bancada (só linhas NULL, preserva disjunção).
update emenda e
set autor_profile_id = x.profile_id
from id_externo x
where x.sistema = 'autor_orcamentario' and x.identificador = e.autor_codigo
  and x.profile_id is not null
  and e.autor_profile_id is null
  and e.autor_codigo between '7102' and '7128';

-- 4) Camada ouro — bancada e composição.
create or replace view bancada_publica as
select p.id, p.nome, p.sigla as uf, p.slug, p.ativo, p.source, p.source_url, p.synced_at
from profiles p
where p.tipo = 'bancada';

-- Composição ATUAL (vigente hoje), deputados E senadores da UF, sem licenciados.
-- DISTINCT ON (bancada, membro): um membro = UMA linha (evita fan-out de vínculos).
-- SEM colunas de valor: a roster não pode ser caminho de soma de dinheiro.
create or replace view bancada_membro_publico as
select distinct on (b.id, p.id)
  b.id   as bancada_id,
  b.sigla as uf,
  b.slug as bancada_slug,
  p.id   as profile_id,
  p.nome,
  p.slug,
  vt.casa,
  vt.ocupacao
from profiles b
join vinculo_temporal vt
  on vt.uf = b.sigla
 and vt.vigencia @> current_date
 and vt.casa in ('camara','senado')
 and vt.ocupacao in ('titular','suplente_em_exercicio')
join profiles p
  on p.id = vt.profile_id and p.tipo = 'parlamentar'
where b.tipo = 'bancada'
order by b.id, p.id, vt.ocupacao;

grant select on bancada_publica to anon, authenticated;
grant select on bancada_membro_publico to anon, authenticated;

comment on view bancada_publica is
  'Camada ouro. Perfis de bancada estadual (autoria coletiva de emenda, RP7). Emendas via emenda_publica WHERE autor_profile_id = id da bancada.';
comment on view bancada_membro_publico is
  'Composicao ATUAL da bancada (vigente hoje; sem licenciados; dep+senadores da UF). SEM colunas de dinheiro por design (anti-dupla-contagem): a emenda de bancada nunca entra no total individual do membro. Para emenda por membro-na-epoca, juntar pelo ano da emenda dentro da vigencia, nunca por current_date.';
