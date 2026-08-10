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

/** Preferências do usuário, guardadas em user_metadata.prefs. Tudo opcional. */
export interface Prefs {
  temas?: string[];
  partidos?: string[];
  cep?: string;
  idade?: string;
  genero?: string;
  escolaridade?: string;
  renda?: string;
  ocupacao?: string;
  nome?: string;
  /** Marca a migração única de temas/partidos (antigos) para a tabela `follows`. */
  migradoFollows?: boolean;
}

interface AuthCtx {
  session: Session | null;
  carregando: boolean; // enquanto resolve a sessão inicial
  /** true quando o usuário já concluiu o onboarding (guardado no metadata). */
  onboarded: boolean;
  /** Preferências atuais (temas, partidos, dados opt-in). */
  prefs: Prefs;
  /** Envia o código de 6 dígitos para o e-mail. */
  enviarCodigo: (email: string) => Promise<void>;
  /** Verifica o código; em sucesso, a sessão passa a existir. */
  verificarCodigo: (email: string, codigo: string) => Promise<void>;
  /** Marca o onboarding como concluído e salva as preferências no perfil. */
  concluirOnboarding: (prefs: Prefs) => Promise<void>;
  /** Mescla um patch nas preferências (Editar perfil). */
  atualizarPrefs: (patch: Prefs) => Promise<void>;
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

  const prefs: Prefs = (session?.user?.user_metadata?.prefs as Prefs) ?? {};

  const concluirOnboarding = async (novas: Prefs) => {
    // Guarda no metadata do usuário (server-side, cross-device) — não em flag
    // local, para o gate funcionar em qualquer entrada (link mágico ou código).
    const { error } = await supabase.auth.updateUser({ data: { onboarded: true, prefs: novas } });
    if (error) throw error;
  };

  const atualizarPrefs = async (patch: Prefs) => {
    const { error } = await supabase.auth.updateUser({ data: { prefs: { ...prefs, ...patch } } });
    if (error) throw error;
  };

  const sair = async () => { await supabase.auth.signOut(); };

  const onboarded = Boolean(session?.user?.user_metadata?.onboarded);

  return (
    <Ctx.Provider value={{ session, carregando, onboarded, prefs, enviarCodigo, verificarCodigo, concluirOnboarding, atualizarPrefs, sair }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth(): AuthCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error('useAuth precisa estar dentro de <AuthProvider>');
  return c;
}
