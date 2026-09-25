-- =============================================================================
-- Aquarius · §13 — perfis de COMISSÃO MISTA (Congresso) + autoria de emenda
-- =============================================================================
-- Três Emendas de Comissão vêm de comissões MISTAS (Câmara+Senado), que não
-- tinham perfil (os 30 perfis de comissão eram só-Câmara, os 61 só-Senado). São
-- entidades institucionais REAIS e permanentes — criadas aqui como perfil
-- coletivo `tipo='comissao'` (mesma disjunção das bancadas/relatoria: a emenda é
-- do colegiado, NUNCA somada ao total individual de um parlamentar).
--
-- Ancoradas em órgão OFICIAL:
--   CMCCAI (Controle das Ativ. de Inteligência - CCAI) — Câmara órgão 5504
--   CMMC   (Mudanças Climáticas)                        — Câmara órgão 537463
--   CMMIR  (Migrações Internacionais e Refugiados)      — Senado colegiado 2301
--
-- Já aplicado ao banco via PostgREST (2026-09-25); registro reproduzível.
-- Idempotente. (Fica FORA: "Senado do Futuro"/CSF — comissão EXTINTA em 2019,
-- sem colegiado atual; suas 2 emendas 2020/2023 seguem como resíduo honesto.)
-- =============================================================================

-- 1) Perfis das 3 comissões mistas.
insert into profiles (tipo, nome, sigla, slug, ativo, source, source_url)
values
  ('comissao','Comissão Mista de Controle das Atividades de Inteligência - CCAI','CMCCAI',
   'comissao-cmccai-5504', true, 'camara.orgaos','https://dadosabertos.camara.leg.br/api/v2'),
  ('comissao','Comissão Mista Permanente sobre Mudanças Climáticas - CMMC','CMMC',
   'comissao-cmmc-537463', true, 'camara.orgaos','https://dadosabertos.camara.leg.br/api/v2'),
  ('comissao','Comissão Mista Permanente sobre Migrações Internacionais e Refugiados','CMMIR',
   'comissao-sf-cmmir-2301', true, 'senado.colegiados','https://legis.senado.leg.br/dadosabertos')
on conflict (slug) do nothing;

-- 2) Vínculo código de autor -> perfil da mista (fonte_direta: sigla + órgão oficial).
insert into id_externo (profile_id, sistema, identificador, metodo, grau, sinais, versao_regra, pendente_conferencia)
select p.id, 'autor_orcamentario', m.cod, 'fonte_direta', 'direto',
       ARRAY['sigla_na_fonte','orgao_oficial_mista'], 'comissoes_sucessao.v1', false
from (values
  ('5027','comissao-cmccai-5504'),
  ('5009','comissao-cmmc-537463'),
  ('5038','comissao-sf-cmmir-2301')
) as m(cod, slug)
join profiles p on p.slug = m.slug
on conflict (sistema, identificador) do nothing;

-- 3) Backfill das emendas dessas mistas (só linhas NULL).
update emenda e
set autor_profile_id = x.profile_id
from id_externo x
where x.sistema = 'autor_orcamentario' and x.identificador = e.autor_codigo
  and x.profile_id is not null
  and e.autor_profile_id is null
  and e.autor_codigo in ('5027','5009','5038');
