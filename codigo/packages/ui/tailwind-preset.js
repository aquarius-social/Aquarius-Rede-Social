/**
 * Preset de Tailwind do Aquarius.
 *
 * Compartilhado por apps/web (Next.js) e apps/mobile (NativeWind).
 * Os valores vêm de src/tokens.ts, que por sua vez transcreve o protótipo.
 *
 * Uso:
 *   // tailwind.config.js
 *   module.exports = { presets: [require('@aquarius/ui/tailwind-preset')] }
 */

const marca = {
  navy: '#0D2B5E',
  blue: '#1A4FA0',
  sky: '#2E7DD1',
  skySoft: '#5FA0E0',
  ink: '#0A1F45',
  gold: '#C8A400',
};

const semantica = {
  pos: '#1E8E5C',
  neg: '#C63A3A',
  warn: '#D97B2E',
  abst: '#6B7280',
};

module.exports = {
  theme: {
    extend: {
      colors: {
        aquarius: {
          ...marca,
          ...semantica,
          surface: '#F4F7FC',
          light: '#E8F1FB',
          muted: '#4A6090',
          mutedSoft: '#7B8FB5',
        },
        // Torre de Controle. Escuro é o padrão.
        adm: {
          bg: '#0A1424',
          surface: '#101D33',
          surfaceAlt: '#0D182C',
          raised: '#152844',
          fg: '#F2F5FA',
          fgMuted: '#9AAFCC',
          fgSubtle: '#5E7AA0',
          // Difere do sky do app por contraste sobre canvas escuro.
          sky: '#3A86C9',
          accent: '#5FA0E0',
          pos: '#3FBE85',
          neg: '#E0625E',
          warn: '#E89556',
          info: '#5FA0E0',
        },
      },
      borderColor: {
        aquarius: 'rgba(13,43,94,0.12)',
        'aquarius-strong': 'rgba(13,43,94,0.22)',
        adm: 'rgba(154,175,204,0.12)',
        'adm-strong': 'rgba(154,175,204,0.22)',
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'system-ui',
          'sans-serif',
        ],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      borderRadius: {
        card: '14px',
        'card-lg': '16px',
        'card-sm': '10px',
        input: '10px',
      },
      boxShadow: {
        card: '0 1px 2px rgba(13,43,94,0.06)',
        destaque: '0 24px 50px rgba(13,43,94,0.20)',
      },
    },
  },
};
