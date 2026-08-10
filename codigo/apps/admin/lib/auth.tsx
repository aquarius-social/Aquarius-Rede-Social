'use client';
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import type { Session } from '@supabase/supabase-js';
import { supabase } from './supabase';

interface AuthCtx {
  session: Session | null;
  carregando: boolean;     // resolvendo sessão + papel
  isAdmin: boolean;        // consta em admin_roles
  papel: string | null;    // papel do admin (superadmin, editor_chefe, …)
  enviarLink: (email: string) => Promise<void>;
  sair: () => Promise<void>;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [papel, setPapel] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);

  // Verifica se o usuário logado é admin (lê a própria linha em admin_roles, via RLS).
  const checarPapel = async (s: Session | null) => {
    if (!s) { setPapel(null); return; }
    const { data } = await supabase.from('admin_roles').select('papel').eq('user_id', s.user.id).maybeSingle();
    setPapel((data as { papel?: string } | null)?.papel ?? null);
  };

  useEffect(() => {
    let vivo = true;
    supabase.auth.getSession().then(async ({ data }) => {
      if (!vivo) return;
      setSession(data.session);
      await checarPapel(data.session);
      setCarregando(false);
    });
    const { data: sub } = supabase.auth.onAuthStateChange(async (_e, s) => {
      setSession(s);
      await checarPapel(s);
    });
    return () => { vivo = false; sub.subscription.unsubscribe(); };
  }, []);

  const enviarLink = async (email: string) => {
    const { error } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      options: { emailRedirectTo: typeof window !== 'undefined' ? window.location.origin : undefined },
    });
    if (error) throw error;
  };

  const sair = async () => { await supabase.auth.signOut(); };

  return (
    <Ctx.Provider value={{ session, carregando, isAdmin: papel != null, papel, enviarLink, sair }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth(): AuthCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error('useAuth precisa de <AuthProvider>');
  return c;
}
