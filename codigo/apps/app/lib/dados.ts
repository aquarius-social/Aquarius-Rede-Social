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

export const ANO_DESPESAS = 2025; // último ano-calendário fechado

export interface Parlamentar {
  id: string;
  nome: string;
  slug: string;
  foto_url: string | null;
  uf_atual: string | null;
  ocupacao_atual: string | null;
  partido_sigla_atual: string | null;
  legislatura: number | null;
  source: string;
  source_url: string | null;
  synced_at: string;
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
  ano: number;
  totalLiquido: number;
  lancamentos: number;
  categorias: CategoriaGasto[]; // ordenadas desc por total
  mensal: number[]; // 12 posições (jan..dez) em reais
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
  const { data, error } = await supabase
    .from('despesa_publica')
    .select('tipo_despesa, mes, valor_liquido, data_documento, fornecedor_nome, fornecedor_cnpj_cpf, url_documento, synced_at')
    .eq('perfil_id', perfilId)
    .eq('ano', ANO_DESPESAS)
    .limit(3000);
  if (error) throw error;
  const linhas = data ?? [];
  const grupos = new Map<string, { total: number; itens: Lancamento[] }>();
  const mensal = new Array(12).fill(0) as number[];
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
    const mi = (Number(l.mes) || 1) - 1;
    if (mi >= 0 && mi < 12) mensal[mi] += v;
    if (l.synced_at) frescor = l.synced_at;
  }
  const categorias = [...grupos.entries()]
    .map(([tipo, g]) => ({ tipo, total: g.total, itens: g.itens.sort((a, b) => b.valorLiquido - a.valorLiquido) }))
    .sort((a, b) => b.total - a.total);
  return { ano: ANO_DESPESAS, totalLiquido: total, lancamentos: linhas.length, categorias, mensal, frescor };
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
