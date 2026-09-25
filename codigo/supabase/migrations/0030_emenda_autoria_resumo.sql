-- =============================================================================
-- Aquarius · §1/§13 — resíduo de autoria EXPLÍCITO (dinheiro nunca some do total)
-- =============================================================================
-- Problema: a soma de emendas POR AUTOR nunca fecha o total geral, porque um
-- punhado de emendas fica sem `autor_profile_id` (autoria coletiva combinada ou
-- ausente na fonte). Num ranking por autor esse resíduo somem silenciosamente —
-- e o dinheiro parece ter evaporado. Isto o torna um objeto de PRIMEIRA CLASSE,
-- reconciliável e registrado no banco.
--
-- `emenda_autoria_resumo_publico`: por ano, o total por estágio × o quanto está
-- SEM autoria identificada. Grand total = soma dos anos; resíduo = soma do
-- *_sem_autor. O Prometeus (`emendas_resumo`) lê daqui e SEMPRE reporta o resíduo.
--
-- Também fecha o último caso de Emenda de Relator: a linha "Sem informação"
-- (codigo_emenda='S/I', 2020, ~R$459mi empenhado) é execução de RP9 que a fonte
-- não amarrou a um código — por §13 toda Emenda de Relator é institucional, então
-- vai ao perfil relator-geral-orcamento (com a ressalva de que o código é S/I).
--
-- Já aplicado ao banco via PostgREST (2026-09-25); registro reproduzível.
-- =============================================================================

-- 1) Emenda de Relator "Sem informação" (sem código) -> perfil institucional (§13).
update emenda e
set autor_profile_id = (select id from profiles where slug = 'relator-geral-orcamento')
where e.tipo = 'Emenda de Relator'
  and e.codigo_emenda = 'S/I'
  and e.autor_profile_id is null;

-- 2) View de reconciliação: total × sem-autoria, por ano e por estágio.
create or replace view emenda_autoria_resumo_publico as
select
  ano,
  count(*)                                    as n_emendas,
  count(autor_profile_id)                     as n_com_autor,
  count(*) - count(autor_profile_id)          as n_sem_autor,
  round(coalesce(sum(valor_empenhado), 0), 2) as empenhado_total,
  round(coalesce(sum(valor_empenhado) filter (where autor_profile_id is null), 0), 2)
                                              as empenhado_sem_autor,
  round(coalesce(sum(valor_pago), 0), 2)      as pago_total,
  round(coalesce(sum(valor_pago) filter (where autor_profile_id is null), 0), 2)
                                              as pago_sem_autor,
  max(source)     as source,
  max(source_url) as source_url,
  max(synced_at)  as synced_at
from emenda
group by ano;

grant select on emenda_autoria_resumo_publico to anon, authenticated;

comment on view emenda_autoria_resumo_publico is
  'Reconciliação de autoria de emenda (§1). Por ano: total por estágio e quanto '
  'está SEM autoria identificada. O resíduo é explícito para nunca sumir de um '
  'ranking por autor — some apenas dentro do mesmo estágio (§13).';
