-- =============================================================================
-- Aquarius · §4/§6/§6.3 — dedup dos autores INDIVIDUAIS de emenda (10 códigos)
-- =============================================================================
-- Fecha os 203 individuais que o casamento por nome deixou nulos porque o nome
-- era AMBÍGUO (homônimo → o lookup por nome devolve None, §6.3) ou porque a
-- pessoa tinha o perfil sob outra grafia. A casa correta é a da DATA DO FATO
-- (§4/§6): a fonte da emenda NÃO carrega a casa do autor, então cada vínculo foi
-- ancorado no MANDATO OFICIAL (API Câmara /deputados/{id} + Senado
-- /senador/{cod}/mandatos e /senador/lista/legislatura/{leg}) e verificado
-- adversarialmente (8/8 duplicados "concorda/alta", 0 divergências; 2 "sem
-- perfil" identificados como perfis JÁ existentes — nenhum perfil criado).
--
-- Legislaturas: 55=2015-2019, 56=2019-2023, 57=2023-2027. Emenda individual à LOA
-- do ano Y é redigida/apresentada em Y-1 → a casa é a de Y-1.
--
-- Homônimos resolvidos por sinal independente:
--   · PEDRO CHAVES são DUAS pessoas — senador Pedro Chaves dos Santos Filho (MS,
--     leg55, cód. Senado 5116) e deputado Pedro Pinheiro Chaves (GO, leg55, cód.
--     Câmara 74812). Desambiguados por UF do gasto (MS vs GO) e nome civil.
--     Códigos de orçamento distintos (3843=MS→Senado, 3672=GO→Câmara).
--   · RENZO BRAZ e AROLDE são a mesma pessoa Câmara↔Senado (nascimento idêntico);
--     a data do fato decide a casa.
--
-- metodo='convergencia' + grau='direto': ≥2 sinais convergentes (nome parlamentar
-- + mandato oficial na data do fato; +UF do gasto onde havia homônimo). Passa em
-- id_externo_grau_coerente (array_length(sinais,1) >= 2). NÃO é pendente: a fonte
-- oficial de mandato é o 2º sinal, não um palpite.
--
-- Já aplicado ao banco via PostgREST (2026-09-24); este arquivo é o registro
-- reproduzível. Idempotente: ON CONFLICT DO NOTHING / WHERE ... IS NULL.
-- =============================================================================

-- 1) Vínculo código de autor -> perfil da casa da data do fato (10 códigos).
insert into id_externo (profile_id, sistema, identificador, metodo, grau, sinais, versao_regra, pendente_conferencia)
select p.id, 'autor_orcamentario', m.cod, 'convergencia', 'direto', m.sinais,
       'dedup_individuais.v1', false
from (values
  -- Senadores na data do fato (Câmara é mandato de outra era):
  ('4185','jorginho-mello-sen-5350',    ARRAY['nome_parlamentar','mandato_oficial_data_do_fato']),  -- senador SC leg56; emendas 2020-2022
  ('4090','arolde-de-oliveira-sen-751', ARRAY['nome_parlamentar','mandato_oficial_data_do_fato']),  -- senador RJ leg56; emenda 2020
  ('2894','eunicio-oliveira-sen-612',   ARRAY['nome_parlamentar','mandato_oficial_data_do_fato']),  -- senador CE leg55; emendas 2018-2019
  ('2881','lindbergh-farias-sen-3695',  ARRAY['nome_parlamentar','mandato_oficial_data_do_fato']),  -- senador RJ leg55; emendas 2018-2019
  ('3886','jean-paul-prates-sen-5627',  ARRAY['nome_parlamentar','mandato_oficial_data_do_fato']),  -- senador RN leg56; emendas 2020-2023 (grafia "Jean-Paul")
  -- Homônimo/UF desambigua (3º sinal = UF do gasto):
  ('3843','pedro-chaves-sen-5116',      ARRAY['nome_parlamentar','mandato_oficial_data_do_fato','uf_do_gasto']),  -- senador MS leg55; gasto MS
  ('3672','pedro-chaves-74812',         ARRAY['nome_parlamentar','mandato_oficial_data_do_fato','uf_do_gasto']),  -- deputado GO leg55; gasto GO (pessoa DIFERENTE do 5116)
  ('2765','renzo-braz-160654',          ARRAY['nome_parlamentar','mandato_oficial_data_do_fato','uf_do_gasto']),  -- deputado MG leg55; LOA2019 redigida 2018; gasto MG
  ('3780','wherles-rocha-178840',       ARRAY['nome_parlamentar','mandato_oficial_data_do_fato','uf_do_gasto']),  -- "ROCHA" = Wherles F. da Rocha, deputado AC leg55; gasto AC
  ('4225','dalua-do-rota-217330',       ARRAY['nome_parlamentar','mandato_oficial_data_do_fato','uf_do_gasto'])   -- "Pedro Dalua" = DaLua do Rota (mesma pessoa), deputado AP leg56; gasto AP
) as m(cod, slug, sinais)
join profiles p on p.slug = m.slug
on conflict (sistema, identificador) do nothing;

-- 2) Backfill: emenda individual sem autor -> o perfil resolvido (só linhas NULL).
update emenda e
set autor_profile_id = x.profile_id
from id_externo x
where x.sistema = 'autor_orcamentario' and x.identificador = e.autor_codigo
  and x.profile_id is not null
  and e.autor_profile_id is null
  and e.autor_codigo in ('4185','4090','2894','2881','3886',
                         '3843','3672','2765','3780','4225');
