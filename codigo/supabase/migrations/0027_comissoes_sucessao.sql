-- =============================================================================
-- Aquarius · §4/§6/§13 — Emenda de Comissão: sucessão de órgão (reforma 2023)
-- =============================================================================
-- Fecha as comissões da Câmara que o 0025 não resolveu porque a sigla na fonte é
-- de ANTES da reforma de 2023 (renomeações/desmembramentos). A chave é a
-- IDENTIDADE DE ÓRGÃO da própria Câmara: a API `/orgaos/{id}` mostra que vários
-- órgãos são CONTÍNUOS desde 2011-03-02 (dataFim null), apenas renomeados —
-- então a emenda antiga resolve para o perfil que carrega esse mesmo id de órgão
-- (NÃO se cria perfil novo: criaria uma duplicata do órgão).
--
-- Verificado por 18 agentes contra a API oficial de órgãos + conferência do id.
-- Legislaturas: emenda à LOA do ano Y é da comissão como existia em Y.
--
-- CONTINUAÇÃO DIRETA (mesma identidade, nome ~inalterado) — metodo='fonte_direta':
--   5007 CTUR, 5036 CMULHER, 5001 CSPCCO, 5010 CAPADR, 5049 CPASF, 5030 CDHM→CDHMIR
-- CONTINUAÇÃO COM RESSALVA (órgão contínuo, mas competência desmembrada p/ órgão
-- NOVO em 2023) — metodo='convergencia', grau='com_ressalva', pendente=true:
--   5011 CCTCI→CCTI (Comunicação saiu p/ CCOM, id novo 539385)
--   5015 CDEIC→CDE  (Ind./Com. saiu p/ CICS, id novo 539386)
--   5021 CSSF →CSAUDE(id 2014)  (Prev./Família saiu p/ CPASF, id novo 539387)
--   5022 CTASP→CTRAB(id 2015)   (Adm./Serv.Púb. saiu p/ CASP, id novo 539388)
--   5033 CINDRA→CINDRE(id 2017) (Amazônia saiu p/ CPOVOS, id novo 539384)
-- RELATOR-GERAL: o código ' GE' ("RELATOR GERAL", 2019) vai ao perfil
--   institucional relator-geral-orcamento (mesma lógica do RP9, §13), com ressalva.
--
-- FORA (honestamente sem autor pessoal, 18): 3 comissões MISTAS do Congresso
-- (5027 CCAI, 5009 CMMC, 5038 Migrações — sem perfil só-Câmara), 3 comissões do
-- SENADO com código no range da Câmara (5029 CSF, 5051 CCDD, 5052 Defesa da
-- Democracia — casa divergente do código, não se força), 1 rótulo que combina
-- DOIS órgãos distintos (5035 Transparência = CFFC+CDC, sem órgão único). São
-- decisão de modelagem (criar perfil misto/histórico), não furo de casamento.
--
-- Já aplicado ao banco via PostgREST (2026-09-25); registro reproduzível.
-- Idempotente: ON CONFLICT DO NOTHING / WHERE ... IS NULL.
-- =============================================================================

-- 1) Continuação de órgão -> perfil atual que carrega o mesmo id de órgão.
insert into id_externo (profile_id, sistema, identificador, metodo, grau, sinais, versao_regra, pendente_conferencia)
select p.id, 'autor_orcamentario', m.cod, m.metodo, m.grau, m.sinais,
       'comissoes_sucessao.v1', m.pendente
from (values
  ('5007','comissao-ctur-6066',    'fonte_direta','direto',       ARRAY['sigla_na_fonte','orgao_id_camara'],  false),
  ('5036','comissao-cmulher-537870','fonte_direta','direto',      ARRAY['sigla_na_fonte','orgao_id_camara'],  false),
  ('5001','comissao-cspcco-5503',  'fonte_direta','direto',       ARRAY['sigla_na_fonte','orgao_id_camara'],  false),
  ('5010','comissao-capadr-2001',  'fonte_direta','direto',       ARRAY['sigla_na_fonte','orgao_id_camara'],  false),
  ('5049','comissao-cpasf-539387', 'fonte_direta','direto',       ARRAY['sigla_na_fonte','orgao_id_camara'],  false),
  ('5030','comissao-cdhmir-2007',  'fonte_direta','direto',       ARRAY['sigla_na_fonte','orgao_id_camara'],  false),
  ('5011','comissao-ccti-2002',    'convergencia','com_ressalva', ARRAY['sigla_na_fonte','orgao_id_continuo'],true),
  ('5015','comissao-cde-2008',     'convergencia','com_ressalva', ARRAY['sigla_na_fonte','orgao_id_continuo'],true),
  ('5021','comissao-csaude-2014',  'convergencia','com_ressalva', ARRAY['sigla_na_fonte','orgao_id_continuo'],true),
  ('5022','comissao-ctrab-2015',   'convergencia','com_ressalva', ARRAY['sigla_na_fonte','orgao_id_continuo'],true),
  ('5033','comissao-cindre-2017',  'convergencia','com_ressalva', ARRAY['sigla_na_fonte','orgao_id_continuo'],true),
  (' GE', 'relator-geral-orcamento','convergencia','com_ressalva',ARRAY['nome_relator_geral'],               true)
) as m(cod, slug, metodo, grau, sinais, pendente)
join profiles p on p.slug = m.slug
on conflict (sistema, identificador) do nothing;

-- 2) Backfill: Emenda de Comissão sem autor -> o perfil resolvido (só linhas NULL).
update emenda e
set autor_profile_id = x.profile_id
from id_externo x
where x.sistema = 'autor_orcamentario' and x.identificador = e.autor_codigo
  and x.profile_id is not null
  and e.autor_profile_id is null
  and e.autor_codigo in ('5007','5036','5001','5010','5049','5030',
                         '5011','5015','5021','5022','5033',' GE');
