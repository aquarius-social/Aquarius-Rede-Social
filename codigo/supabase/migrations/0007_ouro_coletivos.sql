-- =============================================================================
-- Aquarius · Onda 1 · Camada ouro — perfis coletivos (comissão, frente)
-- =============================================================================
-- Estende a camada ouro (0006) para os perfis coletivos populados pelo coletor
-- `coletivos.py`. Mesma disciplina: projeção curada sobre `profiles`, com
-- proveniência/frescor, servida a anon/authenticated. Perfis coletivos não têm
-- PII (não são pessoa natural), mas seguem a regra de ler só do ouro.
--
-- Correção vem em migration nova (padrão da 0003).
-- =============================================================================

create view comissao_publica as
select
  id, nome, sigla, slug, ativo,
  source, source_url, synced_at
from profiles
where tipo = 'comissao' and ativo;

create view frente_publica as
select
  id, nome, slug, ativo,
  source, source_url, synced_at
from profiles
where tipo = 'frente' and ativo;

grant select on comissao_publica, frente_publica to anon, authenticated;

comment on view comissao_publica is
  'Camada ouro. Comissões (perfil polimórfico tipo=comissao).';
comment on view frente_publica is
  'Camada ouro. Frentes parlamentares (perfil polimórfico tipo=frente).';
