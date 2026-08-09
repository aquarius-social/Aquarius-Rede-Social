'use client';
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { ADM_DARK, ADM_LIGHT, type Tema } from './tema';

type Modo = 'dark' | 'light';
interface Ctx { theme: Tema; mode: Modo; toggle: () => void }

const ThemeCtx = createContext<Ctx>({ theme: ADM_DARK, mode: 'dark', toggle: () => {} });

export function AdmThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<Modo>('dark'); // operacional: dark por padrão

  useEffect(() => {
    const salvo = typeof window !== 'undefined' ? window.localStorage.getItem('adm.mode') : null;
    if (salvo === 'light' || salvo === 'dark') setMode(salvo);
  }, []);

  const toggle = () => setMode((m) => {
    const nv = m === 'dark' ? 'light' : 'dark';
    if (typeof window !== 'undefined') window.localStorage.setItem('adm.mode', nv);
    return nv;
  });

  const theme = mode === 'dark' ? ADM_DARK : ADM_LIGHT;
  return <ThemeCtx.Provider value={{ theme, mode, toggle }}>{children}</ThemeCtx.Provider>;
}

export const useAdmTheme = () => useContext(ThemeCtx);
