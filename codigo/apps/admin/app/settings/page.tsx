'use client';
import { useAdmTheme } from '../../lib/theme';
import { Card, PageHeader, SectionLabel, Badge } from '../../components/ui';
import { Icon } from '../../components/Icon';

const TIME = [
  { av: 'MS', nome: 'Mariana Souza', email: 'mariana@base.aq', papel: 'Superadmin', tone: 'accent' as const },
  { av: 'PH', nome: 'Pedro Henrique', email: 'pedro@base.aq', papel: 'Operador', tone: 'muted' as const },
  { av: 'RV', nome: 'Rodrigo Vieira', email: 'rodrigo@base.aq', papel: 'Operador', tone: 'muted' as const },
  { av: 'CM', nome: 'Carla Mendes', email: 'carla@base.aq', papel: 'Auditor', tone: 'warn' as const },
];

// Ordem/nomes do protótipo; STATUS honesto: conectado = de fato em uso; planejado = ainda não integrado.
const INTEGRACOES: { nome: string; status: 'conectado' | 'planejado' }[] = [
  { nome: 'API Câmara dos Deputados', status: 'conectado' },
  { nome: 'API Senado Federal', status: 'conectado' },
  { nome: 'Siga Brasil', status: 'conectado' },
  { nome: 'WhatsApp Business · Meta', status: 'planejado' },
  { nome: 'OpenAI · Tentáculo B/C', status: 'planejado' },
  { nome: 'Anthropic · Tentáculo A', status: 'planejado' },
  { nome: 'Stripe · Pagamentos', status: 'planejado' },
  { nome: 'Supabase · Backend', status: 'conectado' },
];

export default function Settings() {
  const { theme } = useAdmTheme();

  return (
    <>
      <PageHeader title="Configurações" subtitle="Time, integrações, ambiente" />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, alignItems: 'start' }}>
        {/* Time */}
        <Card padding={0}>
          <div style={{ padding: '14px 18px', borderBottom: `1px solid ${theme.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <SectionLabel>Time · Base Aquarius</SectionLabel>
            <Badge tone="muted">ilustrativo</Badge>
          </div>
          {TIME.map((m, i) => (
            <div key={m.email} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 18px', borderBottom: i < TIME.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
              <span style={{ width: 36, height: 36, borderRadius: 9999, background: 'linear-gradient(135deg,#0D2B5E,#2E7DD1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 11, fontWeight: 800, flexShrink: 0 }}>{m.av}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: theme.fg }}>{m.nome}</div>
                <div style={{ marginTop: 2, fontFamily: 'var(--font-mono), monospace', fontSize: 11.5, color: theme.fgSubtle }}>{m.email}</div>
              </div>
              <Badge tone={m.tone}>{m.papel}</Badge>
            </div>
          ))}
          <div style={{ padding: '12px 18px', fontSize: 11.5, color: theme.fgSubtle, lineHeight: 1.5 }}>
            O time real depende da auth/role de admin (backlog). Ver também “Equipe & Permissões”.
          </div>
        </Card>

        {/* Integrações */}
        <Card padding={0}>
          <div style={{ padding: '14px 18px', borderBottom: `1px solid ${theme.border}` }}><SectionLabel>Integrações ativas</SectionLabel></div>
          {INTEGRACOES.map((it, i) => {
            const on = it.status === 'conectado';
            return (
              <div key={it.nome} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '13px 18px', borderBottom: i < INTEGRACOES.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
                <span style={{ width: 8, height: 8, borderRadius: 9999, background: on ? theme.pos : theme.fgSubtle, flexShrink: 0 }} />
                <span style={{ flex: 1, fontSize: 13.5, color: theme.fg }}>{it.nome}</span>
                <span style={{ fontSize: 11.5, fontWeight: 600, color: on ? theme.pos : theme.fgMuted }}>{it.status}</span>
              </div>
            );
          })}
          <div style={{ padding: '12px 18px', fontSize: 11.5, color: theme.fgSubtle, lineHeight: 1.5 }}>
            <Icon name="check" size={12} color={theme.pos} /> “conectado” = de fato em uso · <b>planejado</b> = ainda não integrado.
          </div>
        </Card>
      </div>
    </>
  );
}
