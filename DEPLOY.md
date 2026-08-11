# Deploy — Aquarius

Três alvos, todos a partir do repo de código `Aquarius-Rede-Social` (monorepo).
Env vars públicas (anon key do Supabase é segura por RLS); a **service key nunca**
vai para cliente/build.

## 1. Admin (Next.js) → Vercel

- **Vercel → Add New → Project** → importar `Aquarius-Rede-Social`.
- **Root Directory:** `codigo/apps/admin` (framework Next.js detectado).
- **Environment Variables:**
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
  - (NÃO definir `NEXT_PUBLIC_ADMIN_DEV_BYPASS` — em produção o gate de RBAC fica ativo.)
- **Pré-requisitos:**
  - Seu usuário em `admin_roles` (migration `0017_admin_roles` aplicada + `user_id` inserido).
  - Depois do deploy: pôr a URL da Vercel em Supabase → Authentication → URL Configuration → Redirect URLs.

## 2. App web (Expo) → Vercel

- **Vercel → Add New → Project** → importar `Aquarius-Rede-Social` (segundo projeto).
- **Root Directory:** `codigo/apps/app`. O `vercel.json` cuida do build
  (`expo export -p web` → `dist/`, com fallback SPA).
- **Environment Variables:**
  - `EXPO_PUBLIC_SUPABASE_URL`
  - `EXPO_PUBLIC_SUPABASE_ANON_KEY`

## 3. App mobile (Expo) → EAS

Config em `codigo/apps/app/eas.json` (perfis development / preview / production) e
`app.json` (bundle IDs `com.aquarius.app` — trocar antes do 1º submit à loja, se quiser).

```
cd codigo/apps/app
npx eas-cli login                 # conta Expo (gratis)
npx eas-cli init                  # grava extra.eas.projectId no app.json
npx eas-cli build -p android --profile preview   # APK instalavel p/ teste
npx eas-cli build -p ios --profile preview        # precisa conta Apple
```

- **Lojas:** Apple Developer (US$99/ano) + Google Play (US$25, unico). Depois
  `npx eas-cli submit -p android|ios`.
- As env `EXPO_PUBLIC_*` do build nativo entram como **EAS secrets** (`eas secret:create`)
  ou em `eas.json`.

## CI

`.github/workflows/ci.yml` roda testes + tsc + lint. A Vercel faz deploy automático a
cada push na `main` (uma vez conectada). O EAS é disparado manualmente (ou via EAS Workflows).
