import { createClient } from '@supabase/supabase-js';

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!url || !anon) {
  throw new Error(
    'Faltam NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY em .env.local do admin.',
  );
}

// Admin lê as views ouro (contagens/estado). Ações privilegiadas virão via
// server actions com service_role — nunca a chave secreta no cliente.
export const supabase = createClient(url, anon, { auth: { persistSession: false } });
