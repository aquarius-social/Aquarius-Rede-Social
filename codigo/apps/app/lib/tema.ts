/**
 * Tema do app — ESPELHO de `packages/ui/src/tokens.ts` (a fonte da verdade).
 *
 * Duplicado aqui só para o primeiro vertical rodar sem configurar resolução de
 * monorepo no Metro. TODO: trocar por `import { temaApp } from '@aquarius/ui'`
 * quando o workspace estiver ligado. Os valores são cópia literal — não
 * reinterpretar (o protótipo manda no observável).
 */
export const cor = {
  navy: '#0D2B5E',
  blue: '#1A4FA0',
  sky: '#2E7DD1',
  skySoft: '#5FA0E0',
  ink: '#0A1F45',
  white: '#FFFFFF',
  gold: '#C8A400',
  pos: '#1E8E5C',
  neg: '#C63A3A',
  warn: '#D97B2E',
  abst: '#6B7280',
  surface: '#F4F7FC',
  light: '#E8F1FB',
  muted: '#4A6090',
  mutedSoft: '#7B8FB5',
  border: 'rgba(13,43,94,0.12)',
  borderStrong: 'rgba(13,43,94,0.22)',
} as const;

export const raio = {
  pilula: 9999,
  card: 14,
  cardGrande: 16,
  cardPequeno: 10,
  input: 10,
} as const;

/**
 * Tipografia — Inter (protótipo: DESIGN-TOKENS.md). No React Native cada peso é
 * uma FAMÍLIA distinta (fontWeight sozinho não muda a fonte em fontes custom),
 * então mapeamos peso → família carregada por @expo-google-fonts/inter.
 *   r  400  ·  m  500  ·  sb 600  ·  b  700  ·  xb 800
 */
export const fonte = {
  r: 'Inter_400Regular',
  m: 'Inter_500Medium',
  sb: 'Inter_600SemiBold',
  b: 'Inter_700Bold',
  xb: 'Inter_800ExtraBold',
} as const;

/** Gradiente determinístico do avatar (faixa navy/sky). Cópia de tokens.ts. */
export function gradienteAvatar(nome: string): [string, string] {
  let h = 0;
  for (let i = 0; i < nome.length; i++) h = (h * 31 + nome.charCodeAt(i)) >>> 0;
  const faixa = [cor.navy, cor.blue, cor.sky, cor.skySoft] as const;
  const a = faixa[h % faixa.length] ?? cor.navy;
  const b = faixa[(h >>> 3) % faixa.length] ?? cor.sky;
  return a === b ? [cor.navy, cor.sky] : [a, b];
}

/** Clareia (amt>0) ou escurece (amt<0) um hex. Cópia de aq-screens-4.jsx. */
export function shade(hex: string, amt: number): string {
  const h = hex.replace('#', '');
  const c = (i: number) => Math.max(0, Math.min(255, parseInt(h.substr(i, 2), 16) + Math.round(255 * amt)));
  return '#' + [c(0), c(2), c(4)].map((v) => v.toString(16).padStart(2, '0')).join('');
}

export function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/).filter(Boolean);
  const primeiro = partes[0];
  if (primeiro === undefined) return '?';
  if (partes.length === 1) return primeiro.slice(0, 2).toUpperCase();
  const ultimo = partes[partes.length - 1] ?? primeiro;
  return ((primeiro[0] ?? '') + (ultimo[0] ?? '')).toUpperCase();
}
