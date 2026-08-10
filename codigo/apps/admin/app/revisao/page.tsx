'use client';
import { useState } from 'react';
import { useAdmTheme } from '../../lib/theme';
import { Card, PageHeader, SectionLabel, Badge } from '../../components/ui';
import { KpiCard, Button } from '../../components/charts';
import { Icon } from '../../components/Icon';
import { FILA, CORRECOES } from '../../lib/demo/revisao';

export default function Revisao() {
  const { theme } = useAdmTheme();
  const [sel, setSel] = useState('v1');
  const atual = FILA.find((f) => f.id === sel) ?? FILA[0];

  return (
    <>
      <PageHeader
        title="Revisão editorial"
        subtitle="Cada post gerado por IA é conferido contra a fonte oficial antes de ir ao ar — e corrigido se algo escapar"
        actions={<>
          <Button variant="secondary" icon="gear">Regras editoriais</Button>
          <Button variant="primary" icon="check">Aprovar revisados</Button>
        </>}
      />

      {/* Banner honesto */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', borderRadius: 10, background: theme.warnSoft, marginBottom: 14 }}>
        <Icon name="alert" size={15} color={theme.warn} />
        <span style={{ fontSize: 12.5, color: theme.fg }}>
          <b>Demonstração.</b> A fila de revisão se enche quando o agente <b>Prometeus</b> for ligado. O conteúdo abaixo ilustra o fluxo gerado-vs-fonte — não são posts reais.
        </span>
      </div>

      {/* KPIs (demo) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 14 }}>
        <KpiCard label="Na fila de revisão" value="11" sub="SLA 30 min por item" accent={theme.sky} icon="eye" />
        <KpiCard label="Tempo médio de revisão" value="7 min" sub="caindo com o tempo" delta={-18.2} trend={[14, 12, 11, 10, 9, 8, 8, 7]} accent={theme.warn} icon="trend" />
        <KpiCard label="Auto-aprovável" value="62%" sub="confiança IA ≥ 0,90" delta={4.1} trend={[54, 56, 57, 59, 60, 61, 62]} accent={theme.accent} icon="spark" />
        <KpiCard label="Escalados ao chefe" value="2" sub="casos sensíveis" accent={theme.neg} icon="alert" />
      </div>

      {/* Fila + Conferência */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: 12, marginBottom: 14, alignItems: 'start' }}>
        <Card padding={0}>
          <div style={{ padding: '14px 16px', borderBottom: `1px solid ${theme.border}` }}>
            <SectionLabel>Fila · aguardando revisão</SectionLabel>
          </div>
          <div style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 10 }}>
            {FILA.map((f) => {
              const on = f.id === atual.id;
              const barCor = f.conf >= 70 ? theme.pos : theme.warn;
              return (
                <button key={f.id} onClick={() => setSel(f.id)} style={{ textAlign: 'left', padding: 12, borderRadius: 12, border: `1px solid ${on ? theme.sky : theme.border}`, background: on ? theme.hover : 'transparent', cursor: 'pointer' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <Badge tone="muted">{f.tipo}</Badge>
                    {f.baixa ? <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 10.5, fontWeight: 700, color: theme.warn }}><span style={{ width: 6, height: 6, borderRadius: 9999, background: theme.warn }} />baixa conf.</span> : null}
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: theme.fg, lineHeight: 1.4, marginBottom: 10 }}>{f.headline}</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ flex: 1, height: 6, borderRadius: 9999, background: theme.hover, overflow: 'hidden' }}>
                      <div style={{ width: `${f.conf}%`, height: '100%', background: barCor, borderRadius: 9999 }} />
                    </div>
                    <span style={{ fontFamily: 'var(--font-mono), monospace', fontSize: 11.5, fontWeight: 700, color: barCor }}>{f.conf}%</span>
                  </div>
                </button>
              );
            })}
          </div>
        </Card>

        <Card>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
            <SectionLabel>Conferência · texto gerado vs. fonte oficial</SectionLabel>
            <span style={{ fontSize: 11, color: theme.fgSubtle }}>gerado há {atual.geradoHa}</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 16 }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                <Icon name="spark" size={14} color={theme.accent} />
                <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', color: theme.accent }}>GERADO PELA IA</span>
              </div>
              <div style={{ fontSize: 13.5, color: theme.fg, lineHeight: 1.55 }}>{atual.ia}</div>
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                <Icon name="doc" size={14} color={theme.pos} />
                <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', color: theme.pos }}>FONTE OFICIAL</span>
              </div>
              <div style={{ fontFamily: 'var(--font-mono), monospace', fontSize: 12, color: theme.fgMuted, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{atual.fonte}</div>
              <div style={{ marginTop: 8, fontSize: 11, color: theme.fgSubtle }}>{atual.fonteRef}</div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <Button variant="primary" icon="check">Aprovar e publicar</Button>
            <Button variant="secondary" icon="doc">Editar texto</Button>
            <Button variant="secondary" icon="alert">Escalar ao chefe</Button>
            <div style={{ flex: 1 }} />
            <button style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 12px', borderRadius: 8, border: `1px solid ${theme.borderStrong}`, background: 'transparent', color: theme.neg, cursor: 'pointer', fontSize: 12.5, fontWeight: 600 }}>
              <Icon name="x" size={14} color={theme.neg} />Rejeitar
            </button>
          </div>
        </Card>
      </div>

      {/* Correções & retratações */}
      <Card padding={0}>
        <div style={{ padding: '14px 16px', borderBottom: `1px solid ${theme.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <SectionLabel>Correções & retratações · publicados</SectionLabel>
            <div style={{ marginTop: 3, fontSize: 11.5, color: theme.fgMuted }}>Quando um erro escapa: corrige com nota, ou retrata e notifica quem interagiu.</div>
          </div>
          <Button variant="secondary" icon="alert">Abrir correção</Button>
        </div>
        {CORRECOES.map((c, i) => (
          <div key={c.titulo} style={{ display: 'flex', gap: 12, padding: '14px 16px', borderBottom: i < CORRECOES.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
            <div style={{ width: 30, height: 30, borderRadius: 8, background: c.tone === 'pos' ? theme.posSoft : theme.negSoft, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <Icon name={c.icon} size={15} color={c.tone === 'pos' ? theme.pos : theme.neg} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 13.5, fontWeight: 700, color: theme.fg }}>{c.titulo}</span>
                <Badge tone="muted">{c.tipo}</Badge>
                <Badge tone={c.statusTone}>{c.status}</Badge>
              </div>
              <div style={{ fontSize: 12, color: theme.fg, lineHeight: 1.5 }}><b>Origem:</b> {c.origem}</div>
              <div style={{ marginTop: 2, fontSize: 12, color: theme.fgMuted, lineHeight: 1.5 }}><b style={{ color: theme.fg }}>Ação:</b> {c.acao}</div>
            </div>
            <div style={{ textAlign: 'right', flexShrink: 0, fontSize: 11 }}>
              <div style={{ fontWeight: 700, color: theme.fg }}>{c.autor}</div>
              <div style={{ marginTop: 2, color: theme.fgSubtle }}>{c.quando}</div>
            </div>
          </div>
        ))}
      </Card>
    </>
  );
}
