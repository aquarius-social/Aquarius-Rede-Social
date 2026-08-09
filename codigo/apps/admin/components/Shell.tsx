'use client';
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
  { kind: 'item', id: 'pipelines', href: '/pipelines', icon: 'pipe', label: 'Pipelines' },
  { kind: 'section', label: 'Conteúdo' },
  { kind: 'item', id: 'feed', href: '/feed', icon: 'list', label: 'Feed & Posts' },
  { kind: 'item', id: 'stories', href: '/stories', icon: 'star', label: 'Stories da IA' },
  { kind: 'item', id: 'revisao', href: '/revisao', icon: 'eye', label: 'Revisão editorial' },
  { kind: 'item', id: 'moderacao', href: '/moderacao', icon: 'shield', label: 'Moderação' },
  { kind: 'section', label: 'Inteligência' },
  { kind: 'item', id: 'prometeus', href: '/prometeus', icon: 'spark', label: 'Prometeus IA' },
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

export function Shell({ children }: { children: React.ReactNode }) {
  const { theme, mode, toggle } = useAdmTheme();
  const path = usePathname();

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: theme.bg, color: theme.fg }}>
      {/* Sidebar */}
      <aside style={{ width: 236, flexShrink: 0, borderRight: `1px solid ${theme.border}`, background: theme.surfaceAlt, position: 'sticky', top: 0, height: '100vh', overflowY: 'auto', padding: '16px 12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 8px 16px' }}>
          <div style={{ width: 32, height: 32, borderRadius: 9, background: 'linear-gradient(135deg,#0D2B5E,#2E7DD1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, fontSize: 16 }}>A</div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 14, letterSpacing: '-0.01em' }}>Aquarius</div>
            <div style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: theme.fgSubtle }}>Admin</div>
          </div>
        </div>

        {NAV.map((n, i) =>
          n.kind === 'section' ? (
            <div key={'s' + i} style={{ padding: '14px 8px 6px', fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: theme.fgSubtle }}>{n.label}</div>
          ) : (
            <Link key={n.id} href={n.href} style={navItemStyle(path === n.href, theme)}>
              <Icon name={n.icon} size={17} color={path === n.href ? theme.fg : theme.fgMuted} />
              <span style={{ flex: 1 }}>{n.label}</span>
              {n.badge ? <Badge tone={n.badge.tone} text={n.badge.text} /> : null}
            </Link>
          ),
        )}
      </aside>

      {/* Main */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        <header style={{ height: 56, flexShrink: 0, borderBottom: `1px solid ${theme.border}`, background: theme.surface, display: 'flex', alignItems: 'center', gap: 12, padding: '0 20px', position: 'sticky', top: 0, zIndex: 10 }}>
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 8, color: theme.fgMuted, fontSize: 12.5 }}>
            <Icon name="search" size={15} color={theme.fgSubtle} />
            <span>Buscar (⌘K) — em breve</span>
          </div>
          <button onClick={toggle} aria-label="Alternar tema" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 11px', borderRadius: 9999, border: `1px solid ${theme.borderStrong}`, background: 'transparent', color: theme.fg, cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
            <Icon name={mode === 'dark' ? 'sun' : 'moon'} size={15} color={theme.fg} />
            {mode === 'dark' ? 'Claro' : 'Escuro'}
          </button>
        </header>
        <main style={{ flex: 1, padding: 20 }}>{children}</main>
      </div>
    </div>
  );
}

function navItemStyle(active: boolean, theme: ReturnType<typeof useAdmTheme>['theme']): React.CSSProperties {
  return {
    display: 'flex', alignItems: 'center', gap: 10, padding: '9px 10px', borderRadius: 9,
    fontSize: 13, fontWeight: active ? 700 : 500,
    color: active ? theme.fg : theme.fgMuted,
    background: active ? theme.hover : 'transparent',
    marginBottom: 1,
  };
}

function Badge({ tone, text }: { tone: 'warn' | 'neg' | 'accent'; text: string }) {
  const { theme } = useAdmTheme();
  const map = { warn: [theme.warnSoft, theme.warn], neg: [theme.negSoft, theme.neg], accent: [theme.accentSoft, theme.accent] } as const;
  const [bg, fg] = map[tone];
  return <span style={{ padding: '1px 7px', borderRadius: 9999, background: bg, color: fg, fontSize: 10, fontWeight: 700 }}>{text}</span>;
}
