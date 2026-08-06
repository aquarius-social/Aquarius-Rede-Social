-- =============================================================================
-- Aquarius · §6.4 (Câmara) — titular do suplente vira OPCIONAL
-- =============================================================================
-- A constraint original exigia bicondicional: suplente_em_exercicio ⟺ tem
-- titular. Isso funcionou no Senado (a fonte dá o titular), mas a CÂMARA NÃO
-- expõe o link titular↔suplente (verificado: nem o detalhe do deputado nem o
-- histórico trazem — é dado eleitoral/coligação do TSE). Sem relaxar, o suplente
-- da Câmara ficaria de fora (quarentena) e sumiria da lista, mesmo estando em
-- exercício.
--
-- Relaxa para: titular só faz sentido para suplente, mas NÃO é obrigatório.
--   • suplente com titular  → OK (Senado)
--   • suplente sem titular  → OK (Câmara — mostra 'Suplente em exercício' sem link)
--   • não-suplente com titular → bloqueado (segue proibido)
-- O link da Câmara volta quando ingerirmos a ordem de suplência do TSE (backlog).
-- Correção por migration NOVA (regra 5).
-- =============================================================================

alter table vinculo_temporal drop constraint if exists vinculo_suplente_coerente;

alter table vinculo_temporal add constraint vinculo_suplente_coerente check (
  titular_profile_id is null or ocupacao = 'suplente_em_exercicio'
);

comment on constraint vinculo_suplente_coerente on vinculo_temporal is
  'Titular só para suplente_em_exercicio, mas OPCIONAL (a Câmara não expõe o link; §6.4).';
