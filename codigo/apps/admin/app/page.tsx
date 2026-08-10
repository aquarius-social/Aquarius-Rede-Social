'use client';
import { useEffect, useState } from 'react';
import { useAdmTheme } from '../lib/theme';
import { contagens, ultimoSync, emendasPorAno, type Contagens } from '../lib/dados';
import { Card, PageHeader, SectionLabel, Badge } from '../components/ui';
import { KpiCard, AreaChart, Donut, StatusDot, Button, admFmtK } from '../components/charts';

const fmt = (n: number) => n.toLocaleString('pt-BR');
const dataBR = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString('pt-BR') : '—');

const AREAS: { nome: string; fonte: string; freq: string; estado: 'ok' | 'parcial' | 'fora'; volume?: (c: Contagens) => number }[] = [
  { nome: 'Despesas Câmara (CEAP)', fonte: 'Portal da Transparência', freq: '2×/dia', estado: 'ok' },
  { nome: 'Despesas Senado (CEAPS)', fonte: 'Senado', freq: '2×/dia', estado: 'parcial' },
  { nome: 'Emendas parlamentares', fonte: 'Portal da Transparência', freq: 'diário', estado: 'ok', volume: (c) => c.emendas },
  { nome: 'Agenda / eventos', fonte: 'Câmara + Senado', freq: 'diário', estado: 'ok', volume: (c) => c.eventos },
  { nome: 'Comissões & Frentes', fonte: 'Câmara', freq: 'semanal', estado: 'ok', volume: (c) => c.comissoes + c.frentes },
  { nome: 'Proposições', fonte: 'Câmara + Senado', freq: '—', estado: 'fora' },
  { nome: 'Votações nominais', fonte: 'Câmara + Senado', freq: '—', estado: 'fora' },
  { nome: 'Presença', fonte: '(sem coletor)', freq: '—', estado: 'fora' },
];
const ROTULO = { ok: { t: 'pos' as const, l: 'No ar' }, parcial: { t: 'warn' as const, l: 'Parcial' }, fora: { t: 'neg' as const, l: 'Fora ⛔Pro' } };

export default function Overview() {
  const { theme } = useAdmTheme();
  const [c, setC] = useState<Contagens | null>(null);
  const [sync, setSync] = useState<string | null>(null);
  const [serie, setSerie] = useState<{ ano: number; total: number }[]>([]);

  useEffect(() => {
    contagens().then(setC).catch(() => {});
    ultimoSync().then(setSync).catch(() => {});
    emendasPorAno().then(setSerie).catch(() => {});
  }, []);

  const okN = AREAS.filter((a) => a.estado === 'ok').length;
  const parcN = AREAS.filter((a) => a.estado === 'parcial').length;
  const foraN = AREAS.filter((a) => a.estado === 'fora').length;

  return (
    <>
      <PageHeader
        title="Visão geral"
        subtitle={`Base de dados cívica · dinheiro sincronizado em ${dataBR(sync)}`}
        actions={<>
          <Button variant="secondary" icon="cal">Base 2023–2026</Button>
          <Button variant="secondary" icon="download">Exportar</Button>
        </>}
      />

      {/* KPIs reais */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 12 }}>
        <KpiCard label="Parlamentares" value={c ? fmt(c.parlamentares) : '…'} sub="em exercício · 2 casas" accent={theme.sky} icon="users" />
        <KpiCard label="Emendas" value={c ? admFmtK(c.emendas) : '…'} sub="2023–2026" accent={theme.warn} icon="list" trend={serie.length ? serie.map((s) => s.total) : undefined} />
        <KpiCard label="Eventos na agenda" value={c ? fmt(c.eventos) : '…'} sub="Câmara + Senado" accent={theme.pos} icon="cal" />
        <KpiCard label="Partidos" value={c ? fmt(c.partidos) : '…'} sub="com bancada" accent={theme.blue} icon="flag" />
      </div>

      {/* Área (emendas/ano) + Donut (saúde da ingestão) */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 12, marginBottom: 12 }}>
        <Card>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 14 }}>
            <div>
              <SectionLabel>Emendas registradas · por ano</SectionLabel>
              <div style={{ marginTop: 5, display: 'flex', alignItems: 'baseline', gap: 10 }}>
                <span style={{ fontWeight: 800, fontSize: 24, color: theme.fg, letterSpacing: '-0.02em' }}>{c ? admFmtK(c.emendas) : '…'}</span>
                <span style={{ fontSize: 12, color: theme.fgMuted }}>emendas na base · Portal da Transparência</span>
              </div>
            </div>
            <Badge tone="pos">dado real</Badge>
          </div>
          <AreaChart data={serie.length ? serie.map((s) => s.total) : [0, 0]} labels={serie.map((s) => String(s.ano))} w={640} h={180} accent={theme.sky} />
        </Card>

        <Card>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
            <SectionLabel>Saúde da ingestão</SectionLabel>
            <Badge tone={foraN > okN ? 'warn' : 'pos'}>{okN}/{AREAS.length} no ar</Badge>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <Donut data={[{ value: okN, color: theme.pos }, { value: parcN, color: theme.warn }, { value: foraN, color: theme.neg }]} w={120} />
            <div style={{ flex: 1, fontSize: 12, color: theme.fg }}>
              {[['No ar', okN, theme.pos], ['Parcial', parcN, theme.warn], ['Fora ⛔Pro', foraN, theme.neg]].map(([l, n, cor]) => (
                <div key={l as string} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <span style={{ width: 8, height: 8, borderRadius: 9999, background: cor as string }} />
                  <span style={{ flex: 1 }}>{l as string}</span>
                  <span style={{ fontWeight: 700 }}>{n as number}</span>
                </div>
              ))}
            </div>
          </div>
          <div style={{ marginTop: 14, paddingTop: 12, borderTop: `1px solid ${theme.border}`, fontSize: 11.5, color: theme.fgSubtle, lineHeight: 1.5 }}>
            As áreas “Fora” têm coletor pronto mas foram truncadas por espaço (Supabase Free). Ligam com o Pro.
          </div>
        </Card>
      </div>

      {/* Pipelines (real) + métricas de produto (honesto) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 12 }}>
        <Card padding={0}>
          <div style={{ padding: '14px 16px', borderBottom: `1px solid ${theme.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <SectionLabel>Pipelines · status</SectionLabel>
              <div style={{ marginTop: 3, fontSize: 11.5, color: theme.fgMuted }}>Áreas de ingestão monitoradas</div>
            </div>
            <Button variant="ghost" icon="chevR">Ver todas</Button>
          </div>
          {AREAS.map((a, i) => (
            <div key={a.nome} style={{ padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 12, borderBottom: i < AREAS.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
              <StatusDot status={a.estado} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12.5, fontWeight: 600, color: theme.fg }}>{a.nome}</div>
                <div style={{ marginTop: 2, fontFamily: 'var(--font-mono), monospace', fontSize: 10.5, color: theme.fgSubtle }}>{a.fonte} · {a.freq}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontFamily: 'var(--font-mono), monospace', fontSize: 12, color: theme.fg, fontWeight: 600 }}>{a.volume && c ? admFmtK(a.volume(c)) : '—'}</div>
                <div style={{ marginTop: 2 }}><Badge tone={ROTULO[a.estado].t}>{ROTULO[a.estado].l}</Badge></div>
              </div>
            </div>
          ))}
        </Card>

        <Card>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <SectionLabel>Métricas de produto</SectionLabel>
            <Badge tone="muted">aguardando</Badge>
          </div>
          <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[
              ['Usuários ativos (DAU)', 'analytics ainda não coletado'],
              ['Consultas ao Prometeus', 'o agente de IA ainda não foi ligado'],
              ['Posts publicados', 'pipeline editorial chega com a IA'],
              ['Engajamento do feed', 'camada social ainda não construída'],
            ].map(([k, v]) => (
              <div key={k} style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 10 }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: theme.fg }}>{k}</div>
                  <div style={{ marginTop: 2, fontSize: 11, color: theme.fgMuted }}>{v}</div>
                </div>
                <span style={{ fontFamily: 'var(--font-mono), monospace', fontSize: 15, fontWeight: 700, color: theme.fgSubtle }}>—</span>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 14, paddingTop: 12, borderTop: `1px solid ${theme.border}`, fontSize: 11.5, color: theme.fgSubtle, lineHeight: 1.5 }}>
            Sem número inventado: métricas de produto entram com analytics e o agente Prometeus.
          </div>
        </Card>
      </div>
    </>
  );
}
