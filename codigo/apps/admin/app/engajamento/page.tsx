'use client';
import { useAdmTheme } from '../../lib/theme';
import { ENGAJAMENTO_KPIS, RETENCAO_COORTE, PERFIS_CONSULTADOS, BUSCAS_FREQUENTES } from '../../lib/demo';
import { Card, PageHeader, SectionLabel, Selo } from '../../components/ui';
import { KpiCard, Button } from '../../components/charts';
import { Icon } from '../../components/Icon';

export default function Engajamento() {
  const { theme } = useAdmTheme();
  const acc = [theme.sky, theme.blue, theme.accent, theme.pos];
  const pill = (v: number | null) => (v == null ? null : { background: theme.sky, opacity: 0.18 + (v / 100) * 0.8 });

  return (
    <>
      <PageHeader
        title="Engajamento"
        subtitle="Engajamento da rede cívica · iOS + Android · funil visitante → feed → premium"
        actions={<>
          <Button variant="secondary" icon="cal">Últimos 30 dias</Button>
          <Button variant="secondary" icon="download">Exportar</Button>
        </>}
      />

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', borderRadius: 10, background: theme.warnSoft, marginBottom: 14 }}>
        <Icon name="alert" size={15} color={theme.warn} />
        <span style={{ fontSize: 12.5, color: theme.fg }}><b>Demonstração.</b> Métricas de engajamento dependem do analytics de produto, ainda não coletado.</span>
      </div>

      {/* KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 14 }}>
        {ENGAJAMENTO_KPIS.map((k, i) => (
          <KpiCard key={k.label} label={k.label} value={k.value} sub={k.sub} delta={k.delta} trend={k.trend} accent={acc[i]} icon={k.icon} selo="amostra" />
        ))}
      </div>

      {/* Retenção por coorte */}
      <Card padding={0} style={{ marginBottom: 14 }}>
        <div style={{ padding: '14px 16px', borderBottom: `1px solid ${theme.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><SectionLabel>Retenção por coorte semanal</SectionLabel><Selo tipo="amostra" /></div>
            <div style={{ marginTop: 3, fontSize: 11.5, color: theme.fgMuted }}>D1, D7, D30 · últimas 7 semanas</div>
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr', padding: '10px 16px', fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: theme.fgSubtle, borderBottom: `1px solid ${theme.border}` }}>
          <span>Semana</span><span>Cohort</span><span style={{ textAlign: 'center' }}>D1</span><span style={{ textAlign: 'center' }}>D7</span><span style={{ textAlign: 'center' }}>D30</span>
        </div>
        {RETENCAO_COORTE.map((r, i) => (
          <div key={r.semana} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr', alignItems: 'center', padding: '9px 16px', borderBottom: i < RETENCAO_COORTE.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: theme.fg }}>{r.semana}</span>
            <span style={{ fontFamily: 'var(--font-mono), monospace', fontSize: 12.5, color: theme.fgMuted }}>{r.cohort}</span>
            {[r.d1, r.d7, r.d30].map((v, j) => (
              <span key={j} style={{ textAlign: 'center' }}>
                {v == null ? <span style={{ color: theme.fgSubtle }}>—</span> : (
                  <span style={{ display: 'inline-block', minWidth: 52, padding: '4px 0', borderRadius: 7, ...pill(v), color: v >= 45 ? '#fff' : theme.fg, fontFamily: 'var(--font-mono), monospace', fontSize: 12, fontWeight: 700 }}>{v}%</span>
                )}
              </span>
            ))}
          </div>
        ))}
      </Card>

      {/* Perfis + Buscas */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, alignItems: 'start' }}>
        <Card padding={0}>
          <div style={{ padding: '14px 16px', borderBottom: `1px solid ${theme.border}`, display: 'flex', alignItems: 'center', gap: 8 }}><SectionLabel>Perfis mais consultados · 7d</SectionLabel><Selo tipo="amostra" /></div>
          {PERFIS_CONSULTADOS.map((p, i) => (
            <div key={p.nome} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', borderBottom: i < PERFIS_CONSULTADOS.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
              <span style={{ width: 18, fontFamily: 'var(--font-mono), monospace', fontSize: 12, color: theme.fgSubtle }}>{i + 1}</span>
              <span style={{ width: 32, height: 32, borderRadius: 9999, background: 'linear-gradient(135deg,#0D2B5E,#2E7DD1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 10, fontWeight: 800, flexShrink: 0 }}>{p.av}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: theme.fg }}>{p.nome}</div>
                <div style={{ marginTop: 2, fontSize: 11, color: theme.fgSubtle }}>{p.sub}</div>
              </div>
              <span style={{ fontFamily: 'var(--font-mono), monospace', fontSize: 12.5, fontWeight: 600, color: theme.fg }}>{p.valor}</span>
              <span style={{ fontSize: 11.5, fontWeight: 600, color: theme.pos, minWidth: 46, textAlign: 'right' }}>{p.delta}</span>
            </div>
          ))}
        </Card>

        <Card padding={0}>
          <div style={{ padding: '14px 16px', borderBottom: `1px solid ${theme.border}`, display: 'flex', alignItems: 'center', gap: 8 }}><SectionLabel>Buscas mais frequentes · 30d</SectionLabel><Selo tipo="amostra" /></div>
          {BUSCAS_FREQUENTES.map((b, i) => (
            <div key={b.termo} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '13px 16px', borderBottom: i < BUSCAS_FREQUENTES.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
              <span style={{ width: 18, fontFamily: 'var(--font-mono), monospace', fontSize: 12, color: theme.fgSubtle }}>{i + 1}</span>
              <span style={{ flex: 1, fontSize: 13, color: theme.fg }}>{b.termo}</span>
              <span style={{ fontFamily: 'var(--font-mono), monospace', fontSize: 12.5, fontWeight: 600, color: theme.fg }}>{b.valor}</span>
              <span style={{ fontSize: 11.5, fontWeight: 600, color: theme.pos, minWidth: 46, textAlign: 'right' }}>{b.delta}</span>
            </div>
          ))}
        </Card>
      </div>
    </>
  );
}
