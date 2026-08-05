# Aquarius — app (Expo)

Primeiro vertical: **perfil parlamentar com o dinheiro** (despesas da cota
parlamentar + emendas), lendo a camada OURO do Supabase (views públicas, RLS).

## Estrutura

- `app/` — telas (Expo Router, roteamento por arquivo)
  - `index.tsx` — lista/busca de parlamentares (`parlamentar_publico`)
  - `parlamentar/[id].tsx` — perfil + dinheiro (`despesa_publica`, `emenda_publica`)
- `lib/` — `supabase` (cliente, chave anon), `dados` (consultas + agregação),
  `formato` (dinheiro/data), `tema` (tokens, espelho de `packages/ui`)
- `components/base.tsx` — Avatar, Chip, StatCell, Secao (fiéis ao protótipo)

## Rodar

1. Credenciais **públicas** (a chave ANON é segura no cliente; a service key NÃO
   entra aqui):
   ```
   cp .env.example .env
   ```
   Preencha `EXPO_PUBLIC_SUPABASE_ANON_KEY` com a chave **anon/publishable** do
   projeto (Supabase → Settings → API Keys → publishable/anon).

2. Instalar e abrir no navegador (mais rápido para conferir):
   ```
   npm install
   npm run web
   ```
   Ou `npm start` e escaneie o QR com o app **Expo Go** (celular).

## Notas de disciplina

- Lê SÓ as views ouro (curadas, sem PII, §3.5). Nada ao vivo na fonte.
- Toda seção cita **fonte + frescor** (`synced_at`).
- Estágios de emenda (empenhado/pago) **nunca** somados entre si (§13).
- `tema.ts` é cópia dos tokens de `packages/ui` só para este 1º vertical rodar
  sem configurar o monorepo no Metro — trocar por `@aquarius/ui` depois.
