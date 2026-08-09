'use client';
import { useEffect, useState } from 'react';
import { useAdmTheme } from '../lib/theme';
import { contagens, ultimoSync, type Contagens } from '../lib/dados';
import { Card, PageHeader, KpiCard, SectionLabel, Badge } from '../components/ui';
import { Icon } from '../components/Icon';

const fmt = (n: number) => n.toLocaleString('pt-BR');
const dataBR = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString('pt-BR') : '—');

// Áreas de ingestão e o que está REALMENTE no ar (honesto — ver MELHORIAS.md).
const AREAS: { nome: string; fonte: string; estado: 'ok' | 'parcial' | 'fora' }[] = [
  { nome: 'Despesas Câmara (CEAP)', fonte: 'Portal da Transparência', estado: 'ok' },
  { nome: 'Despesas Senado (CEAPS)', fonte: 'Senado', estado: 'parcial' },
  { nome: 'Emendas parlamentares', fonte: 'Portal da Transparência', estado: 'ok' },
  { nome: 'Agenda / eventos', fonte: 'Câmara + Senado', estado: 'ok' },
  { nome: 'Proposições', fonte: 'Câmara + Senado', estado: 'fora' },
  { nome: 'Votações nominais', fonte: 'Câmara + Senado', estado: 'fora' },
  { nome: 'Discursos', fonte: 'Câmara + Senado', estado: 'fora' },
  { nome: 'Presença', fonte: '(sem coletor ainda)', estado: 'fora' },
];

const ESTADO = {
  ok: { tone: 'pos' as const, txt: 'No ar' },
  parcial: { tone: 'warn' as const, txt: 'Parcial' },
  fora: { tone: 'neg' as const, txt: 'Fora (⛔Pro)' },
};

export default function Overview() {
  const { theme } = useAdmTheme();
  const [c, setC] = useState<Contagens | null>(null);
  const [sync, setSync] = useState<string | null>(null);

  useEffect(() => {
    contagens().then(setC).catch(() => {});
    ultimoSync().then(setSync).catch(() => {});
  }, []);

  return (
    <>
      <PageHeader
        title="Visão geral"
        subtitle={`Base de dados cívica · dinheiro sincronizado em ${dataBR(sync)}`}
      />

      {/* KPIs reais */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 12 }}>
        <KpiCard label="Parlamentares" value={c ? fmt(c.parlamentares) : '…'} sub="em exercício (2 casas)" accent={theme.sky} />
        <KpiCard label="Partidos" value={c ? fmt(c.partidos) : '…'} sub="com bancada" accent={theme.blue} />
        <KpiCard label="Emendas" value={c ? fmt(c.emendas) : '…'} sub="registros na base" accent={theme.warn} />
        <KpiCard label="Eventos na agenda" value={c ? fmt(c.eventos) : '…'} sub="Câmara + Senado" accent={theme.pos} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 18 }}>
        <KpiCard label="Comissões" value={c ? fmt(c.comissoes) : '…'} accent={theme.accent} />
        <KpiCard label="Frentes" value={c ? fmt(c.frentes) : '…'} accent={theme.accent} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: 12 }}>
        {/* Estado da ingestão */}
        <Card padding={0}>
          <div style={{ padding: '14px 16px', borderBottom: `1px solid ${theme.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <SectionLabel>Áreas de dados · o que está no ar</SectionLabel>
            <Badge tone="muted">honesto</Badge>
          </div>
          {AREAS.map((a, i) => (
            <div key={a.nome} style={{ padding: '11px 16px', display: 'flex', alignItems: 'center', gap: 12, borderBottom: i < AREAS.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: theme.fg }}>{a.nome}</div>
                <div style={{ marginTop: 2, fontSize: 11, color: theme.fgSubtle, fontFamily: 'var(--font-mono), monospace' }}>{a.fonte}</div>
              </div>
              <Badge tone={ESTADO[a.estado].tone}>{ESTADO[a.estado].txt}</Badge>
            </div>
          ))}
        </Card>

        {/* Métricas de uso — honestas */}
        <Card>
          <SectionLabel>Métricas de uso</SectionLabel>
          <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[
              ['Usuários ativos (DAU)', 'analytics ainda não coletado'],
              ['Consultas ao Prometeus', 'o agente de IA ainda não foi ligado'],
              ['Posts publicados', 'pipeline editorial chega com a IA'],
              ['Engajamento do feed', 'camada social ainda não construída'],
            ].map(([k, v]) => (
              <div key={k} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                <Icon name="x" size={15} color={theme.fgSubtle} style={{ marginTop: 2, flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: theme.fg }}>{k}</div>
                  <div style={{ marginTop: 2, fontSize: 11.5, color: theme.fgMuted }}>{v}</div>
                </div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 14, paddingTop: 12, borderTop: `1px solid ${theme.border}`, fontSize: 11.5, color: theme.fgSubtle, lineHeight: 1.5 }}>
            Nada de número inventado: só mostramos o que a base afirma com fonte. As métricas de produto
            entram quando houver analytics e o agente Prometeus.
          </div>
        </Card>
      </div>
    </>
  );
}
