/**
 * Cliente Supabase do app.
 *
 * Lê SOMENTE a camada OURO (views públicas: parlamentar_publico,
 * despesa_publica, emenda_publica). Usa a chave ANON/PUBLISHABLE — pública por
 * natureza, protegida por RLS. A service/secret key jamais entra aqui (é de
 * servidor). Nada é consultado ao vivo na fonte oficial; só o banco curado.
 */
import 'react-native-url-polyfill/auto';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { createClient } from '@supabase/supabase-js';

const url = process.env.EXPO_PUBLIC_SUPABASE_URL;
const anon = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY;

if (!url || !anon) {
  // Falha explícita e cedo — melhor que uma tela vazia sem causa (Metodologia:
  // ausência declarada, nunca silenciosa).
  throw new Error(
    'Faltam EXPO_PUBLIC_SUPABASE_URL / EXPO_PUBLIC_SUPABASE_ANON_KEY. ' +
      'Copie .env.example para .env e preencha com a URL e a chave ANON.',
  );
}

export const supabase = createClient(url, anon, {
  auth: {
    // Persistência da sessão de login (OTP). No web usa localStorage (default);
    // no nativo, AsyncStorage. detectSessionInUrl só faz sentido no web.
    storage: Platform.OS === 'web' ? undefined : AsyncStorage,
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: Platform.OS === 'web',
  },
});
