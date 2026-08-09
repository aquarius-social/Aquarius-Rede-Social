'use client';
import type { ReactNode } from 'react';
import { useAdmTheme } from '../lib/theme';
import { Card, SectionLabel } from './ui';
import { Icon, type IconName } from './Icon';

const MONO = 'var(--font-mono), ui-monospace, monospace';

export function admFmtK(n: number): string {
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1).replace('.', ',') + 'M';
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(1).replace('.', ',') + 'K';
  return String(n);
}

/* Sparkline — porte de AdmSparkline */
export function Sparkline({ data, w = 80, h = 24, accent, fill = true }: { data: number[]; w?: number; h?: number; accent?: string; fill?: boolean }) {
  const { theme } = useAdmTheme();
  const c = accent || theme.sky;
  if (!data.length) return <svg width={w} height={h} />;
  const min = Math.min(...data), max = Math.max(...data);
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1 || 1)) * (w - 2) + 1;
    const y = 1 + (1 - (v - min) / (max - min || 1)) * (h - 2);
    return [x, y] as const;
  });
  const d = pts.map((p, i) => (i === 0 ? 'M' : 'L') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
  const dArea = d + ` L${w - 1},${h - 1} L1,${h - 1} Z`;
  return (
    <svg width={w} height={h} style={{ display: 'block' }}>
      {fill && <path d={dArea} fill={c} opacity="0.16" />}
      <path d={d} fill="none" stroke={c} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

/* Área — porte de AdmAreaChart */
export function AreaChart({ data, labels, w = 600, h = 180, accent }: { data: number[]; labels?: string[]; w?: number; h?: number; accent?: string }) {
  const { theme } = useAdmTheme();
  const c = accent || theme.sky;
  if (data.length < 2) return <svg width={w} height={h} />;
  const min = Math.min(...data), max = Math.max(...data);
  const pad = { l: 36, r: 8, t: 8, b: 22 };
  const iw = w - pad.l - pad.r, ih = h - pad.t - pad.b;
  const base = min * 0.92;
  const pts = data.map((v, i) => {
    const x = pad.l + (i / (data.length - 1)) * iw;
    const y = pad.t + (1 - (v - base) / ((max - base) || 1)) * ih;
    return [x, y] as const;
  });
  const d = pts.map((p, i) => (i === 0 ? 'M' : 'L') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
  const dArea = d + ` L${pad.l + iw},${pad.t + ih} L${pad.l},${pad.t + ih} Z`;
  const gid = 'ag' + c.replace(/[^a-z0-9]/gi, '');
  return (
    <svg width={w} height={h} style={{ display: 'block', maxWidth: '100%' }}>
      <defs>
        <linearGradient id={gid} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={c} stopOpacity="0.22" />
          <stop offset="100%" stopColor={c} stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0, 0.25, 0.5, 0.75, 1].map((g, i) => (
        <g key={i}>
          <line x1={pad.l} x2={w - pad.r} y1={pad.t + ih * g} y2={pad.t + ih * g} stroke={theme.border} strokeDasharray={g === 1 ? '' : '2 4'} />
          <text x={pad.l - 7} y={pad.t + ih * g + 3} textAnchor="end" fontFamily={MONO} fontSize="9.5" fill={theme.fgSubtle}>
            {admFmtK(Math.round(base + (max - base) * (1 - g)))}
          </text>
        </g>
      ))}
      <path d={dArea} fill={`url(#${gid})`} />
      <path d={d} fill="none" stroke={c} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
      {pts.map((p, i) => (i % Math.ceil(pts.length / 8) === 0 ? <circle key={i} cx={p[0]} cy={p[1]} r="2.5" fill={c} /> : null))}
      {labels?.map((l, i) => {
        const N = Math.ceil(labels.length / 8);
        if (i % N !== 0 && i !== labels.length - 1) return null;
        const x = pad.l + (i / (labels.length - 1)) * iw;
        return <text key={i} x={x} y={h - 6} textAnchor="middle" fontFamily={MONO} fontSize="9.5" fill={theme.fgSubtle}>{l}</text>;
      })}
    </svg>
  );
}

/* Donut — porte de AdmDonut */
export function Donut({ data, w = 140 }: { data: { value: number; color: string }[]; w?: number }) {
  const { theme } = useAdmTheme();
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const r = w / 2 - 12, cx = w / 2, cy = w / 2, sw = 16;
  let acc = 0;
  return (
    <svg width={w} height={w}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={theme.hover} strokeWidth={sw} />
      {data.map((d, i) => {
        const C = 2 * Math.PI * r;
        const dash = (d.value / total) * C;
        const off = (-acc / total) * C;
        acc += d.value;
        return <circle key={i} cx={cx} cy={cy} r={r} fill="none" stroke={d.color} strokeWidth={sw}
          strokeDasharray={`${dash} ${C - dash}`} strokeDashoffset={off} transform={`rotate(-90 ${cx} ${cy})`} />;
      })}
    </svg>
  );
}

/* KPI card — porte de AdmKpiCard (ícone + delta + sparkline) */
export function KpiCard({ label, value, sub, delta, trend, accent, icon }: {
  label: string; value: string; sub?: string; delta?: number; trend?: number[]; accent?: string; icon?: IconName;
}) {
  const { theme } = useAdmTheme();
  const c = accent || theme.sky;
  const pos = typeof delta === 'number' ? delta >= 0 : true;
  return (
    <Card padding={14}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div style={{ width: 28, height: 28, borderRadius: 7, background: `${c}22`, color: c, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          {icon ? <Icon name={icon} size={15} color={c} /> : null}
        </div>
        {delta != null ? (
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 3, padding: '2px 7px', borderRadius: 5, background: pos ? theme.posSoft : theme.negSoft, color: pos ? theme.pos : theme.neg, fontFamily: MONO, fontSize: 10, fontWeight: 700 }}>
            <span>{pos ? '▲' : '▼'}</span>{Math.abs(delta).toFixed(1)}%
          </div>
        ) : null}
      </div>
      <div style={{ marginTop: 14, fontWeight: 800, fontSize: 24, color: theme.fg, letterSpacing: '-0.02em', lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>{value}</div>
      <div style={{ marginTop: 6, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <SectionLabel>{label}</SectionLabel>
          {sub ? <div style={{ marginTop: 3, fontSize: 11, color: theme.fgMuted, fontWeight: 500 }}>{sub}</div> : null}
        </div>
        {trend ? <Sparkline data={trend} w={70} h={22} accent={c} /> : null}
      </div>
    </Card>
  );
}

const STATUS: Record<string, 'pos' | 'warn' | 'neg'> = { ok: 'pos', parcial: 'warn', fora: 'neg' };
export function StatusDot({ status }: { status: 'ok' | 'parcial' | 'fora' }) {
  const { theme } = useAdmTheme();
  const cor = { pos: theme.pos, warn: theme.warn, neg: theme.neg }[STATUS[status]];
  return <span style={{ width: 9, height: 9, borderRadius: 9999, background: cor, boxShadow: `0 0 0 3px ${cor}22`, flexShrink: 0 }} />;
}

export function Button({ children, variant = 'secondary', icon, onClick }: { children: ReactNode; variant?: 'primary' | 'secondary' | 'ghost'; icon?: IconName; onClick?: () => void }) {
  const { theme } = useAdmTheme();
  const styles = {
    primary: { bg: theme.sky, fg: '#fff', bd: theme.sky },
    secondary: { bg: 'transparent', fg: theme.fg, bd: theme.borderStrong },
    ghost: { bg: 'transparent', fg: theme.fgMuted, bd: 'transparent' },
  }[variant];
  return (
    <button onClick={onClick} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 12px', borderRadius: 8, border: `1px solid ${styles.bd}`, background: styles.bg, color: styles.fg, cursor: 'pointer', fontSize: 12.5, fontWeight: 600 }}>
      {icon ? <Icon name={icon} size={14} color={styles.fg} /> : null}
      {children}
    </button>
  );
}
