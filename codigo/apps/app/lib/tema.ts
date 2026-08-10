/**
 * Tema do app — ESPELHO de `packages/ui/src/tokens.ts` (a fonte da verdade),
 * agora com dois modos (claro/escuro) e um provider React.
 *
 * Duplicado aqui só para o primeiro vertical rodar sem configurar resolução de
 * monorepo no Metro. TODO: trocar por `import { temaApp } from '@aquarius/ui'`
 * quando o workspace estiver ligado. Os valores são cópia literal — não
 * reinterpretar (o protótipo manda no observável).
 *
 * ── Dark mode ──────────────────────────────────────────────────────────────
 * Componentes leem a paleta ativa via `useTema()` (nunca importam `cor` direto).
 * Dois tokens semânticos evitam a sobrecarga de `navy`/`white`:
 *   • `texto`  — cor de TEXTO/ícone-sobre-fundo-claro (era `cor.navy` como cor).
 *   • `cartao` — cor de FUNDO de card/input/chip (era `cor.white` como bg).
 * `white` continua branco (texto/ícone SOBRE preenchimento colorido) e `navy`
 * continua sendo o preenchimento de botões/realces. Assim a migração por tela é
 * mecânica: `color: cor.navy → cor.texto` e `backgroundColor: cor.white → cor.cartao`.
 */

/** Forma da paleta — as duas versões (clara/escura) implementam este contrato. */
export interface Tema {
  navy: string; blue: string; sky: string; skySoft: string; ink: string;
  white: string; gold: string; pos: string; neg: string; warn: string; abst: string;
  surface: string; light: string; muted: string; mutedSoft: string;
  border: string; borderStrong: string;
  /** Texto/ícone primário sobre fundo claro (claro=navy, escuro=quase-branco). */
  texto: string;
  /** Fundo de card/input/chip (claro=branco, escuro=navy elevado). */
  cartao: string;
}

export const TEMA_CLARO: Tema = {
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
  texto: '#0D2B5E',
  cartao: '#FFFFFF',
};

/**
 * Paleta escura — derivada dos PNGs de referência (telas-aquarius/app-dark).
 * Fundo navy profundo, cards navy elevados, texto quase-branco, acentos um
 * pouco mais claros para manter contraste (verde/vermelho/azul).
 */
export const TEMA_ESCURO: Tema = {
  navy: '#16386F',        // preenchimento de botões/realces (elevado p/ contraste no fundo escuro)
  blue: '#2E63B5',
  sky: '#3B86DB',
  skySoft: '#5FA0E0',
  ink: '#DDE8F7',         // texto de corpo
  white: '#FFFFFF',       // texto/ícone SOBRE preenchimento colorido — inalterado
  gold: '#E0B93A',
  pos: '#35C088',
  neg: '#E26158',
  warn: '#E8964A',
  abst: '#8494AE',
  surface: '#0A1A38',     // fundo da página
  light: '#18294A',       // tile suave / trilho de progresso
  muted: '#93A6C8',
  mutedSoft: '#6E83A8',
  border: 'rgba(255,255,255,0.10)',
  borderStrong: 'rgba(255,255,255,0.20)',
  texto: '#EAF1FB',       // texto/ícone primário
  cartao: '#122340',      // fundo de card/input/chip
};

/**
 * Export legado estático (= tema claro). Usado apenas por módulos que NÃO são
 * componentes React (ex.: `mock.ts` — cores de acento de gráfico, independem de
 * modo) e por telas sempre-navy fixas (`splash.tsx`, gradientes decorativos).
 * Componentes de UI NÃO devem importar isto — usar `useTema()`.
 */
export const cor = TEMA_CLARO;

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
