/**
 * Tokens de design do Aquarius.
 *
 * Fonte da verdade: o protótipo (`aq-foundation.jsx` e
 * `aq-admin-foundation.jsx`). Os valores abaixo foram transcritos dele
 * literalmente, não reinterpretados — tokens são observáveis na tela, e a
 * regra do projeto é que o protótipo manda no que é observável.
 *
 * A identidade é descrita na Concepção do Produto, seção 7: paleta clara e
 * institucional ancorada no azul-marinho e no azul-céu, "com o dourado
 * reservado a um único uso, o selo de verificação".
 */

// -----------------------------------------------------------------------------
// Marca
// -----------------------------------------------------------------------------

export const marca = {
  navy: '#0D2B5E',
  blue: '#1A4FA0',
  sky: '#2E7DD1',
  skySoft: '#5FA0E0',
  ink: '#0A1F45',
  white: '#FFFFFF',
  /**
   * Dourado. Uso único: selo de verificação.
   *
   * Não usar como acento decorativo. A Concepção do Produto reserva esta cor
   * a um só significado, e reutilizá-la em outro lugar destrói o sinal.
   */
  gold: '#C8A400',
} as const;

// -----------------------------------------------------------------------------
// Semânticas — votos, saldos, status
// -----------------------------------------------------------------------------

export const semantica = {
  /** "Sim", superávit, sucesso. */
  pos: '#1E8E5C',
  /** "Não", déficit, erro. */
  neg: '#C63A3A',
  /** Atenção, item em revisão. */
  warn: '#D97B2E',
  /** Abstenção, neutro. */
  abst: '#6B7280',
} as const;

// -----------------------------------------------------------------------------
// Tema do app (mobile e web pública)
// -----------------------------------------------------------------------------

export const temaApp = {
  ...marca,
  ...semantica,
  surface: '#F4F7FC',
  light: '#E8F1FB',
  muted: '#4A6090',
  mutedSoft: '#7B8FB5',
  border: 'rgba(13,43,94,0.12)',
  borderStrong: 'rgba(13,43,94,0.22)',
} as const;

// -----------------------------------------------------------------------------
// Temas do admin (Torre de Controle)
// -----------------------------------------------------------------------------

/**
 * O admin abre em escuro por padrão: é ferramenta operacional, usada por
 * longos períodos.
 */
export const temaAdminEscuro = {
  bg: '#0A1424',
  surface: '#101D33',
  surfaceAlt: '#0D182C',
  raised: '#152844',
  fg: '#F2F5FA',
  fgMuted: '#9AAFCC',
  fgSubtle: '#5E7AA0',
  navy: '#0D2B5E',
  blue: '#1A4FA0',
  /**
   * Note que difere do `sky` do app (#2E7DD1). O ajuste é deliberado, para
   * contraste sobre o canvas escuro. Não unificar.
   */
  sky: '#3A86C9',
  skySoft: '#5FA0E0',
  border: 'rgba(154,175,204,0.12)',
  borderStrong: 'rgba(154,175,204,0.22)',
  hover: 'rgba(154,175,204,0.06)',
  pos: '#3FBE85',
  posSoft: 'rgba(63,190,133,0.14)',
  neg: '#E0625E',
  negSoft: 'rgba(224,98,94,0.14)',
  warn: '#E89556',
  warnSoft: 'rgba(232,149,86,0.14)',
  info: '#5FA0E0',
  infoSoft: 'rgba(95,160,224,0.14)',
  /** Superfícies de IA / Prometeus. */
  accent: '#5FA0E0',
  accentSoft: 'rgba(95,160,224,0.14)',
} as const;

export const temaAdminClaro = {
  bg: '#F4F7FC',
  surface: '#FFFFFF',
  surfaceAlt: '#EEF2F8',
  raised: '#FFFFFF',
  fg: '#0A1F45',
  fgMuted: '#4A6090',
  fgSubtle: '#7B8FB5',
  navy: '#0D2B5E',
  blue: '#1A4FA0',
  sky: '#2E7DD1',
  skySoft: '#5FA0E0',
  border: 'rgba(13,43,94,0.10)',
  borderStrong: 'rgba(13,43,94,0.20)',
  hover: 'rgba(13,43,94,0.04)',
  pos: '#1E8E5C',
  posSoft: 'rgba(30,142,92,0.10)',
  neg: '#C63A3A',
  negSoft: 'rgba(198,58,58,0.10)',
  warn: '#D97B2E',
  warnSoft: 'rgba(217,123,46,0.13)',
  info: '#2E7DD1',
  infoSoft: 'rgba(46,125,209,0.10)',
  accent: '#2E7DD1',
  accentSoft: 'rgba(46,125,209,0.10)',
} as const;

// -----------------------------------------------------------------------------
// Tipografia
// -----------------------------------------------------------------------------

export const tipografia = {
  familia:
    "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif",
  /** Números e identificadores no admin. */
  familiaMono: "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace",
  pesos: { normal: 400, medio: 500, semi: 600, forte: 700, extra: 800 },
  app: {
    titulo: { min: 15, max: 22 },
    corpo: { min: 12, max: 14 },
    legenda: { min: 10.5, max: 11.5 },
  },
  admin: {
    tituloPagina: 20,
    kpi: { min: 22, max: 26, peso: 800 },
    corpo: { min: 12, max: 13 },
    micro: { min: 10, max: 11 },
  },
} as const;

// -----------------------------------------------------------------------------
// Forma e profundidade
// -----------------------------------------------------------------------------

export const raio = {
  /** Chips e pílulas. É o raio mais usado no protótipo. */
  pilula: 9999,
  card: 14,
  cardGrande: 16,
  cardPequeno: 10,
  input: 10,
} as const;

export const sombra = {
  /** Cards normais: borda mais leve elevação. */
  card: '0 1px 2px rgba(13,43,94,0.06)',
  /** Destaque forte, usado em mockups e modais. */
  destaque: '0 24px 50px rgba(13,43,94,0.20)',
} as const;

// -----------------------------------------------------------------------------
// Avatar
// -----------------------------------------------------------------------------

/**
 * Gradiente determinístico para avatar, restrito à faixa navy/sky.
 *
 * É placeholder da foto oficial, e a restrição de faixa é o que mantém a
 * coerência visual: cor derivada do nome, nunca aleatória, nunca fora da
 * paleta institucional.
 */
export function gradienteAvatar(nome: string): [string, string] {
  let h = 0;
  for (let i = 0; i < nome.length; i++) {
    h = (h * 31 + nome.charCodeAt(i)) >>> 0;
  }
  const faixa = [marca.navy, marca.blue, marca.sky, marca.skySoft] as const;
  const a = faixa[h % faixa.length] ?? marca.navy;
  const b = faixa[(h >>> 3) % faixa.length] ?? marca.sky;
  return a === b ? [marca.navy, marca.sky] : [a, b];
}

export function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/).filter(Boolean);
  const primeiro = partes[0];
  if (primeiro === undefined) return '?';
  if (partes.length === 1) return primeiro.slice(0, 2).toUpperCase();
  const ultimo = partes[partes.length - 1] ?? primeiro;
  return ((primeiro[0] ?? '') + (ultimo[0] ?? '')).toUpperCase();
}

export type TemaApp = typeof temaApp;
export type TemaAdmin = typeof temaAdminEscuro;
