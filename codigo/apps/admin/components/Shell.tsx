'use client';
import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAdmTheme } from '../lib/theme';
import { Icon, type IconName } from './Icon';

type NavItem =
  | { kind: 'section'; label: string }
  | { kind: 'item'; id: string; href: string; icon: IconName; label: string; badge?: { tone: 'warn' | 'neg' | 'accent'; text: string } };

const NAV: NavItem[] = [
  { kind: 'section', label: 'Painel' },
  { kind: 'item', id: 'overview', href: '/', icon: 'grid', label: 'Visão geral' },
  { kind: 'item', id: 'pipelines', href: '/pipelines', icon: 'pipe', label: 'Pipelines', badge: { tone: 'warn', text: '2' } },
  { kind: 'section', label: 'Conteúdo' },
  { kind: 'item', id: 'feed', href: '/feed', icon: 'list', label: 'Feed & Posts', badge: { tone: 'warn', text: '11' } },
  { kind: 'item', id: 'stories', href: '/stories', icon: 'star', label: 'Stories da IA' },
  { kind: 'item', id: 'revisao', href: '/revisao', icon: 'eye', label: 'Revisão editorial', badge: { tone: 'warn', text: '11' } },
  { kind: 'item', id: 'moderacao', href: '/moderacao', icon: 'shield', label: 'Moderação', badge: { tone: 'neg', text: '9' } },
  { kind: 'section', label: 'Inteligência' },
  { kind: 'item', id: 'prometeus', href: '/prometeus', icon: 'spark', label: 'Prometeus IA', badge: { tone: 'accent', text: '7' } },
  { kind: 'section', label: 'Comunidade' },
  { kind: 'item', id: 'usuarios', href: '/usuarios', icon: 'users', label: 'Usuários' },
  { kind: 'item', id: 'engajamento', href: '/engajamento', icon: 'trend', label: 'Engajamento' },
  { kind: 'item', id: 'audiencias', href: '/audiencias', icon: 'globe', label: 'Audiências', badge: { tone: 'accent', text: 'DaaS' } },
  { kind: 'section', label: 'Sistema' },
  { kind: 'item', id: 'flags', href: '/flags', icon: 'flag', label: 'Feature flags' },
  { kind: 'item', id: 'auditoria', href: '/auditoria', icon: 'lock', label: 'Auditoria LGPD' },
  { kind: 'item', id: 'equipe', href: '/equipe', icon: 'users', label: 'Equipe & Permissões' },
  { kind: 'item', id: 'settings', href: '/settings', icon: 'gear', label: 'Configurações' },
];

const LABELS: Record<string, string> = Object.fromEntries(
  NAV.filter((n): n is Extract<NavItem, { kind: 'item' }> => n.kind === 'item').map((n) => [n.href, n.label]),
);

function AdmMark() {
  return (
    <svg width={30} height={30} viewBox="0 0 32 32" fill="none">
      <rect width="32" height="32" rx="9" fill="url(#am)" />
      <path d="M6 20 Q11 15 16 20 T26 20" stroke="#fff" strokeWidth="2" fill="none" strokeLinecap="round" />
      <path d="M6 15 Q11 10 16 15 T26 15" stroke="#5FA0E0" strokeWidth="2" fill="none" strokeLinecap="round" opacity="0.9" />
      <defs>
        <linearGradient id="am" x1="0" y1="0" x2="1" y2="1">
          <stop stopColor="#0D2B5E" /><stop offset="1" stopColor="#2E7DD1" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  const { theme, mode, toggle } = useAdmTheme();
  const path = usePathname();
  const [colapsado, setColapsado] = useState(false);
  const w = colapsado ? 68 : 236;
  const pagina = LABELS[path] ?? 'Visão geral';

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: theme.bg, color: theme.fg }}>
      {/* Sidebar */}
      <aside style={{ width: w, flexShrink: 0, borderRight: `1px solid ${theme.border}`, background: theme.surfaceAlt, position: 'sticky', top: 0, height: '100vh', display: 'flex', flexDirection: 'column', transition: 'width .18s ease' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '18px 16px 14px' }}>
          <AdmMark />
          {!colapsado ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontWeight: 800, fontSize: 17, letterSpacing: '0.02em' }}>AQUARIUS</span>
              <span style={{ fontSize: 10, fontWeight: 700, color: theme.fgMuted, padding: '2px 6px', borderRadius: 6, background: theme.hover }}>Admin</span>
            </div>
          ) : null}
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '0 12px' }}>
          {NAV.map((n, i) =>
            n.kind === 'section' ? (
              colapsado ? <div key={'s' + i} style={{ height: 14 }} /> :
                <div key={'s' + i} style={{ padding: '14px 8px 6px', fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: theme.fgSubtle }}>{n.label}</div>
            ) : (
              <Link key={n.id} href={n.href} title={n.label} style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '9px 10px', borderRadius: 9, fontSize: 13, fontWeight: path === n.href ? 700 : 500, color: path === n.href ? theme.fg : theme.fgMuted, background: path === n.href ? theme.hover : 'transparent', marginBottom: 1, justifyContent: colapsado ? 'center' : 'flex-start' }}>
                <Icon name={n.icon} size={17} color={path === n.href ? theme.sky : theme.fgMuted} />
                {!colapsado ? <span style={{ flex: 1 }}>{n.label}</span> : null}
                {!colapsado && n.badge ? <Badge tone={n.badge.tone} text={n.badge.text} /> : null}
              </Link>
            ),
          )}
        </div>

        <button onClick={() => setColapsado((v) => !v)} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 18px', borderTop: `1px solid ${theme.border}`, background: 'transparent', color: theme.fgMuted, cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
          <Icon name="chevR" size={15} color={theme.fgMuted} style={{ transform: colapsado ? 'none' : 'rotate(180deg)' }} />
          {!colapsado ? 'Recolher' : null}
        </button>
      </aside>

      {/* Main */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        <header style={{ height: 60, flexShrink: 0, borderBottom: `1px solid ${theme.border}`, background: theme.surface, display: 'flex', alignItems: 'center', gap: 14, padding: '0 20px', position: 'sticky', top: 0, zIndex: 10 }}>
          {/* Breadcrumb */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, flexShrink: 0 }}>
            <span style={{ color: theme.fgMuted }}>Aquarius</span>
            <Icon name="chevR" size={13} color={theme.fgSubtle} />
            <span style={{ fontWeight: 700, color: theme.fg }}>{pagina}</span>
          </div>
          {/* Busca central */}
          <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
            <div style={{ width: '100%', maxWidth: 460, display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', borderRadius: 10, border: `1px solid ${theme.border}`, background: theme.bg, color: theme.fgMuted, fontSize: 12.5 }}>
              <Icon name="search" size={15} color={theme.fgSubtle} />
              <span style={{ flex: 1 }}>Buscar ou perguntar ao Prometeus…</span>
              <span style={{ padding: '1px 6px', borderRadius: 5, border: `1px solid ${theme.borderStrong}`, fontSize: 10.5, fontFamily: 'var(--font-mono), monospace' }}>⌘K</span>
            </div>
          </div>
          {/* Direita */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 10px', borderRadius: 9999, border: `1px solid ${theme.borderStrong}`, fontSize: 11, fontWeight: 700, letterSpacing: '0.04em' }}>
              <span style={{ width: 6, height: 6, borderRadius: 9999, background: theme.warn }} />DEV
            </span>
            <button onClick={toggle} aria-label="Alternar tema" style={{ width: 34, height: 34, borderRadius: 9999, border: `1px solid ${theme.borderStrong}`, background: 'transparent', color: theme.fg, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Icon name={mode === 'dark' ? 'sun' : 'moon'} size={16} color={theme.fg} />
            </button>
            <button aria-label="Notificações" style={{ position: 'relative', width: 34, height: 34, borderRadius: 9999, border: `1px solid ${theme.borderStrong}`, background: 'transparent', color: theme.fg, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Icon name="bell" size={16} color={theme.fg} />
              <span style={{ position: 'absolute', top: 7, right: 8, width: 7, height: 7, borderRadius: 9999, background: theme.neg, border: `1.5px solid ${theme.surface}` }} />
            </button>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 10px 4px 4px', borderRadius: 9999, border: `1px solid ${theme.border}` }}>
              <span style={{ width: 26, height: 26, borderRadius: 9999, background: 'linear-gradient(135deg,#0D2B5E,#2E7DD1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 10, fontWeight: 800 }}>AQ</span>
              <span style={{ fontSize: 12.5, fontWeight: 600 }}>Admin</span>
              <Icon name="chevR" size={13} color={theme.fgMuted} style={{ transform: 'rotate(90deg)' }} />
            </div>
          </div>
        </header>
        <main style={{ flex: 1, padding: 20 }}>{children}</main>
      </div>
    </div>
  );
}

function Badge({ tone, text }: { tone: 'warn' | 'neg' | 'accent'; text: string }) {
  const { theme } = useAdmTheme();
  const map = { warn: [theme.warnSoft, theme.warn], neg: [theme.negSoft, theme.neg], accent: [theme.accentSoft, theme.accent] } as const;
  const [bg, fg] = map[tone];
  return <span style={{ padding: '1px 7px', borderRadius: 9999, background: bg, color: fg, fontSize: 10, fontWeight: 700 }}>{text}</span>;
}
