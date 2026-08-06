-- =============================================================================
-- Aquarius · §6.4 (Câmara) — situação 'licenciado' honra o vínculo, não só `ativo`
-- =============================================================================
-- O deputado licenciado (ex.: Padilha, ministro) tem `ocupacao='licenciado'` no
-- vínculo vigente (após corrigir o coletor, que não reconhecia a situação
-- "Licença" da Câmara). Mas a lógica de `situacao` da view usava `p.ativo` — e
-- deputado é sempre `ativo=true` —, então ele apareceria como 'em_exercicio'.
-- Aqui a situação passa a checar `ocupacao='licenciado'` primeiro.
-- Correção por migration NOVA (regra 5).
-- =============================================================================

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
    when vt.ocupacao = 'licenciado'                        then 'licenciado'
    when p.ativo and vt.ocupacao = 'suplente_em_exercicio' then 'suplente_em_exercicio'
    when p.ativo                                           then 'em_exercicio'
    else 'licenciado'
  end                                        as situacao,
  vt.titular_profile_id,
  tit.nome                                   as titular_nome,
  case when vt.ocupacao = 'suplente_em_exercicio' then lower(vt.vigencia) end as assumiu_em,
  vt.causa,
  sup.profile_id                             as suplente_profile_id,
  sup.nome                                   as suplente_nome,
  sup.desde                                  as suplente_desde
from profiles p
left join lateral (
  select v.* from vinculo_temporal v
  where v.profile_id = p.id and v.vigencia @> current_date
  order by lower(v.vigencia) desc limit 1
) vt on true
left join partido pa on pa.id = vt.partido_id
left join profiles tit on tit.id = vt.titular_profile_id
left join lateral (
  select s.profile_id, pf2.nome, lower(s.vigencia) as desde
  from vinculo_temporal s join profiles pf2 on pf2.id = s.profile_id
  where s.titular_profile_id = p.id and s.vigencia @> current_date
  order by lower(s.vigencia) desc limit 1
) sup on true
where p.tipo = 'parlamentar' and vt.profile_id is not null;
