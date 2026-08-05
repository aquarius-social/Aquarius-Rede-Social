-- =============================================================================
-- Aquarius · Situação do parlamentar — licenciado x suplente em exercício (§6.4)
-- =============================================================================
-- Problema: a view `parlamentar_publico` (0010) filtrava `and p.ativo`, então o
-- TITULAR LICENCIADO (ex.: virou ministro — `ativo=false`) sumia do app. Mas os
-- atos dele (despesas, emendas, votos) são DELE (§4) e precisam ser navegáveis.
--
-- Correção (regra 5: migration NOVA, não se edita a 0006/0010):
--   1. Mostrar também os titulares fora de exercício (licenciados/afastados),
--      SEM trazer o banco de suplentes que nunca assumiram (esses continuam fora).
--   2. Projetar `situacao` derivada para o app selar o estado atual:
--        em_exercicio · licenciado · suplente_em_exercicio
--
-- Regra da situação (a partir do que já temos: `ativo` = em exercício hoje, e
-- `ocupacao` do vínculo vigente = titular / suplente_em_exercicio):
--   • ativo  + ocupacao 'suplente_em_exercicio' → 'suplente_em_exercicio'
--   • ativo  (titular)                          → 'em_exercicio'
--   • não-ativo + ocupacao 'titular'            → 'licenciado'
--
-- Limite honesto: hoje só os SENADORES marcam `ativo=false` para licenciados (o
-- roster do Senado é completo). Deputados vêm todos `ativo=true` da lista da
-- Câmara — marcar o afastamento de deputado é a próxima etapa §6.4 (ingestão).
-- =============================================================================

create or replace view parlamentar_publico as
select
  p.id,
  p.nome,
  p.slug,
  p.foto_url,
  p.ativo,
  vt.uf                                      as uf_atual,
  vt.legislatura,
  vt.ocupacao                                as ocupacao_atual,
  coalesce(pa.sigla_atual, vt.partido_sigla_fonte) as partido_sigla_atual,
  pa.id                                      as partido_id,
  p.source, p.source_url, p.synced_at,
  vt.casa                                    as casa_atual,
  -- << nova coluna: estado atual para o selo do app
  case
    when p.ativo and vt.ocupacao = 'suplente_em_exercicio' then 'suplente_em_exercicio'
    when p.ativo                                           then 'em_exercicio'
    else 'licenciado'
  end                                        as situacao
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
where p.tipo = 'parlamentar'
  -- em exercício HOJE, OU titular fora de exercício (licenciado) — este último
  -- só aparece se tiver mandato vigente (vt) e for titular; suplente de banco
  -- (nunca assumiu) fica fora.
  and (p.ativo or vt.ocupacao = 'titular');

comment on view parlamentar_publico is
  'Camada ouro. Perfil de parlamentar SEM PII (§3.5); partido/UF/casa na data de '
  'hoje (§4). Bicameral (§17). `situacao` distingue em_exercicio/licenciado/'
  'suplente_em_exercicio (§6.4); titular licenciado permanece navegável.';
