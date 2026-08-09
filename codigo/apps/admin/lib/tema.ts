/** Tokens do admin — cópia literal de aq-admin-foundation.jsx (dark default). */
export interface Tema {
  bg: string; surface: string; surfaceAlt: string; raised: string;
  fg: string; fgMuted: string; fgSubtle: string;
  navy: string; blue: string; sky: string; skySoft: string;
  border: string; borderStrong: string; hover: string;
  pos: string; posSoft: string; neg: string; negSoft: string;
  warn: string; warnSoft: string; info: string; infoSoft: string;
  accent: string; accentSoft: string;
}

export const ADM_LIGHT: Tema = {
  bg: '#F4F7FC', surface: '#FFFFFF', surfaceAlt: '#EEF2F8', raised: '#FFFFFF',
  fg: '#0A1F45', fgMuted: '#4A6090', fgSubtle: '#7B8FB5',
  navy: '#0D2B5E', blue: '#1A4FA0', sky: '#2E7DD1', skySoft: '#5FA0E0',
  border: 'rgba(13,43,94,0.10)', borderStrong: 'rgba(13,43,94,0.20)', hover: 'rgba(13,43,94,0.04)',
  pos: '#1E8E5C', posSoft: 'rgba(30,142,92,0.10)', neg: '#C63A3A', negSoft: 'rgba(198,58,58,0.10)',
  warn: '#D97B2E', warnSoft: 'rgba(217,123,46,0.13)', info: '#2E7DD1', infoSoft: 'rgba(46,125,209,0.10)',
  accent: '#2E7DD1', accentSoft: 'rgba(46,125,209,0.10)',
};

export const ADM_DARK: Tema = {
  bg: '#0A1424', surface: '#101D33', surfaceAlt: '#0D182C', raised: '#152844',
  fg: '#F2F5FA', fgMuted: '#9AAFCC', fgSubtle: '#5E7AA0',
  navy: '#0D2B5E', blue: '#1A4FA0', sky: '#3A86C9', skySoft: '#5FA0E0',
  border: 'rgba(154,175,204,0.12)', borderStrong: 'rgba(154,175,204,0.22)', hover: 'rgba(154,175,204,0.06)',
  pos: '#3FBE85', posSoft: 'rgba(63,190,133,0.14)', neg: '#E0625E', negSoft: 'rgba(224,98,94,0.14)',
  warn: '#E89556', warnSoft: 'rgba(232,149,86,0.14)', info: '#5FA0E0', infoSoft: 'rgba(95,160,224,0.14)',
  accent: '#5FA0E0', accentSoft: 'rgba(95,160,224,0.14)',
};

export const raio = { card: 14, pill: 9999, sm: 8 };
