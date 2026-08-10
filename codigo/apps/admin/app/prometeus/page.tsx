'use client';
import { useState } from 'react';
import { useAdmTheme } from '../../lib/theme';
import { PROMETEUS_KPIS, PROMETEUS_CUSTO, PROMETEUS_LATENCIA, PROMETEUS_DISTRIBUICAO } from '../../lib/demo';
import { Card, PageHeader, SectionLabel, Badge, Selo } from '../../components/ui';
import { KpiCard, AreaChart, Button } from '../../components/charts';
import { Icon, type IconName } from '../../components/Icon';

type Aba = 'telemetria' | 'auditoria' | 'config';
const ABAS: { id: Aba; icon: IconName; label: string; badge?: string }[] = [
  { id: 'telemetria', icon: 'trend', label: 'Telemetria' },
  { id: 'auditoria', icon: 'shield', label: 'Auditoria humana', badge: '4' },
  { id: 'config', icon: 'gear', label: 'Configuração' },
];

const HORA = [0.08, 0.06, 0.05, 0.05, 0.05, 0.07, 0.12, 0.22, 0.34, 0.42, 0.48, 0.52, 0.62, 0.7, 0.92, 0.96, 0.9, 0.8, 0.55, 0.45, 0.35, 0.25, 0.16, 0.1];
const DIA = [0.78, 0.95, 0.98, 0.92, 0.7, 0.5, 0.42];
const DIAS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];

export default function Prometeus() {
  const { theme } = useAdmTheme();
  const [aba, setAba] = useState<Aba>('telemetria');
  const acc = [theme.accent, theme.warn, theme.sky, theme.pos];
  const latCor = { pos: theme.pos, warn: theme.warn, neg: theme.neg };

  return (
    <>
      <PageHeader
        title="Prometeus IA"
        subtitle="Telemetria do Oráculo · custo · auditoria humana das saídas"
        actions={<>
          <Button variant="secondary" icon="cal">Últimos 30 dias</Button>
          <Button variant="secondary" icon="download">Exportar</Button>
        </>}
      />

      <div style={{ display: 'flex', gap: 4, marginBottom: 14, flexWrap: 'wrap' }}>
        {ABAS.map((a) => (
          <button key={a.id} onClick={() => setAba(a.id)} style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: '9px 14px', borderRadius: 9, border: `1px solid ${aba === a.id ? theme.borderStrong : 'transparent'}`, background: aba === a.id ? theme.surface : 'transparent', color: aba === a.id ? theme.fg : theme.fgMuted, cursor: 'pointer', fontSize: 13, fontWeight: aba === a.id ? 700 : 500 }}>
            <Icon name={a.icon} size={15} color={aba === a.id ? theme.accent : theme.fgMuted} />{a.label}
            {a.badge ? <span style={{ fontSize: 11, color: theme.fgSubtle }}>{a.badge}</span> : null}
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', borderRadius: 10, background: theme.warnSoft, marginBottom: 14 }}>
        <Icon name="alert" size={15} color={theme.warn} />
        <span style={{ fontSize: 12.5, color: theme.fg }}><b>Demonstração.</b> A telemetria real (custo, tokens, latência) aparece quando o agente <b>Prometeus</b> for ligado.</span>
      </div>

      {aba !== 'telemetria' ? (
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '18px 4px' }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: theme.accentSoft, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Icon name={aba === 'auditoria' ? 'shield' : 'gear'} size={20} color={theme.accent} />
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: theme.fg }}>{aba === 'auditoria' ? 'Auditoria humana' : 'Configuração'} — em construção</div>
              <div style={{ marginTop: 3, fontSize: 12.5, color: theme.fgMuted, lineHeight: 1.5 }}>
                {aba === 'auditoria'
                  ? 'Amostragem e revisão humana das saídas do agente (contra a fonte oficial) — entra com o agente.'
                  : 'Modelos, limites de custo/rate, guarda-corpos e o contrato de resposta — definidos ao construir o agente.'}
              </div>
            </div>
          </div>
        </Card>
      ) : (
        <>
          {/* KPIs */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 14 }}>
            {PROMETEUS_KPIS.map((k, i) => (
              <KpiCard key={k.label} label={k.label} value={k.value} sub={k.sub} delta={k.delta} trend={k.trend} accent={acc[i]} icon={k.icon} selo="amostra" />
            ))}
          </div>

          {/* Custo diário + Latência */}
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 12, marginBottom: 14, alignItems: 'start' }}>
            <Card>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><SectionLabel>Custo diário · 30 dias</SectionLabel><Selo tipo="amostra" /></div>
                  <div style={{ marginTop: 5, display: 'flex', alignItems: 'baseline', gap: 8 }}>
                    <span style={{ fontWeight: 800, fontSize: 24, color: theme.fg }}>{PROMETEUS_CUSTO.media}</span>
                    <span style={{ fontSize: 12, color: theme.fgMuted }}>média/dia</span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 14, fontSize: 11, color: theme.fgMuted }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}><span style={{ width: 8, height: 8, borderRadius: 9999, background: theme.warn }} />OpenAI</span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}><span style={{ width: 8, height: 8, borderRadius: 9999, background: theme.sky }} />Anthropic</span>
                </div>
              </div>
              <AreaChart data={PROMETEUS_CUSTO.serie} labels={PROMETEUS_CUSTO.labels} w={640} h={190} accent={theme.warn} />
            </Card>

            <Card>
              <SectionLabel>Latência p50 / p95 / p99</SectionLabel>
              <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
                {PROMETEUS_LATENCIA.map((l) => (
                  <div key={l.label}>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 5 }}>
                      <span style={{ fontFamily: 'var(--font-mono), monospace', fontSize: 11, color: theme.fgSubtle }}>{l.label}</span>
                      <span style={{ fontSize: 15, fontWeight: 800, color: theme.fg }}>{l.v}</span>
                    </div>
                    <div style={{ height: 6, borderRadius: 9999, background: theme.hover, overflow: 'hidden' }}>
                      <div style={{ width: `${l.pct}%`, height: '100%', background: latCor[l.tone], borderRadius: 9999 }} />
                    </div>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 16, paddingTop: 14, borderTop: `1px solid ${theme.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: theme.fgMuted }}>SLO p95 &lt; 5s</span>
                <Badge tone="pos">96% conformidade</Badge>
              </div>
            </Card>
          </div>

          {/* Distribuição + Heatmap */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, alignItems: 'start' }}>
            <Card>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><SectionLabel>Distribuição por tema · 30d</SectionLabel><Selo tipo="amostra" /></div>
                <span style={{ fontSize: 11.5, color: theme.fgMuted }}>7.748 perguntas</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {PROMETEUS_DISTRIBUICAO.map((d) => (
                  <div key={d.tema}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 5 }}>
                      <span style={{ fontSize: 12.5, color: theme.fg, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.tema}</span>
                      <span style={{ flexShrink: 0, fontFamily: 'var(--font-mono), monospace', fontSize: 11.5, color: theme.fgMuted }}>{d.n} · {d.pct}%</span>
                    </div>
                    <div style={{ height: 6, borderRadius: 9999, background: theme.hover, overflow: 'hidden' }}>
                      <div style={{ width: `${d.pct * 4}%`, maxWidth: '100%', height: '100%', background: theme.sky, borderRadius: 9999 }} />
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}><SectionLabel>Heatmap de uso · semana × hora</SectionLabel><Selo tipo="amostra" /></div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {DIAS.map((d, r) => (
                  <div key={d} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ width: 26, fontSize: 10, color: theme.fgSubtle }}>{d}</span>
                    <div style={{ flex: 1, display: 'grid', gridTemplateColumns: 'repeat(24, 1fr)', gap: 3 }}>
                      {Array.from({ length: 24 }).map((_, h) => (
                        <div key={h} style={{ paddingTop: '100%', borderRadius: 2, background: theme.sky, opacity: 0.08 + HORA[h] * DIA[r] * 0.9 }} />
                      ))}
                    </div>
                  </div>
                ))}
                <div style={{ display: 'flex', justifyContent: 'space-between', marginLeft: 32, marginTop: 4, fontSize: 9.5, fontFamily: 'var(--font-mono), monospace', color: theme.fgSubtle }}>
                  <span>00h</span><span>06h</span><span>12h</span><span>18h</span><span>23h</span>
                </div>
              </div>
              <div style={{ marginTop: 10, fontSize: 11.5, color: theme.fgSubtle }}>Pico: ter–qui 14h–17h</div>
            </Card>
          </div>
        </>
      )}
    </>
  );
}
