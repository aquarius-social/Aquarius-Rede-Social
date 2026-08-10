'use client';
import { useState } from 'react';
import { useAdmTheme } from '../../lib/theme';
import { Card, PageHeader, SectionLabel, Badge } from '../../components/ui';
import { Button } from '../../components/charts';
import { Icon } from '../../components/Icon';
import { PERMISSOES, PAPEIS, MEMBROS } from '../../lib/demo/equipe';

export default function Equipe() {
  const { theme } = useAdmTheme();
  const [sel, setSel] = useState('chefe');
  const papel = PAPEIS.find((p) => p.id === sel) ?? PAPEIS[0];

  return (
    <>
      <PageHeader
        title="Equipe & Permissões"
        subtitle="Quem pode publicar, moderar e — crítico para a LGPD — exportar dados. Cada ação fica registrada na Auditoria."
        actions={<>
          <Button variant="secondary" icon="doc">Log de acessos</Button>
          <Button variant="primary" icon="plus">Convidar membro</Button>
        </>}
      />

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', borderRadius: 10, background: theme.hover, marginBottom: 14 }}>
        <Icon name="users" size={15} color={theme.fgMuted} />
        <span style={{ fontSize: 12.5, color: theme.fgMuted }}>Demonstração de papéis e permissões (RBAC). O time e o controle real dependem da auth/role de admin (backlog).</span>
      </div>

      {/* Cards de papel */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 14 }}>
        {PAPEIS.map((p) => {
          const on = p.id === sel;
          return (
            <button key={p.id} onClick={() => setSel(p.id)} style={{ textAlign: 'left', padding: 16, borderRadius: 14, border: `1px solid ${on ? theme.sky : theme.border}`, background: on ? theme.hover : theme.surface, cursor: 'pointer' }}>
              <Badge tone="accent">{p.membros} membros</Badge>
              <div style={{ marginTop: 12, fontSize: 16, fontWeight: 800, color: theme.fg }}>{p.nome}</div>
              <div style={{ marginTop: 4, fontSize: 12, color: theme.fgMuted }}>{p.perm.length} permiss{p.perm.length === 1 ? 'ão' : 'ões'}</div>
            </button>
          );
        })}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: 12, alignItems: 'start' }}>
        {/* Matriz */}
        <Card padding={0}>
          <div style={{ padding: '14px 16px', borderBottom: `1px solid ${theme.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <SectionLabel>Permissões · {papel.nome}</SectionLabel>
            <button style={{ display: 'inline-flex', alignItems: 'center', gap: 6, border: 'none', background: 'transparent', color: theme.fgMuted, cursor: 'pointer', fontSize: 12, fontWeight: 600 }}><Icon name="gear" size={13} color={theme.fgMuted} />Editar papel</button>
          </div>
          {PERMISSOES.map((perm, i) => {
            const on = papel.perm.includes(i);
            return (
              <div key={perm.l} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '13px 16px', borderBottom: i < PERMISSOES.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
                <span style={{ width: 40, height: 22, borderRadius: 9999, background: on ? theme.pos : theme.borderStrong, position: 'relative', flexShrink: 0 }}>
                  <span style={{ position: 'absolute', top: 3, left: on ? 21 : 3, width: 16, height: 16, borderRadius: 9999, background: '#fff' }} />
                </span>
                <span style={{ flex: 1, fontSize: 13.5, fontWeight: 500, color: on ? theme.fg : theme.fgMuted }}>{perm.l}</span>
                {perm.s ? <Badge tone="warn">sensível</Badge> : null}
              </div>
            );
          })}
        </Card>

        {/* Membros */}
        <Card padding={0}>
          <div style={{ padding: '14px 16px', borderBottom: `1px solid ${theme.border}` }}><SectionLabel>Membros da equipe</SectionLabel></div>
          {MEMBROS.map((m, i) => (
            <div key={m.email} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '13px 16px', borderBottom: i < MEMBROS.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
              <span style={{ width: 34, height: 34, borderRadius: 9999, background: 'linear-gradient(135deg,#0D2B5E,#2E7DD1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 10.5, fontWeight: 800, flexShrink: 0 }}>{m.av}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 13.5, fontWeight: 700, color: theme.fg }}>{m.nome}</span>
                  {m.conv ? <Badge tone="warn">convidado</Badge> : null}
                </div>
                <div style={{ marginTop: 2, fontFamily: 'var(--font-mono), monospace', fontSize: 11, color: theme.fgSubtle }}>{m.email}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <Badge tone={m.tone}>{m.papel}</Badge>
                <div style={{ marginTop: 4, display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 5, fontSize: 10.5, color: m.twofa ? theme.pos : theme.warn }}>
                  <span style={{ width: 6, height: 6, borderRadius: 9999, background: m.twofa ? theme.pos : theme.warn }} />{m.twofa ? '2FA' : 'sem 2FA'} · {m.quando}
                </div>
              </div>
            </div>
          ))}
        </Card>
      </div>
    </>
  );
}
