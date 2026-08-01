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
