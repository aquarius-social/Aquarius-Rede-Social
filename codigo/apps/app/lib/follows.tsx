/**
 * Sistema de "seguir" — fonte única do que o usuário acompanha (parlamentar,
 * partido, comissão, frente, tema). Persistido na tabela `follows` (migration
 * 0018), com RLS por dono. Um contexto (`useFollows`) compartilha o estado entre
 * os botões Seguir (telas de entidade) e o Interesses/Configurações.
 *
 * Atualizações são otimistas (mexe no estado local na hora, persiste em
 * background e reverte em caso de erro). Na primeira carga, faz uma migração
 * única dos temas/partidos antigos (user_metadata.prefs) para `follows`.
 */
import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react';
import { supabase } from './supabase';
import { useAuth } from './auth';

export type TipoFollow = 'parlamentar' | 'partido' | 'comissao' | 'frente' | 'tema';

export interface Follow {
  tipo: TipoFollow;
  ref_id: string;
  rotulo?: string | null;
  meta?: Record<string, unknown> | null;
}

const chave = (tipo: TipoFollow, refId: string) => `${tipo}:${refId}`;

/* ── Acesso ao banco ──────────────────────────────────────────────────────── */

async function carregar(userId: string): Promise<Follow[]> {
  const { data, error } = await supabase
    .from('follows').select('tipo, ref_id, rotulo, meta').eq('user_id', userId);
  if (error) { console.warn('[follows] carregar falhou:', error.message); return []; }
  return (data ?? []) as Follow[];
}

async function inserir(userId: string, fs: Follow[]): Promise<void> {
  if (!fs.length) return;
  const rows = fs.map((f) => ({
    user_id: userId, tipo: f.tipo, ref_id: f.ref_id, rotulo: f.rotulo ?? null, meta: f.meta ?? null,
  }));
  const { error } = await supabase.from('follows').insert(rows);
  // Ignora violação de PK (já seguia) — seguir é idempotente.
  if (error && !/duplicate key|conflict/i.test(error.message)) throw error;
}

async function remover(userId: string, tipo: TipoFollow, refId: string): Promise<void> {
  const { error } = await supabase.from('follows')
    .delete().eq('user_id', userId).eq('tipo', tipo).eq('ref_id', refId);
  if (error) throw error;
}

/* ── Contexto ─────────────────────────────────────────────────────────────── */

interface FollowsCtx {
  follows: Follow[];
  carregando: boolean;
  estaSeguindo: (tipo: TipoFollow, refId: string) => boolean;
  porTipo: (tipo: TipoFollow) => Follow[];
  seguir: (f: Follow) => Promise<void>;
  deixarDeSeguir: (tipo: TipoFollow, refId: string) => Promise<void>;
}

const Ctx = createContext<FollowsCtx | null>(null);

export function FollowsProvider({ children }: { children: ReactNode }) {
  const { session, prefs, atualizarPrefs } = useAuth();
  const userId = session?.user?.id ?? null;
  const [follows, setFollows] = useState<Follow[]>([]);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    let vivo = true;
    if (!userId) { setFollows([]); setCarregando(false); return; }
    (async () => {
      setCarregando(true);
      let fs = await carregar(userId);

      // Migração única: semeia temas/partidos antigos (prefs) como follows.
      if (!prefs.migradoFollows) {
        const sementes: Follow[] = [
          ...(prefs.temas ?? []).map((t) => ({ tipo: 'tema' as const, ref_id: t, rotulo: t })),
          ...(prefs.partidos ?? []).map((p) => ({ tipo: 'partido' as const, ref_id: p, rotulo: p })),
        ].filter((s) => !fs.some((f) => f.tipo === s.tipo && f.ref_id === s.ref_id));
        try {
          if (sementes.length) { await inserir(userId, sementes); fs = [...fs, ...sementes]; }
          await atualizarPrefs({ migradoFollows: true });
        } catch (e) { console.warn('[follows] seed inicial falhou:', (e as Error).message); }
      }

      if (vivo) { setFollows(fs); setCarregando(false); }
    })();
    return () => { vivo = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, prefs.migradoFollows]);

  const estaSeguindo = useCallback(
    (tipo: TipoFollow, refId: string) => follows.some((f) => f.tipo === tipo && f.ref_id === refId),
    [follows],
  );
  const porTipo = useCallback((tipo: TipoFollow) => follows.filter((f) => f.tipo === tipo), [follows]);

  const seguir = useCallback(async (f: Follow) => {
    if (!userId || follows.some((x) => x.tipo === f.tipo && x.ref_id === f.ref_id)) return;
    setFollows((prev) => [...prev, f]);                                   // otimista
    try { await inserir(userId, [f]); }
    catch (e) {
      console.warn('[follows] seguir falhou:', (e as Error).message);
      setFollows((prev) => prev.filter((x) => chave(x.tipo, x.ref_id) !== chave(f.tipo, f.ref_id))); // reverte
    }
  }, [userId, follows]);

  const deixarDeSeguir = useCallback(async (tipo: TipoFollow, refId: string) => {
    if (!userId) return;
    const anterior = follows;
    setFollows((prev) => prev.filter((x) => chave(x.tipo, x.ref_id) !== chave(tipo, refId))); // otimista
    try { await remover(userId, tipo, refId); }
    catch (e) {
      console.warn('[follows] deixar de seguir falhou:', (e as Error).message);
      setFollows(anterior); // reverte
    }
  }, [userId, follows]);

  return (
    <Ctx.Provider value={{ follows, carregando, estaSeguindo, porTipo, seguir, deixarDeSeguir }}>
      {children}
    </Ctx.Provider>
  );
}

export function useFollows(): FollowsCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error('useFollows precisa de <FollowsProvider>');
  return c;
}
