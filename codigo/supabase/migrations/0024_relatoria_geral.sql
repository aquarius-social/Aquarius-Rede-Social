-- =============================================================================
-- Aquarius · §6.3/§13 — Relator-Geral do Orçamento (Emenda de Relator, RP9)
-- =============================================================================
-- Depende da 0023 (valor de enum 'relatoria' já commitado numa migration anterior).
--
-- O QUE É: as "Emendas de Relator" (autor_codigo 8100, ~295, R$19,4 bi em 2020–2022)
-- são o RP9 / "orçamento secreto" — o STF (ADPFs 850/851/854) mandou dar
-- transparência JUSTAMENTE porque não têm autoria pessoal clara: o Relator-Geral
-- as insere distribuindo a pedido de terceiros ocultos.
--
-- MODELO HONESTO (categoria + responsabilidade funcional, sem inflar ninguém):
--   (1) CATEGORIA: um perfil INSTITUCIONAL 'relatoria' ("Relator-Geral do
--       Orçamento") é o DONO das 295 emendas (autor_profile_id). Como as bancadas,
--       NUNCA é somado ao total individual de nenhuma pessoa.
--   (2) RESPONSABILIDADE FORMAL: a tabela `relatoria_geral` liga cada EXERCÍCIO ao
--       relator-geral formal daquele ano (pessoa verificável, com fonte) — é quem
--       "assinou o pacote", exposto como CONTEXTO, JAMAIS como emenda individual
--       dele (o autor_profile_id da emenda continua sendo o perfil institucional).
--   O que fica honestamente AUSENTE: o SOLICITANTE real de cada emenda (o pedinte
--   oculto) — não está na fonte que ingerimos (só em disclosures do SIOP/pós-STF).
--
-- Idempotente: ON CONFLICT DO NOTHING / WHERE ... IS NULL / CREATE OR REPLACE.
-- =============================================================================

-- 1) Perfil INSTITUCIONAL (a função, não uma pessoa).
insert into profiles (tipo, nome, slug, source, source_url, ativo)
values ('relatoria'::profile_tipo, 'Relator-Geral do Orçamento',
        'relator-geral-orcamento',
        'transparencia.emendas',
        'https://api.portaldatransparencia.gov.br/api-de-dados', true)
on conflict (slug) do nothing;

-- 2) Ligação código de autor 8100 -> perfil institucional (determinístico, direto).
insert into id_externo (profile_id, sistema, identificador, metodo, grau, sinais, versao_regra, pendente_conferencia)
select p.id, 'autor_orcamentario', '8100', 'fonte_direta', 'direto',
       ARRAY['codigo_orcamentario'], 'transparencia.v1', false
from profiles p
where p.slug = 'relator-geral-orcamento'
on conflict (sistema, identificador) do nothing;

-- 3) Backfill: Emendas de Relator sem autor -> o perfil institucional (dono da
--    categoria). Só linhas NULL, preservando a disjunção (1 emenda = 1 dono).
update emenda e
set autor_profile_id = x.profile_id
from id_externo x
where x.sistema = 'autor_orcamentario' and x.identificador = '8100'
  and x.profile_id is not null
  and e.autor_codigo = '8100'
  and e.autor_profile_id is null;

-- 4) Relator-Geral FORMAL por exercício (responsabilidade, não autoria pessoal).
--    Fontes: 2020 Domingos Neto (camara.leg.br/noticias/621332); 2021 Marcio Bittar
--    (senado.leg.br/noticias/materias/2020/05/06); 2022 Hugo Leal (camara.leg.br/
--    noticias/856841). Chave por EXERCÍCIO (o `ano` da emenda) — RP9 só existe
--    2020–2022 nos dados, coerente com o exercício.
create table if not exists relatoria_geral (
  ano                int primary key,
  relator_profile_id uuid not null references profiles(id),
  source             text not null,
  source_url         text,
  synced_at          timestamptz not null default now()
);

comment on table relatoria_geral is
  'Relator-Geral FORMAL do Orcamento por exercicio (quem assinou o pacote RP9). '
  'Responsabilidade funcional, NAO autoria individual: a emenda de relator pertence '
  'ao perfil institucional (autor_profile_id), nunca ao total individual do relator.';

insert into relatoria_geral (ano, relator_profile_id, source, source_url)
select v.ano, p.id, 'curadoria.relator_geral', v.url
from (values
  (2020, 'domingos-neto-143632',
   'https://www.camara.leg.br/noticias/621332-relator-do-orcamento-para-2020-apresenta-parecer-preliminar-que-deve-ser-votado-amanha/'),
  (2021, 'marcio-bittar-sen-285',
   'https://www12.senado.leg.br/noticias/materias/2020/05/06/marcio-bittar-sera-relator-do-orcamento-de-2021'),
  (2022, 'hugo-leal-141450',
   'https://www.camara.leg.br/noticias/856841-comissao-de-orcamento-cria-sistema-eletronico-para-receber-sugestoes-as-emendas-de-relator-em-2022/')
) as v(ano, slug, url)
join profiles p on p.slug = v.slug
on conflict (ano) do nothing;

-- 5) Camada ouro.
-- Perfil institucional (as emendas RP9 = emenda_publica WHERE autor_profile_id = este id).
create or replace view relator_geral_publico as
select p.id, p.nome, p.slug, p.ativo, p.source, p.source_url, p.synced_at
from profiles p
where p.tipo = 'relatoria';

-- Relator formal por exercício (CONTEXTO — nunca soma ao individual do relator).
create or replace view relatoria_geral_publico as
select rg.ano,
       p.id   as relator_profile_id,
       p.nome as relator_nome,
       p.slug as relator_slug,
       rg.source, rg.source_url, rg.synced_at
from relatoria_geral rg
join profiles p on p.id = rg.relator_profile_id;

grant select on relator_geral_publico   to anon, authenticated;
grant select on relatoria_geral_publico to anon, authenticated;

comment on view relator_geral_publico is
  'Camada ouro. Perfil institucional Relator-Geral do Orcamento (dono das Emendas '
  'de Relator / RP9). Emendas via emenda_publica WHERE autor_profile_id = este id.';
comment on view relatoria_geral_publico is
  'Camada ouro. Quem foi o Relator-Geral FORMAL de cada exercicio (com fonte). '
  'Responsabilidade funcional; a emenda RP9 pertence ao perfil institucional, '
  'nunca ao total individual do relator. Solicitante real de cada emenda = ausente '
  '(fora da fonte ingerida).';
