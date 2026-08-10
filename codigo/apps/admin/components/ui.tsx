'use client';
import type { CSSProperties, ReactNode } from 'react';
import { useAdmTheme } from '../lib/theme';

export function Card({ children, padding = 16, style }: { children: ReactNode; padding?: number; style?: CSSProperties }) {
  const { theme } = useAdmTheme();
  return (
    <div style={{ background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: 14, padding, ...style }}>
      {children}
    </div>
  );
}

export function SectionLabel({ children }: { children: ReactNode }) {
  const { theme } = useAdmTheme();
  return <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: theme.fgMuted }}>{children}</div>;
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  const { theme } = useAdmTheme();
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 16, marginBottom: 18 }}>
      <div>
        <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800, letterSpacing: '-0.02em', color: theme.fg }}>{title}</h1>
        {subtitle ? <div style={{ marginTop: 4, fontSize: 12.5, color: theme.fgMuted }}>{subtitle}</div> : null}
      </div>
      {actions ? <div style={{ display: 'flex', gap: 8 }}>{actions}</div> : null}
    </div>
  );
}

export function KpiCard({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: string }) {
  const { theme } = useAdmTheme();
  return (
    <Card>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ width: 8, height: 8, borderRadius: 9999, background: accent ?? theme.sky }} />
        <SectionLabel>{label}</SectionLabel>
      </div>
      <div style={{ marginTop: 10, fontSize: 28, fontWeight: 800, letterSpacing: '-0.02em', color: theme.fg, fontVariantNumeric: 'tabular-nums' }}>{value}</div>
      {sub ? <div style={{ marginTop: 4, fontSize: 11.5, color: theme.fgMuted }}>{sub}</div> : null}
    </Card>
  );
}

/** Selo sutil de proveniência do dado: `real` (do banco) ou `amostra` (placeholder). */
export function Selo({ tipo }: { tipo: 'amostra' | 'real' }) {
  const { theme } = useAdmTheme();
  const cor = tipo === 'real' ? theme.pos : theme.fgSubtle;
  return (
    <span title={tipo === 'real' ? 'Dado real do banco' : 'Placeholder — entra dado real quando a fonte existir'}
      style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 9, fontWeight: 700, letterSpacing: '0.06em', color: cor, textTransform: 'uppercase' }}>
      <span style={{ width: 5, height: 5, borderRadius: 9999, background: cor }} />{tipo}
    </span>
  );
}

export function Badge({ tone = 'muted', children }: { tone?: 'muted' | 'pos' | 'warn' | 'neg' | 'accent'; children: ReactNode }) {
  const { theme } = useAdmTheme();
  const map = {
    muted: [theme.hover, theme.fgMuted], pos: [theme.posSoft, theme.pos], warn: [theme.warnSoft, theme.warn],
    neg: [theme.negSoft, theme.neg], accent: [theme.accentSoft, theme.accent],
  } as const;
  const [bg, fg] = map[tone];
  return <span style={{ padding: '2px 9px', borderRadius: 9999, background: bg, color: fg, fontSize: 10.5, fontWeight: 700, letterSpacing: '0.02em' }}>{children}</span>;
}
