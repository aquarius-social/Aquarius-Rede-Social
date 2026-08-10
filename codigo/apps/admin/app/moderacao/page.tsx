'use client';
import { useState } from 'react';
import { useAdmTheme } from '../../lib/theme';
import { Card, PageHeader, SectionLabel, Badge } from '../../components/ui';
import { KpiCard, Donut, Button } from '../../components/charts';
import { Icon } from '../../components/Icon';
import { DENUNCIAS, MOTIVOS, ACAO, Motivo, Sev } from '../../lib/demo/moderacao';

const TABS = [['pendentes', 'Pendentes', 4], ['removidos', 'Removidos', 2], ['mantidos', 'Mantidos', 1]] as const;

const MOT_TONE: Record<Motivo, 'warn' | 'neg' | 'muted'> = { desinformação: 'warn', assédio: 'neg', spam: 'muted', 'discurso de ódio': 'neg' };

export default function Moderacao() {
  const { theme } = useAdmTheme();
  const [tab, setTab] = useState('pendentes');
  const sevCor = (s: Sev) => (s === 'crítica' ? theme.neg : s === 'alta' ? theme.warn : theme.fgMuted);
  const donutCores = [theme.sky, theme.warn, theme.neg, theme.skySoft];

  return (
    <>
      <PageHeader
        title="Moderação"
        subtitle="Fila de denúncias de comentários e posts · triagem automática pela IA, decisão final humana"
        actions={<>
          <Button variant="secondary" icon="gear">Regras da comunidade</Button>
          <Button variant="primary" icon="shield">Revisar pendentes</Button>
        </>}
      />

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', borderRadius: 10, background: theme.warnSoft, marginBottom: 14 }}>
        <Icon name="alert" size={15} color={theme.warn} />
        <span style={{ fontSize: 12.5, color: theme.fg }}><b>Demonstração.</b> A fila de moderação depende da camada social (comentários, denúncias) e da auth de usuários — ainda não construídas.</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 14 }}>
        <KpiCard label="Denúncias pendentes" value="9" sub="aguardando decisão humana" accent={theme.warn} icon="alert" />
        <KpiCard label="Removidos · 24h" value="42" sub="conteúdos retirados do feed" delta={-4.2} accent={theme.neg} icon="trash" />
        <KpiCard label="Auto-moderação IA" value="86%" sub="resolvidos antes do humano" delta={3.1} accent={theme.accent} icon="spark" />
        <KpiCard label="Usuários suspensos" value="7" sub="ações ativas de moderação" accent={theme.sky} icon="lock" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.7fr 1fr', gap: 12, alignItems: 'start' }}>
        {/* Fila */}
        <Card padding={0}>
          <div style={{ padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 12, borderBottom: `1px solid ${theme.border}`, flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', gap: 4, flex: 1 }}>
              {TABS.map(([id, l, n]) => (
                <button key={id} onClick={() => setTab(id)} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 10px', borderRadius: 8, border: 'none', cursor: 'pointer', background: tab === id ? theme.hover : 'transparent', color: tab === id ? theme.fg : theme.fgMuted, fontSize: 12.5, fontWeight: tab === id ? 700 : 500 }}>
                  {l}<span style={{ fontSize: 11, color: theme.fgSubtle }}>{n}</span>
                </button>
              ))}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px', borderRadius: 8, border: `1px solid ${theme.border}`, background: theme.bg, minWidth: 160 }}>
              <Icon name="search" size={14} color={theme.fgSubtle} />
              <input placeholder="Filtrar…" style={{ flex: 1, border: 'none', outline: 'none', background: 'transparent', color: theme.fg, fontSize: 12.5 }} />
            </div>
          </div>

          {tab === 'pendentes' ? DENUNCIAS.map((d, i) => (
            <div key={i} style={{ padding: '14px 16px', borderBottom: i < DENUNCIAS.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
                <Badge tone="muted">{d.tipo}</Badge>
                <Badge tone={MOT_TONE[d.motivo]}>{d.motivo}</Badge>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 10.5, fontWeight: 700, color: sevCor(d.sev) }}><span style={{ width: 6, height: 6, borderRadius: 9999, background: sevCor(d.sev) }} />{d.sev}</span>
                <div style={{ flex: 1 }} />
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12, fontWeight: 700, color: theme.neg }}><Icon name="alert" size={12} color={theme.neg} />{d.flags}</span>
              </div>
              <div style={{ padding: '11px 14px', borderRadius: 9, background: theme.bg, border: `1px solid ${theme.border}`, fontSize: 13.5, fontStyle: 'italic', color: theme.fg, marginBottom: 10 }}>“{d.texto}”</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                <span style={{ width: 30, height: 30, borderRadius: 9999, background: theme.hover, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 800, color: theme.fgMuted }}>{d.autor.slice(0, 2).toUpperCase()}</span>
                <span style={{ fontSize: 12.5, color: theme.fg, fontWeight: 600 }}>{d.autor}</span>
                <span style={{ fontSize: 11.5, color: theme.fgSubtle }}>{d.ctx}</span>
                <div style={{ flex: 1 }} />
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11.5, color: theme.accent, fontWeight: 700 }}><Icon name="spark" size={12} color={theme.accent} />IA {d.ia}%</span>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 12px', borderRadius: 8, border: `1px solid ${theme.borderStrong}`, background: 'transparent', color: theme.neg, cursor: 'pointer', fontSize: 12, fontWeight: 600 }}><Icon name="trash" size={13} color={theme.neg} />Remover</button>
                <button style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 12px', borderRadius: 8, border: `1px solid ${theme.borderStrong}`, background: 'transparent', color: theme.fg, cursor: 'pointer', fontSize: 12, fontWeight: 600 }}><Icon name="check" size={13} color={theme.fg} />Manter</button>
                <button style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 12px', borderRadius: 8, border: 'none', background: 'transparent', color: theme.fgMuted, cursor: 'pointer', fontSize: 12, fontWeight: 600 }}><Icon name="lock" size={13} color={theme.fgMuted} />Suspender autor</button>
              </div>
            </div>
          )) : (
            <div style={{ padding: '32px 16px', textAlign: 'center', fontSize: 12.5, color: theme.fgMuted }}>Sem itens de demonstração nesta aba.</div>
          )}
        </Card>

        {/* Direita */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Card>
            <SectionLabel>Denúncias por motivo · 30d</SectionLabel>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 14 }}>
              <Donut data={MOTIVOS.map(([, v], i) => ({ value: v, color: donutCores[i] }))} w={120} />
              <div style={{ flex: 1 }}>
                {MOTIVOS.map(([l, v], i) => (
                  <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, fontSize: 12.5 }}>
                    <span style={{ width: 8, height: 8, borderRadius: 9999, background: donutCores[i] }} />
                    <span style={{ flex: 1, color: theme.fg }}>{l}</span>
                    <span style={{ fontWeight: 700, color: theme.fg }}>{v}%</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>

          <Card padding={0}>
            <div style={{ padding: '14px 16px', borderBottom: `1px solid ${theme.border}` }}><SectionLabel>Usuários sob ação</SectionLabel></div>
            {ACAO.map((u, i) => (
              <div key={u.nome} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', borderBottom: i < ACAO.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
                <span style={{ width: 32, height: 32, borderRadius: 9999, background: 'linear-gradient(135deg,#0D2B5E,#2E7DD1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 10, fontWeight: 800, flexShrink: 0 }}>{u.av}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: theme.fg }}>{u.nome}</div>
                  <div style={{ marginTop: 2, fontSize: 11, color: theme.fgSubtle }}>{u.motivo}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <Badge tone={u.tone}>{u.status}</Badge>
                  <div style={{ marginTop: 4, fontSize: 10.5, color: theme.fgSubtle }}>{u.n} denúncias</div>
                </div>
              </div>
            ))}
          </Card>
        </div>
      </div>
    </>
  );
}
