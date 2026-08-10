'use client';
import { useState } from 'react';
import { useAdmTheme } from '../../lib/theme';
import { Card, PageHeader, Badge } from '../../components/ui';
import { Button } from '../../components/charts';
import { Icon } from '../../components/Icon';

type Estagio = 'rollout' | 'beta' | 'ga' | 'experiment';
const FLAGS: { chave: string; desc: string; estagio: Estagio; pct: string; on: boolean }[] = [
  { chave: 'feed.algoV2', desc: 'Novo algoritmo de recomendação do feed', estagio: 'rollout', pct: '20%', on: false },
  { chave: 'stories.autoPublish', desc: 'Publicação automática de stories de alta confiança', estagio: 'beta', pct: 'beta', on: false },
  { chave: 'mod.autoRemoveSpam', desc: 'Auto-remoção de spam com confiança IA > 95%', estagio: 'ga', pct: '100%', on: true },
  { chave: 'feed.liveBadge', desc: 'Selo "ao vivo" em sessões em andamento', estagio: 'ga', pct: '100%', on: true },
  { chave: 'comments.communityNotes', desc: 'Notas da comunidade em posts contestados', estagio: 'experiment', pct: '5%', on: false },
];
const EST_TONE: Record<Estagio, 'accent' | 'pos' | 'warn'> = { rollout: 'accent', beta: 'accent', ga: 'pos', experiment: 'warn' };

export default function Flags() {
  const { theme } = useAdmTheme();
  const [estado, setEstado] = useState<Record<string, boolean>>(() => Object.fromEntries(FLAGS.map((f) => [f.chave, f.on])));

  return (
    <>
      <PageHeader
        title="Feature flags"
        subtitle="Controle de rollout e experimentos A/B"
        actions={<Button variant="primary" icon="plus">Nova flag</Button>}
      />

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', borderRadius: 10, background: theme.hover, marginBottom: 14 }}>
        <Icon name="flag" size={15} color={theme.fgMuted} />
        <span style={{ fontSize: 12.5, color: theme.fgMuted }}>Os toggles funcionam localmente para demonstrar o controle — a persistência (tabela <code>feature_flags</code> + leitura pelo app/admin) é backlog.</span>
      </div>

      <Card padding={0}>
        {FLAGS.map((f, i) => {
          const on = estado[f.chave];
          return (
            <div key={f.chave} style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '16px 18px', borderBottom: i < FLAGS.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontFamily: 'var(--font-mono), monospace', fontSize: 13.5, fontWeight: 600, color: theme.sky }}>{f.chave}</div>
                <div style={{ marginTop: 4, fontSize: 12.5, color: theme.fgMuted }}>{f.desc}</div>
              </div>
              <Badge tone={EST_TONE[f.estagio]}>{f.estagio}</Badge>
              <span style={{ width: 46, textAlign: 'right', fontFamily: 'var(--font-mono), monospace', fontSize: 12.5, color: theme.fgMuted }}>{f.pct}</span>
              <button onClick={() => setEstado((e) => ({ ...e, [f.chave]: !e[f.chave] }))} aria-label={`Alternar ${f.chave}`}
                style={{ width: 46, height: 26, borderRadius: 9999, border: 'none', cursor: 'pointer', background: on ? theme.pos : theme.borderStrong, position: 'relative', transition: 'background .15s', flexShrink: 0 }}>
                <span style={{ position: 'absolute', top: 3, left: on ? 23 : 3, width: 20, height: 20, borderRadius: 9999, background: '#fff', transition: 'left .15s' }} />
              </button>
            </div>
          );
        })}
      </Card>
    </>
  );
}
