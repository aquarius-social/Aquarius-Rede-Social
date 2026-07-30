-- =============================================================================
-- Aquarius · Onda 1 · Alvo de upsert idempotente para vinculo_temporal
-- =============================================================================
-- Motivo: a ingestão do histórico de mandatos (§12 D4) reconstrói os vínculos
-- temporais a cada rodada. Sem uma chave de conflito, re-rodar duplicaria os
-- vínculos. A `vinculo_sem_sobreposicao` (exclusion) impede SOBREPOSIÇÃO, mas
-- não é alvo de ON CONFLICT — o upsert precisa de uma constraint única.
--
-- (profile_id, casa, vigencia) identifica um vínculo: a mesma pessoa, na mesma
-- casa, com a mesma vigência exata, é o mesmo mandato — reingerir atualiza,
-- não duplica. daterange tem operador de igualdade btree, então serve a uma
-- unique constraint.
--
-- Não editamos migrations anteriores: correção vem em migration nova (padrão
-- que a 0003 estabeleceu).
-- =============================================================================

alter table vinculo_temporal
  add constraint vinculo_temporal_unico unique (profile_id, casa, vigencia);

comment on constraint vinculo_temporal_unico on vinculo_temporal is
  'Alvo de upsert da ingestão do histórico de mandatos (§12 D4). Reingestão do mesmo período atualiza em vez de duplicar.';
