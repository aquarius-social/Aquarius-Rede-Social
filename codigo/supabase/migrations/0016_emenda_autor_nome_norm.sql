-- =============================================================================
-- Aquarius · §6.3 — casar autor de emenda por NOME sem acento (furo do ilike)
-- =============================================================================
-- A fonte (Portal da Transparência) grava o autor SEM acento e em MAIÚSCULAS
-- ("JOAO CARLOS BACELAR"), enquanto o cadastro é acentuado ("João Carlos
-- Bacelar"). O `ilike` do PostgREST ignora caixa, mas NÃO ignora acento — então
-- uma busca pelo nome correto podia devolver VAZIO enganoso (modo de falha 8).
--
-- Correção na RAIZ: a view ouro passa a expor `autor_nome_norm` — o nome em
-- minúsculas e sem acento — e a ferramenta `emendas_por_autor_nome` casa sobre
-- essa coluna (o termo de busca é normalizado do mesmo jeito no serviço).
-- Usa `translate` (IMUTÁVEL, sem depender da extensão unaccent).
--
-- Correção por migration NOVA, recriando só a view (regra 5); a tabela `emenda`
-- não muda. `create or replace view` adiciona a coluna ao FIM da projeção.
-- =============================================================================

create or replace view emenda_publica as
select
  id, codigo_emenda, ano, tipo, numero,
  autor_nome, autor_profile_id,
  localidade_gasto, funcao, subfuncao,
  valor_empenhado, valor_liquidado, valor_pago,
  valor_resto_inscrito, valor_resto_cancelado, valor_resto_pago,
  source, source_url, synced_at,
  translate(lower(coalesce(autor_nome, '')),
            'áàâãäéèêëíìîïóòôõöúùûüç',
            'aaaaaeeeeiiiiooooouuuuc') as autor_nome_norm
from emenda;

grant select on emenda_publica to anon, authenticated;

comment on view emenda_publica is
  'Camada ouro. Emendas por estágio orçamentário (§13, nunca somar estágios). '
  'autor_nome_norm = nome sem acento/caixa, para casar autor por nome (§6.3).';
