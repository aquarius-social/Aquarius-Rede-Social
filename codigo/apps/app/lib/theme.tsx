/**
 * Provider de tema do app (claro/escuro). Envolve a árvore em `_layout.tsx`.
 *
 * Preferência do usuário: 'auto' (segue o sistema), 'light' ou 'dark',
 * persistida em AsyncStorage. Até carregar, assume 'auto' (evita flash).
 * Componentes consomem via `useTema()` (paleta) e telas de estilo via
 * `useTemaEstilos(criarSt)`. O controle (toggle) usa `useTemaCtrl()`.
 */
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useColorScheme } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { TEMA_CLARO, TEMA_ESCURO, type Tema } from './tema';

export type Modo = 'light' | 'dark';
export type PrefTema = 'auto' | Modo;

const CHAVE = 'aq.tema.pref';

interface TemaCtx {
  cor: Tema;          // paleta ativa
  modo: Modo;         // efetivo (auto resolvido pelo sistema)
  pref: PrefTema;     // escolha do usuário
  definir: (p: PrefTema) => void;
  alternar: () => void; // atalho claro↔escuro (fixa a escolha)
}

const Ctx = createContext<TemaCtx | null>(null);

export function TemaProvider({ children }: { children: ReactNode }) {
  const sistema = useColorScheme(); // 'light' | 'dark' | null
  const [pref, setPref] = useState<PrefTema>('auto');

  // Carrega a preferência persistida uma vez.
  useEffect(() => {
    let vivo = true;
    AsyncStorage.getItem(CHAVE)
      .then((v) => { if (vivo && (v === 'auto' || v === 'light' || v === 'dark')) setPref(v); })
      .catch(() => {});
    return () => { vivo = false; };
  }, []);

  const definir = (p: PrefTema) => {
    setPref(p);
    AsyncStorage.setItem(CHAVE, p).catch(() => {});
  };

  const modo: Modo = pref === 'auto' ? (sistema === 'dark' ? 'dark' : 'light') : pref;
  const alternar = () => definir(modo === 'dark' ? 'light' : 'dark');
  const cor = modo === 'dark' ? TEMA_ESCURO : TEMA_CLARO;

  const valor = useMemo<TemaCtx>(() => ({ cor, modo, pref, definir, alternar }), [cor, modo, pref]);
  return <Ctx.Provider value={valor}>{children}</Ctx.Provider>;
}

function usarCtx(): TemaCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error('useTema precisa de <TemaProvider>');
  return c;
}

/** Paleta ativa. Uso mais comum nos componentes. */
export function useTema(): Tema {
  return usarCtx().cor;
}

/** Controle do tema (modo efetivo, preferência e setters) — para o toggle. */
export function useTemaCtrl(): Omit<TemaCtx, 'cor'> {
  const { modo, pref, definir, alternar } = usarCtx();
  return { modo, pref, definir, alternar };
}

/**
 * Açúcar para telas: devolve a paleta e o StyleSheet já memoizado a partir de
 * uma fábrica `criar(cor)`. Ex.:
 *   const criarSt = (cor: Tema) => StyleSheet.create({ ... });
 *   const { cor, st } = useTemaEstilos(criarSt);
 */
export function useTemaEstilos<T>(criar: (cor: Tema) => T): { cor: Tema; st: T } {
  const cor = useTema();
  const st = useMemo(() => criar(cor), [cor]);
  return { cor, st };
}
