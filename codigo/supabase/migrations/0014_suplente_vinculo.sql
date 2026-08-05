-- =============================================================================
-- Aquarius · §6.4 — Suplente em exercício: vínculo real + titular + causa
-- =============================================================================
-- Fecha o §6.4 do Senado: o suplente que assumiu passa a ter vínculo (período
-- REAL de exercício, dos `Exercicios` da fonte), preso ao TITULAR
-- (`titular_profile_id`, da lista `Titular` do mandato) e com a CAUSA do
-- afastamento (`DescricaoCausaAfastamento` — procedural: "Licença com convocação
-- de suplente" etc.; a fonte NÃO traz o motivo específico, ex.: "Ministro").
--
--   1. Coluna `causa` em `vinculo_temporal`.
--   2. View `parlamentar_publico` expõe o link BIDIRECIONAL:
--        • no suplente: titular_nome + assumiu_em + causa;
--        • no titular licenciado: suplente_nome + suplente_desde (quem cobre).
-- Correção por migration NOVA (regra 5).
-- =============================================================================

alter table vinculo_temporal add column if not exists causa text;
comment on column vinculo_temporal.causa is
  'Causa do exercício/afastamento (suplente): DescricaoCausaAfastamento (§6.4).';

create or replace view parlamentar_publico as
select
  p.id, p.nome, p.slug, p.foto_url, p.ativo,
  vt.uf                                      as uf_atual,
  vt.legislatura,
  vt.ocupacao                                as ocupacao_atual,
  coalesce(pa.sigla_atual, vt.partido_sigla_fonte) as partido_sigla_atual,
  pa.id                                      as partido_id,
  p.source, p.source_url, p.synced_at,
  vt.casa                                    as casa_atual,
  case
    when p.ativo and vt.ocupacao = 'suplente_em_exercicio' then 'suplente_em_exercicio'
    when p.ativo                                           then 'em_exercicio'
    else 'licenciado'
  end                                        as situacao,
  -- Suplente → titular
  vt.titular_profile_id,
  tit.nome                                   as titular_nome,
  case when vt.ocupacao = 'suplente_em_exercicio' then lower(vt.vigencia) end as assumiu_em,
  vt.causa,
  -- Titular licenciado → suplente que está cobrindo hoje
  sup.profile_id                             as suplente_profile_id,
  sup.nome                                   as suplente_nome,
  sup.desde                                  as suplente_desde
from profiles p
left join lateral (
  select v.*
  from vinculo_temporal v
  where v.profile_id = p.id
    and v.vigencia @> current_date
  order by lower(v.vigencia) desc
  limit 1
) vt on true
left join partido pa on pa.id = vt.partido_id
left join profiles tit on tit.id = vt.titular_profile_id
left join lateral (
  select s.profile_id, pf2.nome, lower(s.vigencia) as desde
  from vinculo_temporal s
  join profiles pf2 on pf2.id = s.profile_id
  where s.titular_profile_id = p.id
    and s.vigencia @> current_date
  order by lower(s.vigencia) desc
  limit 1
) sup on true
where p.tipo = 'parlamentar' and vt.profile_id is not null;

comment on view parlamentar_publico is
  'Camada ouro. Perfil de parlamentar SEM PII (§3.5); partido/UF/casa/situação na '
  'data de hoje (§4/§6.4). Link bidirecional suplente↔titular + causa/datas.';
