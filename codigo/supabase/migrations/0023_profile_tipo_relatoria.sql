-- =============================================================================
-- Aquarius · autoria de emenda de relator — novo tipo de perfil 'relatoria'
-- =============================================================================
-- ALTER TYPE ... ADD VALUE precisa ficar SOZINHO nesta migration: no Postgres um
-- valor de enum recém-adicionado NÃO pode ser USADO na mesma transação em que foi
-- adicionado ("unsafe use of new value"). O uso do valor ('relatoria') fica na
-- 0024. (regra 5: adição vem em migration nova; não editar migration antiga.)
--
-- 'relatoria' = a FUNÇÃO institucional de Relator-Geral do Orçamento, dona das
-- "Emendas de Relator" (RP9 / "orçamento secreto"). NÃO é pessoa nem bancada.
-- =============================================================================

alter type profile_tipo add value if not exists 'relatoria';
