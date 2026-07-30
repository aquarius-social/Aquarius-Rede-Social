-- =============================================================================
-- Aquarius · Onda 1 · Placar da votação como "não extraído" (nullable)
-- =============================================================================
-- Motivo: a Metodologia §10 estabelece que o placar declarado vive no TEXTO da
-- descrição da votação (formatos distintos entre plenário e comissão), extraído
-- por parsing. Quando a descrição é narrativa e não traz número, NÃO há placar.
--
-- As colunas sim/nao/abstencao nasceram `int not null default 0` (migration
-- 0002). Contra a fonte real, isso força 0 onde o valor é DESCONHECIDO — e
-- "dado errado é pior que dado ausente" (Metodologia, seção 1). Tornar as
-- colunas nuláveis deixa o banco representar honestamente "não extraído".
--
-- `resultado` idem: votação sem aprovação declarada tem resultado desconhecido;
-- `text not null` obrigava a inventar um rótulo.
--
-- A check `votacao_contadores_nao_negativos` permanece: em Postgres, comparação
-- com NULL resulta em NULL (não viola), então nulo passa e negativo continua
-- barrado. Não editamos 0002 — o histórico é imutável (padrão da 0003).
-- =============================================================================

alter table votacao alter column sim       drop not null;
alter table votacao alter column sim       drop default;
alter table votacao alter column nao       drop not null;
alter table votacao alter column nao       drop default;
alter table votacao alter column abstencao drop not null;
alter table votacao alter column abstencao drop default;
alter table votacao alter column resultado drop not null;

comment on column votacao.sim is
  'Placar declarado (do texto da descrição, §10). NULL = não extraído; nunca 0 por ausência.';
comment on column votacao.nao is
  'Placar declarado (do texto da descrição, §10). NULL = não extraído.';
comment on column votacao.abstencao is
  'Placar declarado (do texto da descrição, §10). NULL = não extraído.';
comment on column votacao.resultado is
  'aprovada | rejeitada, derivado de aprovacao. NULL quando a fonte não declara.';
