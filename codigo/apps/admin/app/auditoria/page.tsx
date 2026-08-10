'use client';
import { useState } from 'react';
import { useAdmTheme } from '../../lib/theme';
import { Card, PageHeader } from '../../components/ui';
import { Button } from '../../components/charts';
import { Icon } from '../../components/Icon';
import { EVENTOS } from '../../lib/demo/auditoria';

const TABS = [['todos', 'Todos'], ['seguranca', 'Segurança'], ['dados', 'Dados'], ['sistema', 'Sistema']] as const;

export default function Auditoria() {
  const { theme } = useAdmTheme();
  const [tab, setTab] = useState<string>('todos');
  const [busca, setBusca] = useState('');

  const lista = EVENTOS.filter((e) => {
    if (tab !== 'todos' && e.cat !== tab) return false;
    if (busca && !(`${e.ator} ${e.acao} ${e.alvo}`.toLowerCase().includes(busca.toLowerCase()))) return false;
    return true;
  });

  return (
    <>
      <PageHeader
        title="Auditoria LGPD"
        subtitle="Trilha imutável de eventos do sistema · retenção: 5 anos"
        actions={<Button variant="secondary" icon="download">Exportar 7 dias</Button>}
      />

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', borderRadius: 10, background: theme.hover, marginBottom: 14 }}>
        <Icon name="lock" size={15} color={theme.fgMuted} />
        <span style={{ fontSize: 12.5, color: theme.fgMuted }}>Demonstração da trilha. A auditoria real (tabela <code>audit_log</code> imutável) entra com a auth/role de admin.</span>
      </div>

      <Card padding={0}>
        <div style={{ padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 12, borderBottom: `1px solid ${theme.border}`, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', gap: 4, flex: 1 }}>
            {TABS.map(([id, l]) => (
              <button key={id} onClick={() => setTab(id)} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 10px', borderRadius: 8, border: 'none', cursor: 'pointer', background: tab === id ? theme.hover : 'transparent', color: tab === id ? theme.fg : theme.fgMuted, fontSize: 12.5, fontWeight: tab === id ? 700 : 500 }}>
                {l}{id === 'todos' ? <span style={{ fontSize: 10.5, fontWeight: 700, color: theme.fgMuted, background: theme.hover, padding: '1px 7px', borderRadius: 9999 }}>{EVENTOS.length}</span> : null}
              </button>
            ))}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px', borderRadius: 8, border: `1px solid ${theme.border}`, background: theme.bg, minWidth: 220 }}>
            <Icon name="search" size={14} color={theme.fgSubtle} />
            <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Filtrar por ator, ação…" style={{ flex: 1, border: 'none', outline: 'none', background: 'transparent', color: theme.fg, fontSize: 12.5 }} />
          </div>
        </div>

        {/* header */}
        <div style={{ display: 'grid', gridTemplateColumns: '90px 1.4fr 1.1fr 1.2fr 120px', padding: '10px 16px', fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: theme.fgSubtle, borderBottom: `1px solid ${theme.border}` }}>
          <span>Quando</span><span>Ator</span><span>Ação</span><span>Alvo</span><span style={{ textAlign: 'right' }}>IP</span>
        </div>

        {lista.map((e, i) => (
          <div key={i} style={{ display: 'grid', gridTemplateColumns: '90px 1.4fr 1.1fr 1.2fr 120px', alignItems: 'center', padding: '13px 16px', borderBottom: i < lista.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
            <span style={{ fontSize: 12, color: theme.fgMuted }}>{e.quando}</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 9, minWidth: 0 }}>
              <span style={{ width: 26, height: 26, borderRadius: 9999, background: e.sistema ? theme.hover : 'linear-gradient(135deg,#0D2B5E,#2E7DD1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: e.sistema ? theme.fgMuted : '#fff', fontSize: 9.5, fontWeight: 800, flexShrink: 0 }}>
                {e.sistema ? <Icon name="gear" size={13} color={theme.fgMuted} /> : e.av}
              </span>
              <span style={{ fontFamily: 'var(--font-mono), monospace', fontSize: 12.5, color: theme.fg, overflow: 'hidden', textOverflow: 'ellipsis' }}>{e.ator}</span>
            </span>
            <span style={{ fontFamily: 'var(--font-mono), monospace', fontSize: 12.5, fontWeight: 600, color: theme.sky }}>{e.acao}</span>
            <span style={{ fontSize: 12.5, color: theme.fg }}>{e.alvo}</span>
            <span style={{ textAlign: 'right', fontFamily: 'var(--font-mono), monospace', fontSize: 12, color: theme.fgSubtle }}>{e.ip}</span>
          </div>
        ))}
      </Card>
    </>
  );
}
