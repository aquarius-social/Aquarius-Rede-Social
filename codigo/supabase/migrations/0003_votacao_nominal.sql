-- =============================================================================
-- Aquarius · Onda 1 · Correção: distinguir nominal de secreta em votacao
-- =============================================================================
-- Motivo: leitura do modelo Django do Parlametria (leggo-backend) revelou que
-- o binário secreta/não-secreta que estávamos usando estava incompleto.
-- Existem TRÊS estados legítimos, não dois:
--
--   secreta = true                    → sem nominais (design constitucional)
--   nominal = false, secreta = false  → simbólica ou por acordo, sem nominais
--   nominal = true                    → deve trazer nominais
--
-- Sem esta distinção, uma votação simbólica que chega sem nominais é lida
-- como falha de integridade referencial — e votação simbólica é a MAIORIA
-- das votações da Câmara. Falso positivo em escala.
--
-- Não editamos a migration 0001/0002: o histórico é imutável. Novas
-- correções vêm em migrations novas.
-- =============================================================================

alter table votacao
  add column nominal boolean;

comment on column votacao.nominal is
  'True: nominal, deve ter voto_nominal. False: simbólica/por acordo, sem nominais. Null: não inferido pela fonte (heurística falhou). Ver Parlametria leggo-backend api/model/votacao.py como referência de que este campo é necessário.';

-- Coerência entre secreta e nominal: uma votação secreta não pode ser
-- simultaneamente declarada nominal. Se a fonte publicar essa combinação,
-- o portão da camada prata já recusa; aqui só documentamos a invariante.
alter table votacao
  add constraint votacao_secreta_nao_e_nominal
  check (not (secreta = true and nominal = true));
