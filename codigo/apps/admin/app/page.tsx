'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useAdmTheme } from '../lib/theme';
import { contagens, despesasTotal, ultimoSync, type Contagens } from '../lib/dados';
import { PIPES, saudePipelines } from '../lib/pipelines';
import { KPIS_VISAO, ATIVIDADE_APP, SAUDE_STATS, TOP_TEMAS } from '../lib/demo';
import { Card, PageHeader, SectionLabel, Badge, Selo } from '../components/ui';
import { KpiCard, AreaChart, Donut, StatusDot, Button, admFmtK } from '../components/charts';
import { Icon } from '../components/Icon';

const dataBR = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString('pt-BR') : '—');

export default function Overview() {
  const { theme } = useAdmTheme();
  const [c, setC] = useState<Contagens | null>(null);
  const [desp, setDesp] = useState(0);
  const [sync, setSync] = useState<string | null>(null);

  useEffect(() => {
    contagens().then(setC).catch(() => {});
    despesasTotal().then(setDesp).catch(() => {});
    ultimoSync().then(setSync).catch(() => {});
  }, []);

  const saude = saudePipelines();

  return (
    <>
      <PageHeader
        title="Visão geral"
        subtitle={`Sinais críticos da rede social cívica · base sincronizada em ${dataBR(sync)}`}
        actions={<>
          <Button variant="secondary" icon="cal">Últimos 30 dias</Button>
          <Button variant="secondary" icon="download">Exportar</Button>
        </>}
      />

      {/* KPIs — estrutura do protótipo; placeholder (amostra) até analytics + agente */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 12 }}>
        {KPIS_VISAO.map((k, i) => (
          <KpiCard key={k.label} label={k.label} value={k.value} sub={k.sub} delta={k.delta} trend={k.trend}
            accent={[theme.sky, theme.accent, theme.warn, theme.pos][i]} icon={k.icon} selo="amostra" />
        ))}
      </div>

      {/* Atividade do app + Saúde do sistema */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 12, marginBottom: 12 }}>
        <Card>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><SectionLabel>Atividade do app · 24h</SectionLabel><Selo tipo="amostra" /></div>
              <div style={{ marginTop: 5, display: 'flex', alignItems: 'baseline', gap: 10 }}>
                <span style={{ fontWeight: 800, fontSize: 24, color: theme.fg, letterSpacing: '-0.02em' }}>{ATIVIDADE_APP.total}</span>
                <span style={{ fontSize: 12, color: theme.fgMuted }}>sessões nas últimas 24 horas</span>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 14, fontSize: 11, color: theme.fgMuted }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}><span style={{ width: 8, height: 8, borderRadius: 9999, background: theme.sky }} />Sessões</span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}><span style={{ width: 8, height: 8, borderRadius: 9999, background: theme.accent, opacity: 0.6 }} />Perguntas Prometeus</span>
            </div>
          </div>
          <AreaChart data={ATIVIDADE_APP.serie} labels={ATIVIDADE_APP.labels} w={640} h={180} accent={theme.sky} />
        </Card>

        <Card>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><SectionLabel>Saúde do sistema</SectionLabel><Selo tipo="real" /></div>
            <Badge tone={saude.fora > saude.ok ? 'warn' : 'pos'}>{saude.fora > saude.ok ? 'ATENÇÃO' : 'OK'}</Badge>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <Donut data={[{ value: saude.ok, color: theme.pos }, { value: saude.parcial, color: theme.warn }, { value: saude.fora, color: theme.neg }]} w={120} />
            <div style={{ flex: 1, fontSize: 12, color: theme.fg }}>
              {[['Pipelines OK', saude.ok, theme.pos], ['Com avisos', saude.parcial, theme.warn], ['Falhas', saude.fora, theme.neg]].map(([l, n, cor]) => (
                <div key={l as string} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <span style={{ width: 8, height: 8, borderRadius: 9999, background: cor as string }} />
                  <span style={{ flex: 1 }}>{l as string}</span>
                  <span style={{ fontWeight: 700 }}>{n as number}</span>
                </div>
              ))}
            </div>
          </div>
          <div style={{ marginTop: 14, paddingTop: 14, borderTop: `1px solid ${theme.border}`, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {[['uptime · 30d', `${SAUDE_STATS.uptime}`, '%'], ['erros · 24h', `${SAUDE_STATS.erros}`, '/h']].map(([l, v, u]) => (
              <div key={l}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
                  <span style={{ fontWeight: 800, fontSize: 18, color: theme.fg }}>{v}</span><span style={{ fontSize: 12, color: theme.fgMuted }}>{u}</span>
                </div>
                <div style={{ marginTop: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: theme.fgMuted }}>{l}</span><Selo tipo="amostra" />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Pipelines status (real) + Top temas Prometeus (amostra) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 12 }}>
        <Card padding={0}>
          <div style={{ padding: '14px 16px', borderBottom: `1px solid ${theme.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><SectionLabel>Pipelines · status</SectionLabel><Selo tipo="real" /></div>
              <div style={{ marginTop: 3, fontSize: 11.5, color: theme.fgMuted }}>Resumo dos {PIPES.length} pipelines monitorados</div>
            </div>
            <Link href="/pipelines" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, color: theme.fgMuted }}>Ver todas<Icon name="chevR" size={13} color={theme.fgMuted} /></Link>
          </div>
          {PIPES.slice(0, 6).map((p, i, arr) => {
            const reg = c ? p.reg(c, desp) : null;
            return (
              <div key={p.id} style={{ padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 12, borderBottom: i < arr.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
                <StatusDot status={p.estado} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12.5, fontWeight: 600, color: theme.fg }}>{p.nome}</div>
                  <div style={{ marginTop: 2, fontFamily: 'var(--font-mono), monospace', fontSize: 10.5, color: theme.fgSubtle }}>{p.fonte} · {p.freq}</div>
                </div>
                <span style={{ fontFamily: 'var(--font-mono), monospace', fontSize: 12, fontWeight: 600, color: reg == null ? theme.fgSubtle : theme.fg }}>{reg == null ? '—' : admFmtK(reg)}</span>
              </div>
            );
          })}
        </Card>

        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}><SectionLabel>Top temas · Prometeus · 30d</SectionLabel><Selo tipo="amostra" /></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {TOP_TEMAS.map((t) => (
              <div key={t.label}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 5 }}>
                  <span style={{ fontSize: 12, color: theme.fg, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.label}</span>
                  <span style={{ flexShrink: 0, fontFamily: 'var(--font-mono), monospace', fontSize: 11.5, color: theme.fgMuted }}>{t.valor} · {t.pct}%</span>
                </div>
                <div style={{ height: 6, borderRadius: 9999, background: theme.hover, overflow: 'hidden' }}>
                  <div style={{ width: `${t.pct * 4}%`, maxWidth: '100%', height: '100%', background: theme.sky, borderRadius: 9999 }} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </>
  );
}
