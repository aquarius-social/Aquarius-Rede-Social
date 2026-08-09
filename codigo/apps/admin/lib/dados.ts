import { supabase } from './supabase';

export interface Contagens {
  parlamentares: number;
  partidos: number;
  comissoes: number;
  frentes: number;
  emendas: number;
  eventos: number;
}

/** Contagens reais das views ouro — o que o admin pode afirmar com verdade. */
export async function contagens(): Promise<Contagens> {
  const head = { count: 'exact' as const, head: true };
  const [pa, pt, co, fr, em, ev] = await Promise.all([
    supabase.from('parlamentar_publico').select('*', head),
    supabase.from('partido_publico').select('*', head),
    supabase.from('comissao_publica').select('*', head),
    supabase.from('frente_publica').select('*', head),
    supabase.from('emenda_publica').select('*', head),
    supabase.from('evento_publico').select('*', head),
  ]);
  return {
    parlamentares: pa.count ?? 0,
    partidos: pt.count ?? 0,
    comissoes: co.count ?? 0,
    frentes: fr.count ?? 0,
    emendas: em.count ?? 0,
    eventos: ev.count ?? 0,
  };
}

/** Frescor: data de sincronização mais recente vista nas emendas. */
export async function ultimoSync(): Promise<string | null> {
  const { data } = await supabase
    .from('emenda_publica')
    .select('synced_at')
    .order('synced_at', { ascending: false })
    .limit(1)
    .maybeSingle();
  return (data as { synced_at?: string } | null)?.synced_at ?? null;
}
