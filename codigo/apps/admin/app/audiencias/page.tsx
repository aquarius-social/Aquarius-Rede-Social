'use client';
import { useState } from 'react';
import { useAdmTheme } from '../../lib/theme';
import { AUDIENCIAS_KPIS, AUDIENCIAS_BARRAS, AUDIENCIAS_PRONTAS } from '../../lib/demo';
import { Card, PageHeader, SectionLabel, Badge, Selo } from '../../components/ui';
import { KpiCard, Button } from '../../components/charts';
import { Icon, type IconName } from '../../components/Icon';

const VIS: { id: string; icon: IconName; label: string }[] = [
  { id: 'crosstab', icon: 'grid', label: 'Cross-tab' },
  { id: 'barras', icon: 'trend', label: 'Barras' },
  { id: 'afinidade', icon: 'star', label: 'Afinidade' },
  { id: 'mapa', icon: 'globe', label: 'Mapa' },
  { id: 'tendencia', icon: 'spark', label: 'Tendência' },
];

export default function Audiencias() {
  const { theme } = useAdmTheme();
  const [vis, setVis] = useState('barras');
  const acc = [theme.sky, theme.pos, theme.accent, theme.warn];
  const maxEng = Math.max(...AUDIENCIAS_BARRAS.map((b) => b.engajado));

  return (
    <>
      <PageHeader
        title="Audiências & DaaS"
        subtitle="Quem engaja com o quê — por região, idade, sexo, renda e mais. Agregado, anônimo e pronto para exportar."
        actions={<>
          <Button variant="secondary" icon="doc">Catálogo</Button>
          <Button variant="primary" icon="plus">Novo relatório</Button>
        </>}
      />

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', borderRadius: 10, background: theme.warnSoft, marginBottom: 14 }}>
        <Icon name="alert" size={15} color={theme.warn} />
        <span style={{ fontSize: 12.5, color: theme.fg }}><b>Demonstração.</b> O DaaS só é vendável com base de usuários consentidos em escala (k-anonimato). Números ilustrativos.</span>
      </div>

      {/* KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 14 }}>
        {AUDIENCIAS_KPIS.map((k, i) => (
          <KpiCard key={k.label} label={k.label} value={k.value} sub={k.sub} delta={k.delta} trend={k.trend} accent={acc[i]} icon={k.icon} selo="amostra" />
        ))}
      </div>

      {/* Construtor */}
      <Card padding={0} style={{ marginBottom: 14 }}>
        <div style={{ padding: '16px', borderBottom: `1px solid ${theme.border}`, display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div>
            <SectionLabel>Eixo · engajamento com</SectionLabel>
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <Select theme={theme} v="Tema" /><Select theme={theme} v="Educação" w={180} />
            </div>
          </div>
          <div>
            <SectionLabel>Recorte · por</SectionLabel>
            <div style={{ marginTop: 8 }}><Select theme={theme} v="Região" /></div>
          </div>
          <div style={{ marginLeft: 'auto' }}>
            <SectionLabel>Visualização</SectionLabel>
            <div style={{ display: 'flex', gap: 4, marginTop: 8, border: `1px solid ${theme.border}`, borderRadius: 9, padding: 3 }}>
              {VIS.map((o) => (
                <button key={o.id} onClick={() => setVis(o.id)} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 11px', borderRadius: 7, border: 'none', cursor: 'pointer', background: vis === o.id ? theme.sky : 'transparent', color: vis === o.id ? '#fff' : theme.fgMuted, fontSize: 12, fontWeight: 600 }}>
                  <Icon name={o.icon} size={13} color={vis === o.id ? '#fff' : theme.fgMuted} />{o.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Sub-header */}
        <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${theme.border}`, flexWrap: 'wrap', gap: 8 }}>
          <span style={{ fontSize: 12.5, color: theme.fgMuted }}>
            <b style={{ color: theme.fg }}>Educação</b> · coorte 58,9K · Recorte por região · cobertura do dado <b style={{ color: theme.pos }}>96%</b> (CEP no onboarding)
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '4px 10px', borderRadius: 9999, background: theme.posSoft, color: theme.pos, fontSize: 11, fontWeight: 700 }}><Icon name="lock" size={12} color={theme.pos} />k-anon ≥ 1.000</span>
        </div>

        {/* Barras */}
        <div style={{ padding: '16px' }}>
          {AUDIENCIAS_BARRAS.map((b) => (
            <div key={b.regiao} style={{ display: 'grid', gridTemplateColumns: '110px 1fr 40px', alignItems: 'center', gap: 14, marginBottom: 16 }}>
              <span style={{ fontSize: 13.5, fontWeight: 700, color: theme.fg }}>{b.regiao}</span>
              <div>
                <div style={{ position: 'relative', height: 22, background: theme.hover, borderRadius: 6 }}>
                  <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${(b.engajado / maxEng) * 100}%`, background: `linear-gradient(90deg, ${theme.blue}, ${theme.sky})`, borderRadius: 6 }} />
                  <div style={{ position: 'absolute', top: -2, bottom: -2, left: `${(b.base / maxEng) * 100}%`, width: 2, background: theme.fgSubtle }} title="média da base" />
                </div>
                <div style={{ marginTop: 5, fontSize: 11, color: theme.fgSubtle }}>engajado {b.engajado}% · base {b.base}%</div>
              </div>
              <span style={{ textAlign: 'right', fontFamily: 'var(--font-mono), monospace', fontSize: 13, fontWeight: 700, color: b.index >= 100 ? theme.pos : b.index < 90 ? theme.warn : theme.fg }}>{b.index}</span>
            </div>
          ))}
          <div style={{ fontSize: 11, color: theme.fgSubtle, marginTop: 4 }}>│ linha = média da base · índice ≥ 100 = acima da média</div>
        </div>

        {/* Exportar */}
        <div style={{ padding: '14px 16px', borderTop: `1px solid ${theme.border}`, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: theme.fgMuted }}>Exportar:</span>
          {([['CSV', 'download'], ['PDF', 'doc'], ['API', 'sync'], ['Link', 'send']] as const).map(([l, ic]) => (
            <button key={l} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 11px', borderRadius: 8, border: `1px solid ${theme.borderStrong}`, background: 'transparent', color: theme.fg, cursor: 'pointer', fontSize: 12, fontWeight: 600 }}><Icon name={ic} size={13} color={theme.fg} />{l}</button>
          ))}
          <span style={{ marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11.5, color: theme.pos }}><Icon name="shield" size={13} color={theme.pos} />Apenas agregados anônimos · nenhum dado individual exportável</span>
        </div>
      </Card>

      {/* Análises prontas */}
      <Card padding={0}>
        <div style={{ padding: '14px 16px', borderBottom: `1px solid ${theme.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <SectionLabel>Análises prontas · destaques</SectionLabel>
            <div style={{ marginTop: 3, fontSize: 11.5, color: theme.fgMuted }}>Clique para abrir no construtor acima</div>
          </div>
          <Badge tone="accent">{AUDIENCIAS_PRONTAS.length} relatórios</Badge>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, padding: 16 }}>
          {AUDIENCIAS_PRONTAS.map((a) => (
            <div key={a.titulo} style={{ padding: 14, borderRadius: 12, border: `1px solid ${theme.border}`, background: theme.surfaceAlt, cursor: 'pointer' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <div style={{ width: 32, height: 32, borderRadius: 8, background: theme.accentSoft, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon name={a.icon} size={16} color={theme.accent} /></div>
                {a.badge ? <Badge tone="muted">{a.badge}</Badge> : null}
              </div>
              <div style={{ fontSize: 12.5, fontWeight: 600, color: theme.fg, lineHeight: 1.35 }}>{a.titulo}</div>
            </div>
          ))}
        </div>
      </Card>
    </>
  );
}

function Select({ theme, v, w }: { theme: ReturnType<typeof useAdmTheme>['theme']; v: string; w?: number }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, minWidth: w ?? 130, padding: '10px 12px', borderRadius: 9, border: `1px solid ${theme.border}`, background: theme.bg, color: theme.fg, fontSize: 13, fontWeight: 600 }}>
      {v}<Icon name="chevR" size={13} color={theme.fgMuted} style={{ transform: 'rotate(90deg)' }} />
    </div>
  );
}
