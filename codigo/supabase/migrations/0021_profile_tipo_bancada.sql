-- =============================================================================
-- Aquarius · autoria coletiva de emenda — novo tipo de perfil 'bancada'
-- =============================================================================
-- ALTER TYPE ... ADD VALUE precisa ficar SOZINHO nesta migration: no Postgres um
-- valor de enum recém-adicionado NÃO pode ser USADO na mesma transação em que foi
-- adicionado ("unsafe use of new value"). Como o runner de migrations roda cada
-- arquivo numa transação, o uso do valor ('bancada') fica na 0022. (regra 5:
-- adição vem em migration nova; não editar migration antiga.)
-- =============================================================================

alter type profile_tipo add value if not exists 'bancada';
