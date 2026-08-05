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

export interface CategoriaGasto {
  tipo: string;
  total: number;
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
  ano: number;
  finalidade: string | null;
  uf: string | null;
  pago: number | null;
  empenhado: number | null;
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
    .select('tipo_despesa, mes, valor_liquido, synced_at')
    .eq('perfil_id', perfilId)
    .eq('ano', ANO_DESPESAS)
    .limit(3000);
  if (error) throw error;
  const linhas = data ?? [];
  const porTipo = new Map<string, number>();
  const mensal = new Array(12).fill(0) as number[];
  let total = 0;
  let frescor: string | null = null;
  for (const l of linhas as any[]) {
    const v = Number(l.valor_liquido) || 0;
    total += v;
    const t = l.tipo_despesa || 'Outros';
    porTipo.set(t, (porTipo.get(t) ?? 0) + v);
    const mi = (Number(l.mes) || 1) - 1;
    if (mi >= 0 && mi < 12) mensal[mi] += v;
    if (l.synced_at) frescor = l.synced_at;
  }
  const categorias = [...porTipo.entries()]
    .map(([tipo, tot]) => ({ tipo, total: tot }))
    .sort((a, b) => b.total - a.total);
  return { ano: ANO_DESPESAS, totalLiquido: total, lancamentos: linhas.length, categorias, mensal, frescor };
}

export async function resumoEmendas(perfilId: string): Promise<ResumoEmendas> {
  const { data, error } = await supabase
    .from('emenda_publica')
    .select('id, ano, funcao, localidade_gasto, valor_pago, valor_empenhado, synced_at')
    .eq('autor_profile_id', perfilId)
    .limit(2000);
  if (error) throw error;
  const linhas = (data ?? []) as any[];
  let pago = 0;
  let empenhado = 0;
  let frescor: string | null = null;
  const out: EmendaLinha[] = linhas.map((l) => {
    pago += Number(l.valor_pago) || 0;
    empenhado += Number(l.valor_empenhado) || 0;
    if (l.synced_at) frescor = l.synced_at;
    return {
      id: l.id,
      ano: l.ano,
      finalidade: l.funcao,
      uf: l.localidade_gasto,
      pago: l.valor_pago === null ? null : Number(l.valor_pago),
      empenhado: l.valor_empenhado === null ? null : Number(l.valor_empenhado),
    };
  });
  out.sort((a, b) => (b.pago ?? 0) - (a.pago ?? 0));
  return { totalPago: pago, totalEmpenhado: empenhado, quantidade: out.length, linhas: out, frescor };
}
