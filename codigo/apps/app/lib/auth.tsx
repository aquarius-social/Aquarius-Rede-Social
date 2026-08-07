/**
 * Contexto de autenticação — login por OTP de e-mail via Supabase Auth.
 *
 * Decisão travada (CLAUDE.md): OTP por e-mail/SMS primeiro; WhatsApp em paralelo
 * (habilitação Meta é lenta). Aqui implementamos o e-mail, que funciona só com o
 * Supabase (sem provedor externo). SMS/WhatsApp entram depois.
 */
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import type { Session } from '@supabase/supabase-js';
import { supabase } from './supabase';

export interface PrefsOnboarding {
  temas: string[];
  partidos: string[];
  cep?: string;
  idade?: string;
  genero?: string;
}

interface AuthCtx {
  session: Session | null;
  carregando: boolean; // enquanto resolve a sessão inicial
  /** true quando o usuário já concluiu o onboarding (guardado no metadata). */
  onboarded: boolean;
  /** Envia o código de 6 dígitos para o e-mail. */
  enviarCodigo: (email: string) => Promise<void>;
  /** Verifica o código; em sucesso, a sessão passa a existir. */
  verificarCodigo: (email: string, codigo: string) => Promise<void>;
  /** Marca o onboarding como concluído e salva as preferências no perfil. */
  concluirOnboarding: (prefs: PrefsOnboarding) => Promise<void>;
  sair: () => Promise<void>;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    let vivo = true;
    supabase.auth.getSession().then(({ data }) => {
      if (!vivo) return;
      setSession(data.session);
      setCarregando(false);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_evento, s) => {
      setSession(s);
    });
    return () => { vivo = false; sub.subscription.unsubscribe(); };
  }, []);

  const enviarCodigo = async (email: string) => {
    const { error } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      options: { shouldCreateUser: true },
    });
    if (error) throw error;
  };

  const verificarCodigo = async (email: string, codigo: string) => {
    const { error } = await supabase.auth.verifyOtp({
      email: email.trim(),
      token: codigo.trim(),
      type: 'email',
    });
    if (error) throw error;
  };

  const concluirOnboarding = async (prefs: PrefsOnboarding) => {
    // Guarda no metadata do usuário (server-side, cross-device) — não em flag
    // local, para o gate funcionar em qualquer entrada (link mágico ou código).
    const { error } = await supabase.auth.updateUser({ data: { onboarded: true, prefs } });
    if (error) throw error;
  };

  const sair = async () => { await supabase.auth.signOut(); };

  const onboarded = Boolean(session?.user?.user_metadata?.onboarded);

  return (
    <Ctx.Provider value={{ session, carregando, onboarded, enviarCodigo, verificarCodigo, concluirOnboarding, sair }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth(): AuthCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error('useAuth precisa estar dentro de <AuthProvider>');
  return c;
}
