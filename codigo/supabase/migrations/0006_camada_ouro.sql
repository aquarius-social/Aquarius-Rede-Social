-- =============================================================================
-- Aquarius · Onda 1 · Camada OURO — a projeção servida (Metodologia §3.1)
-- =============================================================================
-- A terceira camada do pipeline. Bronze é o cru imutável; prata é o tratado e
-- qualificado; OURO é "o modelo consumível pelo oráculo, com rótulos de
-- proveniência, completude e frescor embutidos". É esta camada — e SÓ ela — que
-- o app público e o Prometeus leem. Nada é consultado ao vivo na fonte.
--
-- Implementada como VIEWS sobre a prata. Duas decisões deliberadas:
--
--   1. DUAS FRONTEIRAS DE PII (Metodologia §3.5). Nome civil, data de nascimento
--      e naturalidade "permanecem restritos à camada interna de resolução, sem
--      integrar respostas". RLS é por LINHA, não por coluna — não consegue
--      esconder uma coluna. Então a fronteira é a VIEW: ela seleciona apenas as
--      colunas públicas, e a PII simplesmente não é projetada. Toda view aqui é
--      auditável por inspeção: se uma coluna de PII não aparece no SELECT, ela
--      não vaza. É a razão de a camada servida ser uma projeção curada, não a
--      tabela crua.
--
--   2. VIEW COMO PORTA DE LEITURA PÚBLICA. As tabelas de prata têm RLS ligada e
--      SEM policy — ou seja, negam leitura a quem não é service role. As views
--      abaixo rodam com o privilégio do dono (comportamento padrão, "security
--      definer") e recebem GRANT SELECT para `anon` e `authenticated`. Assim o
--      público lê exatamente as colunas curadas, e nunca as tabelas cruas.
--      A ingestão (service role) continua escrevendo nas tabelas normalmente.
--
-- Proveniência + frescor: toda view carrega source/source_url/synced_at. O
-- `synced_at` é o frescor — a última vez que a fonte foi relida para aquela linha.
--
-- Correção vem em migration nova (padrão da 0003). Este arquivo não altera nada
-- da prata; só projeta.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- parlamentar_publico — perfil de parlamentar, SEM PII
-- -----------------------------------------------------------------------------
-- Partido/UF são resolvidos NA DATA DE HOJE: o vínculo temporal vigente agora
-- (§4, "resolver na data do fato"). Para o partido de um voto antigo, use
-- `voto_nominal_publico.partido_sigla_na_epoca`, não este.
create view parlamentar_publico as
select
  p.id,
  p.nome,                                   -- nome parlamentar (de urna), público
  p.slug,
  p.foto_url,
  p.ativo,
  vt.uf                                      as uf_atual,
  vt.legislatura,
  vt.ocupacao                                as ocupacao_atual,
  coalesce(pa.sigla_atual, vt.partido_sigla_fonte) as partido_sigla_atual,
  pa.id                                      as partido_id,
  -- Proveniência e frescor
  p.source, p.source_url, p.synced_at
from profiles p
left join lateral (
  select v.*
  from vinculo_temporal v
  where v.profile_id = p.id
    and v.casa = 'camara'
    and v.vigencia @> current_date          -- o vínculo vigente hoje
  order by lower(v.vigencia) desc
  limit 1
) vt on true
left join partido pa on pa.id = vt.partido_id
where p.tipo = 'parlamentar' and p.ativo;
-- NB: PII de `profiles` (nome_civil, data_nascimento, naturalidade_*) NÃO é
-- projetada — de propósito (§3.5).


-- -----------------------------------------------------------------------------
-- partido_publico — perfil de partido canônico
-- -----------------------------------------------------------------------------
create view partido_publico as
select
  pf.id,
  pf.nome,
  pf.slug,
  pf.foto_url,
  pf.ativo,
  pa.sigla_atual,
  pa.nome_atual,
  pa.numero_urna,
  pf.source, pf.source_url, pf.synced_at
from profiles pf
join partido pa on pa.profile_id = pf.id
where pf.tipo = 'partido';


-- -----------------------------------------------------------------------------
-- proposicao_publica — projetos de lei e afins
-- -----------------------------------------------------------------------------
create view proposicao_publica as
select
  id,
  casa_origem,
  identificador,
  tipo,
  numero,
  ano,
  ementa,
  tema,
  situacao,
  data_apresentacao,
  inteiro_teor_url,
  inteiro_teor_tem_texto,
  tem_resumo_ia,
  source, source_url, synced_at
from proposicao;


-- -----------------------------------------------------------------------------
-- votacao_publica — votação com a matéria já resolvida
-- -----------------------------------------------------------------------------
-- Placar (sim/nao/abstencao) pode ser NULL quando ainda não extraído do texto
-- (§10, V4) — NULL é "não extraído", nunca zero. `nominal`/`secreta` indicam a
-- completude esperada dos votos individuais.
create view votacao_publica as
select
  vo.id,
  vo.casa,
  vo.data_hora,
  vo.titulo,
  vo.resultado,
  vo.sim,
  vo.nao,
  vo.abstencao,
  vo.secreta,
  vo.nominal,
  pr.id            as proposicao_id,
  pr.identificador as proposicao_identificador,
  pr.ementa        as proposicao_ementa,
  vo.source, vo.source_url, vo.synced_at
from votacao vo
left join proposicao pr on pr.id = vo.proposicao_id;


-- -----------------------------------------------------------------------------
-- voto_nominal_publico — como cada parlamentar votou
-- -----------------------------------------------------------------------------
-- Aqui o partido é o DA ÉPOCA do voto (§4), não o atual — vem do snapshot que a
-- fonte fez no momento. A presidência (Artigo 17) não está aqui: não é posição.
create view voto_nominal_publico as
select
  vn.votacao_id,
  vo.data_hora        as votacao_data_hora,
  pf.id               as parlamentar_id,
  pf.nome             as parlamentar_nome,
  pf.slug             as parlamentar_slug,
  vn.voto,
  vn.partido_sigla_na_epoca,
  vn.grau_atribuicao,
  vn.synced_at
from voto_nominal vn
join votacao vo  on vo.id = vn.votacao_id
join profiles pf on pf.id = vn.perfil_id;


-- -----------------------------------------------------------------------------
-- tramitacao_publica — a cadeia de despachos de cada matéria
-- -----------------------------------------------------------------------------
-- `despacho` é texto de parte interessada (secretaria/relator, §11) — o
-- consumidor jamais o lê como narração neutra.
create view tramitacao_publica as
select
  id,
  proposicao_id,
  sequencia,
  data_hora,
  orgao_sigla,
  descricao,
  despacho,
  source, source_url, synced_at
from tramitacao;


-- -----------------------------------------------------------------------------
-- Leitura pública: só as views curadas, nunca as tabelas de prata.
-- -----------------------------------------------------------------------------
grant select on
  parlamentar_publico,
  partido_publico,
  proposicao_publica,
  votacao_publica,
  voto_nominal_publico,
  tramitacao_publica
to anon, authenticated;

comment on view parlamentar_publico is
  'Camada ouro. Perfil de parlamentar SEM PII (§3.5); partido/UF na data de hoje (§4).';
comment on view voto_nominal_publico is
  'Camada ouro. Voto individual com o partido DA ÉPOCA (§4), não o atual.';
