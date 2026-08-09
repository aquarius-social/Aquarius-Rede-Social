/**
 * Consultas à camada OURO do Supabase. Só views públicas; agregação de dinheiro
 * feita no cliente sobre um recorte limitado (despesas do último ano fechado +
 * todas as emendas do parlamentar, ambos volumes pequenos por pessoa).
 *
 * Princípio da Metodologia: todo dado servido carrega fonte + frescor, e estágio
 * de emenda JAMAIS é somado com outro (empenhado ≠ pago). Aqui somamos PAGO com
 * PAGO — nunca cruzamos estágios.
 */
import { supabase } from './supabase';
import { reais, reaisCompacto } from './formato';


export interface Parlamentar {
  id: string;
  nome: string;
  slug: string;
  foto_url: string | null;
  uf_atual: string | null;
  ocupacao_atual: string | null;
  partido_sigla_atual: string | null;
  partido_id: string | null;
  casa_atual: string | null; // 'camara' | 'senado'
  situacao: string | null;   // 'em_exercicio' | 'licenciado' | 'suplente_em_exercicio'
  // §6.4 — transição suplente↔titular (só quando aplicável)
  titular_profile_id: string | null;
  titular_nome: string | null;
  assumiu_em: string | null;   // suplente: quando assumiu
  causa: string | null;        // suplente: causa do afastamento (procedural)
  suplente_profile_id: string | null;
  suplente_nome: string | null;
  suplente_desde: string | null; // titular licenciado: desde quando o suplente cobre
  legislatura: number | null;
  source: string;
  source_url: string | null;
  synced_at: string;
}

export interface Partido {
  id: string;
  nome: string;
  slug: string;
  sigla_atual: string;
  nome_atual: string;
  numero_urna: number | null;
  source: string;
  source_url: string | null;
  synced_at: string;
}

export interface AreaGasto {
  funcao: string;
  total: number;
}

export interface ResumoEmendasPartido {
  totalPago: number;
  totalEmpenhado: number;
  quantidade: number;
  areas: AreaGasto[]; // por função, desc por total
  frescor: string | null;
}

export interface Lancamento {
  data: string | null;        // data_documento (AAAA-MM-DD)
  fornecedor: string | null;
  cnpjCpf: string | null;
  valorLiquido: number;
  urlDocumento: string | null; // nota fiscal oficial na Câmara
}

export interface CategoriaGasto {
  tipo: string;
  total: number;
  itens: Lancamento[]; // lançamentos individuais, desc por valor
}

export interface ResumoDespesas {
  totalLiquido: number;         // mandato inteiro
  lancamentos: number;
  categorias: CategoriaGasto[]; // ordenadas desc por total
  anual: { ano: number; total: number }[]; // por ano, asc
  frescor: string | null;
}

export interface EmendaLinha {
  id: string;
  codigo: string | null;
  ano: number;
  finalidade: string | null;  // funcao
  subfuncao: string | null;
  uf: string | null;          // localidade_gasto
  empenhado: number | null;
  liquidado: number | null;
  pago: number | null;
  restoInscrito: number | null;
  restoPago: number | null;
}

export interface ResumoEmendas {
  totalPago: number;
  totalEmpenhado: number;
  quantidade: number;
  linhas: EmendaLinha[]; // ordenadas desc por pago
  frescor: string | null;
}

export interface Comissao {
  id: string;
  nome: string;
  sigla: string | null;
  slug: string;
  source: string;
  source_url: string | null;
  synced_at: string;
}

export interface Frente {
  id: string;
  nome: string;
  slug: string;
  source: string;
  source_url: string | null;
  synced_at: string;
}

export interface Contagens {
  parlamentares: number;
  partidos: number;
  comissoes: number;
  frentes: number;
}

/** Contagens para o hub Explorar (só o que a camada ouro expõe ao anon). */
export async function contagens(): Promise<Contagens> {
  const head = { count: 'exact' as const, head: true };
  const [p, pa, co, fr] = await Promise.all([
    supabase.from('parlamentar_publico').select('*', head),
    supabase.from('partido_publico').select('*', head),
    supabase.from('comissao_publica').select('*', head),
    supabase.from('frente_publica').select('*', head),
  ]);
  return {
    parlamentares: p.count ?? 0,
    partidos: pa.count ?? 0,
    comissoes: co.count ?? 0,
    frentes: fr.count ?? 0,
  };
}

export async function listarComissoes(): Promise<Comissao[]> {
  const { data, error } = await supabase
    .from('comissao_publica')
    .select('*')
    .order('sigla', { ascending: true });
  if (error) throw error;
  return (data ?? []) as Comissao[];
}

export async function listarFrentes(): Promise<Frente[]> {
  const { data, error } = await supabase
    .from('frente_publica')
    .select('*')
    .order('nome', { ascending: true })
    .limit(2000);
  if (error) throw error;
  return (data ?? []) as Frente[];
}

export async function obterComissao(id: string): Promise<Comissao | null> {
  const { data, error } = await supabase
    .from('comissao_publica')
    .select('*')
    .eq('id', id)
    .maybeSingle();
  if (error) throw error;
  return (data as Comissao) ?? null;
}

export async function obterFrente(id: string): Promise<Frente | null> {
  const { data, error } = await supabase
    .from('frente_publica')
    .select('*')
    .eq('id', id)
    .maybeSingle();
  if (error) throw error;
  return (data as Frente) ?? null;
}

export async function listarPartidos(): Promise<Partido[]> {
  const { data, error } = await supabase
    .from('partido_publico')
    .select('*')
    .order('sigla_atual', { ascending: true });
  if (error) throw error;
  return (data ?? []) as Partido[];
}

export async function listarParlamentares(busca?: string): Promise<Parlamentar[]> {
  let q = supabase
    .from('parlamentar_publico')
    .select('*')
    .order('nome', { ascending: true })
    .limit(600);
  if (busca && busca.trim()) q = q.ilike('nome', `%${busca.trim()}%`);
  const { data, error } = await q;
  if (error) throw error;
  return (data ?? []) as Parlamentar[];
}

export async function obterParlamentar(id: string): Promise<Parlamentar | null> {
  const { data, error } = await supabase
    .from('parlamentar_publico')
    .select('*')
    .eq('id', id)
    .maybeSingle();
  if (error) throw error;
  return (data as Parlamentar) ?? null;
}

export async function resumoDespesas(perfilId: string): Promise<ResumoDespesas> {
  // Mandato inteiro (a base de despesas cobre 2023–2026); sem filtro de ano.
  const { data, error } = await supabase
    .from('despesa_publica')
    .select('tipo_despesa, ano, valor_liquido, data_documento, fornecedor_nome, fornecedor_cnpj_cpf, url_documento, synced_at')
    .eq('perfil_id', perfilId)
    .limit(8000);
  if (error) throw error;
  const linhas = data ?? [];
  const grupos = new Map<string, { total: number; itens: Lancamento[] }>();
  const porAno = new Map<number, number>();
  let total = 0;
  let frescor: string | null = null;
  for (const l of linhas as any[]) {
    const v = Number(l.valor_liquido) || 0;
    total += v;
    const t = l.tipo_despesa || 'Outros';
    const g = grupos.get(t) ?? { total: 0, itens: [] };
    g.total += v;
    g.itens.push({
      data: l.data_documento ?? null,
      fornecedor: l.fornecedor_nome ?? null,
      cnpjCpf: l.fornecedor_cnpj_cpf ?? null,
      valorLiquido: v,
      urlDocumento: l.url_documento ?? null,
    });
    grupos.set(t, g);
    const ano = Number(l.ano) || 0;
    if (ano) porAno.set(ano, (porAno.get(ano) ?? 0) + v);
    if (l.synced_at) frescor = l.synced_at;
  }
  const categorias = [...grupos.entries()]
    .map(([tipo, g]) => ({ tipo, total: g.total, itens: g.itens.sort((a, b) => b.valorLiquido - a.valorLiquido) }))
    .sort((a, b) => b.total - a.total);
  const anual = [...porAno.entries()].map(([ano, tot]) => ({ ano, total: tot })).sort((a, b) => a.ano - b.ano);
  return { totalLiquido: total, lancamentos: linhas.length, categorias, anual, frescor };
}

export async function resumoEmendas(perfilId: string): Promise<ResumoEmendas> {
  const { data, error } = await supabase
    .from('emenda_publica')
    .select('id, codigo_emenda, ano, funcao, subfuncao, localidade_gasto, valor_empenhado, valor_liquidado, valor_pago, valor_resto_inscrito, valor_resto_pago, synced_at')
    .eq('autor_profile_id', perfilId)
    .limit(2000);
  if (error) throw error;
  const linhas = (data ?? []) as any[];
  let pago = 0;
  let empenhado = 0;
  let frescor: string | null = null;
  const num = (x: any) => (x === null || x === undefined ? null : Number(x));
  const out: EmendaLinha[] = linhas.map((l) => {
    pago += Number(l.valor_pago) || 0;
    empenhado += Number(l.valor_empenhado) || 0;
    if (l.synced_at) frescor = l.synced_at;
    return {
      id: l.id,
      codigo: l.codigo_emenda ?? null,
      ano: l.ano,
      finalidade: l.funcao,
      subfuncao: l.subfuncao ?? null,
      uf: l.localidade_gasto,
      empenhado: num(l.valor_empenhado),
      liquidado: num(l.valor_liquidado),
      pago: num(l.valor_pago),
      restoInscrito: num(l.valor_resto_inscrito),
      restoPago: num(l.valor_resto_pago),
    };
  });
  out.sort((a, b) => (b.pago ?? 0) - (a.pago ?? 0));
  return { totalPago: pago, totalEmpenhado: empenhado, quantidade: out.length, linhas: out, frescor };
}

export async function obterPartido(sigla: string): Promise<Partido | null> {
  const { data, error } = await supabase
    .from('partido_publico')
    .select('*')
    .eq('sigla_atual', sigla)
    .maybeSingle();
  if (error) throw error;
  return (data as Partido) ?? null;
}

export async function membrosDoPartido(sigla: string): Promise<Parlamentar[]> {
  const { data, error } = await supabase
    .from('parlamentar_publico')
    .select('*')
    .eq('partido_sigla_atual', sigla)
    .order('nome', { ascending: true })
    .limit(600);
  if (error) throw error;
  return (data ?? []) as Parlamentar[];
}

/** Agrega as emendas de TODOS os membros do partido (uma consulta com IN). */
export async function resumoEmendasPartido(membroIds: string[]): Promise<ResumoEmendasPartido> {
  if (membroIds.length === 0) return { totalPago: 0, totalEmpenhado: 0, quantidade: 0, areas: [], frescor: null };
  const { data, error } = await supabase
    .from('emenda_publica')
    .select('funcao, valor_pago, valor_empenhado, synced_at')
    .in('autor_profile_id', membroIds)
    .limit(20000);
  if (error) throw error;
  const linhas = (data ?? []) as any[];
  const porFuncao = new Map<string, number>();
  let pago = 0;
  let empenhado = 0;
  let frescor: string | null = null;
  for (const l of linhas) {
    const p = Number(l.valor_pago) || 0;
    pago += p;
    empenhado += Number(l.valor_empenhado) || 0;
    const f = l.funcao || 'Não informada';
    porFuncao.set(f, (porFuncao.get(f) ?? 0) + p);
    if (l.synced_at) frescor = l.synced_at;
  }
  const areas = [...porFuncao.entries()]
    .map(([funcao, total]) => ({ funcao, total }))
    .sort((a, b) => b.total - a.total);
  return { totalPago: pago, totalEmpenhado: empenhado, quantidade: linhas.length, areas, frescor };
}

/* ── Feed v1: destaques de dinheiro REAIS (sem IA) ─────────────────────────
 * Posts factuais em terceira pessoa a partir das maiores emendas empenhadas.
 * Não misturamos estágios (empenhado ≠ pago). Autoria resolvida na fonte.
 */
export interface FeedPost {
  id: string;
  fonte: string;
  autorId: string | null;
  autorNome: string;
  autorSigla: string | null;
  autorUf: string | null;
  headline: string;
  body: string;
  valorEmpenhado: number;
  valorPago: number;
  area: string;
  local: string | null;
  ano: number;
  codigo: string | null;
  syncedAt: string | null;
}

export async function destaquesFeed(limite = 24): Promise<FeedPost[]> {
  const { data, error } = await supabase
    .from('emenda_publica')
    .select('id, codigo_emenda, ano, funcao, localidade_gasto, valor_empenhado, valor_pago, autor_profile_id, synced_at')
    .not('autor_profile_id', 'is', null)
    .order('valor_empenhado', { ascending: false })
    .limit(limite);
  if (error) throw error;
  const linhas = (data ?? []) as any[];

  const ids = [...new Set(linhas.map((l) => l.autor_profile_id).filter(Boolean))] as string[];
  const autores = new Map<string, any>();
  if (ids.length) {
    const { data: as } = await supabase
      .from('parlamentar_publico')
      .select('id, nome, partido_sigla_atual, uf_atual')
      .in('id', ids);
    for (const a of (as ?? []) as any[]) autores.set(a.id, a);
  }

  return linhas.map((l) => {
    const a = autores.get(l.autor_profile_id);
    const nome = a?.nome ?? 'Autoria em resolução';
    const sigla = a?.partido_sigla_atual ?? null;
    const uf = a?.uf_atual ?? null;
    const area = l.funcao || 'Área não informada';
    // Localidades genéricas do Portal (MÚLTIPLO/NACIONAL/EXTERIOR) não viram
    // "em X" — só municípios/UF específicos entram na frase.
    const localBruto = (l.localidade_gasto || '').trim();
    const generica = /^(m[uú]ltiplo|nacional|exterior|n[aã]o informad|diversos)/i.test(localBruto);
    const local = localBruto && !generica ? localBruto : null;
    const emp = Number(l.valor_empenhado) || 0;
    const pago = Number(l.valor_pago) || 0;
    const onde = local ? ` em ${local}` : '';
    const headline = `Emenda de ${reaisCompacto(emp)} para ${area}${onde}`;
    const body = `O Portal da Transparência registra a emenda${l.codigo_emenda ? ' nº ' + l.codigo_emenda : ''} de ${nome}` +
      `${sigla ? ` (${sigla}${uf ? '-' + uf : ''})` : ''}, com ${reais(emp)} empenhados para ${area}${onde} em ${l.ano}.`;
    return {
      id: l.id, fonte: 'Portal da Transparência',
      autorId: l.autor_profile_id ?? null, autorNome: nome, autorSigla: sigla, autorUf: uf,
      headline, body, valorEmpenhado: emp, valorPago: pago,
      area, local, ano: l.ano, codigo: l.codigo_emenda ?? null, syncedAt: l.synced_at ?? null,
    };
  });
}

/* ── Agenda / Calendário (área de eventos, view evento_publico) ────────────── */
export interface Evento {
  id: string;
  casa: string;               // 'camara' | 'senado'
  tipo: string | null;
  titulo: string | null;
  inicio: string | null;      // data_hora_inicio (ISO, hora de Brasília)
  fim: string | null;
  situacao: string | null;    // Agendada / Realizada / Cancelada
  orgaoSigla: string | null;
  orgaoNome: string | null;
  local: string | null;
  url: string | null;
  source: string;
  sourceUrl: string | null;
  syncedAt: string | null;
}

export async function listarEventos(casa?: 'camara' | 'senado', limite = 80): Promise<Evento[]> {
  let q = supabase
    .from('evento_publico')
    .select('id, casa, tipo, titulo, data_hora_inicio, data_hora_fim, situacao, orgao_sigla, orgao_nome, local, url, source, source_url, synced_at')
    .order('data_hora_inicio', { ascending: false })
    .limit(limite);
  if (casa) q = q.eq('casa', casa);
  const { data, error } = await q;
  if (error) throw error;
  return ((data ?? []) as any[]).map((e) => ({
    id: e.id, casa: e.casa, tipo: e.tipo ?? null, titulo: e.titulo ?? null,
    inicio: e.data_hora_inicio ?? null, fim: e.data_hora_fim ?? null, situacao: e.situacao ?? null,
    orgaoSigla: e.orgao_sigla ?? null, orgaoNome: e.orgao_nome ?? null, local: e.local ?? null,
    url: e.url ?? null, source: e.source, sourceUrl: e.source_url ?? null, syncedAt: e.synced_at ?? null,
  }));
}
