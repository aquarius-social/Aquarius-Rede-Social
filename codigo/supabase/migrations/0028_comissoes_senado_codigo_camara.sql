-- =============================================================================
-- Aquarius · §6.3/§13 — Emenda de Comissão do SENADO com código no range Câmara
-- =============================================================================
-- Dois códigos de autor de comissão vêm no range 5xxx (que 0025 tratou como
-- Câmara), mas o nome bate EXATAMENTE — e só — com uma comissão do SENADO que já
-- tem perfil. Não há comissão homônima na Câmara (a Câmara tem CCOM, não CCDD;
-- não tem "Defesa da Democracia"), então o autor é inequivocamente a do Senado.
-- O descasamento código↔casa é ruído da fonte orçamentária, não pessoa/entidade
-- diferente. Ligação por nome exato + casa; grau 'com_ressalva' (pendente) por
-- causa do descasamento de range, para conferência.
--
--   5051 -> comissao-sf-ccdd-2614  (Comissão de Comunicação e Direito Digital)
--   5052 -> comissao-sf-cdd-2617   (Comissão de Defesa da Democracia)
--
-- Já aplicado ao banco via PostgREST (2026-09-25); registro reproduzível.
-- Idempotente. (Fica FORA, honesto: 5029 "Senado do Futuro" — sem perfil ainda.)
-- =============================================================================

insert into id_externo (profile_id, sistema, identificador, metodo, grau, sinais, versao_regra, pendente_conferencia)
select p.id, 'autor_orcamentario', m.cod, 'convergencia', 'com_ressalva',
       ARRAY['nome_exato_comissao','casa_senado'], 'comissoes_sucessao.v1', true
from (values
  ('5051','comissao-sf-ccdd-2614'),
  ('5052','comissao-sf-cdd-2617')
) as m(cod, slug)
join profiles p on p.slug = m.slug
on conflict (sistema, identificador) do nothing;

update emenda e
set autor_profile_id = x.profile_id
from id_externo x
where x.sistema = 'autor_orcamentario' and x.identificador = e.autor_codigo
  and x.profile_id is not null
  and e.autor_profile_id is null
  and e.autor_codigo in ('5051','5052');
