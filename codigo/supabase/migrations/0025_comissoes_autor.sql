-- =============================================================================
-- Aquarius · §6.3/§13 — autoria de Emenda de Comissão (alta confiança)
-- =============================================================================
-- Liga códigos de autor 5xxx (Câmara) / 6xxx (Senado) aos perfis `tipo='comissao'`
-- já existentes. SÓ os matches de ALTA CONFIANÇA: a fonte declara a SIGLA no nome
-- ("... - CE", "- CAE"...), o código dá a CASA (5xxx=Câmara, 6xxx=Senado), e
-- sigla+casa → exatamente UM perfil; o nome semântico foi conferido (token overlap).
-- Os ~38 códigos ambíguos (sigla truncada/ausente, ex.: "COM. DA SAUDE") ficam
-- FORA — precisam de curadoria à mão (regra 2: não atribuir às cegas).
--
-- Mesma disjunção das bancadas/relatoria: a emenda de comissão pertence ao perfil
-- da comissão, NUNCA somada ao total individual de um parlamentar.
--
-- Já aplicado ao banco via PostgREST (2026-09-23); este arquivo é o registro
-- reproduzível. Idempotente: ON CONFLICT DO NOTHING / WHERE ... IS NULL.
-- =============================================================================

-- 1) Ligação código de autor -> perfil da comissão (13 de alta confiança).
--    metodo='fonte_direta'/grau='direto': a fonte declara a sigla no nome +
--    o código dá a casa — resolução determinística, não casamento de nome cru.
insert into id_externo (profile_id, sistema, identificador, metodo, grau, sinais, versao_regra, pendente_conferencia)
select p.id, 'autor_orcamentario', m.cod, 'fonte_direta', 'direto',
       ARRAY['codigo_orcamentario','sigla_na_fonte','casa'], 'transparencia.v1', false
from (values
  ('5004','comissao-ccult-536996'),   -- Comissão de Cultura (Câmara / CCULT)
  ('5005','comissao-ce-2009'),        -- Comissão de Educação (Câmara / CE)
  ('5006','comissao-cespo-537236'),   -- Comissão do Esporte (Câmara / CESPO)
  ('5013','comissao-cdc-2004'),       -- Comissão de Defesa do Consumidor (Câmara / CDC)
  ('5017','comissao-cft-2010'),       -- Comissão de Finanças e Tributação (Câmara / CFT)
  ('5018','comissao-cme-2012'),       -- Comissão de Minas e Energia (Câmara / CME)
  ('5023','comissao-cdu-2006'),       -- Comissão de Desenvolvimento Urbano (Câmara / CDU)
  ('5034','comissao-clp-5438'),       -- Comissão de Legislação Participativa (Câmara / CLP)
  ('6001','comissao-sf-ci-59'),       -- Comissão de Serviços de Infraestrutura (Senado / CI)
  ('6004','comissao-sf-ce-47'),       -- Comissão de Educação e Cultura (Senado / CE)
  ('6005','comissao-sf-cae-38'),      -- Comissão de Assuntos Econômicos (Senado / CAE)
  ('6006','comissao-sf-cas-40'),      -- Comissão de Assuntos Sociais (Senado / CAS)
  ('6012','comissao-sf-cra-1307')     -- Comissão de Agricultura e Reforma Agrária (Senado / CRA)
) as m(cod, slug)
join profiles p on p.slug = m.slug
on conflict (sistema, identificador) do nothing;

-- 2) Backfill: Emenda de Comissão sem autor -> a comissão (só linhas NULL).
update emenda e
set autor_profile_id = x.profile_id
from id_externo x
where x.sistema = 'autor_orcamentario' and x.identificador = e.autor_codigo
  and x.profile_id is not null
  and e.autor_profile_id is null
  and e.tipo = 'Emenda de Comissão'
  and e.autor_codigo in ('5004','5005','5006','5013','5017','5018','5023','5034',
                         '6001','6004','6005','6006','6012');
