'use client';
import { useState } from 'react';
import { useAdmTheme } from '../../lib/theme';
import { Card, PageHeader, SectionLabel, Badge } from '../../components/ui';
import { KpiCard, Button } from '../../components/charts';
import { Icon } from '../../components/Icon';

// DEMONSTRAÇÃO — motor editorial. A fila real se enche quando o agente Prometeus
// gerar posts a partir dos atos oficiais (cada um revisado antes de publicar).
const POSTS = [
  { id: 'p7', tipo: 'Votação', fonte: 'Câmara', ha: '6min', conf: 74, headline: 'A Câmara aprovou em 1º turno a PEC 78/2024, que torna o FUNDEB permanente.', origem: 'PEC 78/2024 · 412 votos' },
  { id: 'p8', tipo: 'Projeto', fonte: 'Câmara', ha: '14min', conf: 69, headline: 'Tabata Amaral protocolou requerimento para convocar o Ministro da Educação.', origem: 'Requerimento · Comissão de Educação' },
  { id: 'p9', tipo: 'Discurso', fonte: 'Câmara', ha: '22min', conf: 58, headline: 'Em plenário, Erika Hilton defendeu a regulamentação do Pé-de-Meia.', origem: 'Grande Expediente · notas taquigráficas' },
];
const TABS = [['revisao', 'Em revisão', 3], ['agendados', 'Agendados', 1], ['publicados', 'Publicados', 5], ['rascunhos', 'Rascunhos', 1]] as const;

export default function FeedPosts() {
  const { theme } = useAdmTheme();
  const [tab, setTab] = useState<string>('revisao');
  const [sel, setSel] = useState('p7');
  const atual = POSTS.find((p) => p.id === sel) ?? POSTS[0];

  return (
    <>
      <PageHeader
        title="Feed & Posts"
        subtitle="Motor editorial · cada ato oficial vira um post em 3ª pessoa, revisado antes de publicar"
        actions={<>
          <Button variant="secondary" icon="sync">Atualizar fila</Button>
          <Button variant="primary" icon="send">Publicar revisados</Button>
        </>}
      />

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', borderRadius: 10, background: theme.warnSoft, marginBottom: 14 }}>
        <Icon name="alert" size={15} color={theme.warn} />
        <span style={{ fontSize: 12.5, color: theme.fg }}><b>Demonstração.</b> A fila de posts se enche quando o agente <b>Prometeus</b> converter os atos oficiais em posts. O conteúdo abaixo ilustra o fluxo.</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 14 }}>
        <KpiCard label="Posts publicados · hoje" value="284" sub="atos oficiais convertidos" delta={6.2} trend={[210, 228, 240, 255, 268, 276, 284]} accent={theme.sky} icon="list" />
        <KpiCard label="Em revisão" value="11" sub="aguardando aprovação humana" accent={theme.warn} icon="eye" />
        <KpiCard label="Alcance · 24h" value="1,3M" sub="impressões no feed" delta={9.4} trend={[0.8, 0.9, 1.0, 1.1, 1.2, 1.25, 1.3]} accent={theme.accent} icon="trend" />
        <KpiCard label="Taxa de engajamento" value="7.8%" sub="curtidas + comentários + shares" delta={0.6} accent={theme.pos} icon="spark" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 12, alignItems: 'start' }}>
        {/* Lista */}
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

          {tab === 'revisao' ? POSTS.map((p) => {
            const on = p.id === atual.id;
            const barCor = p.conf >= 70 ? theme.pos : theme.warn;
            return (
              <button key={p.id} onClick={() => setSel(p.id)} style={{ width: '100%', textAlign: 'left', padding: '14px 16px', border: 'none', borderLeft: `2px solid ${on ? theme.sky : 'transparent'}`, borderBottom: `1px solid ${theme.border}`, background: on ? theme.hover : 'transparent', cursor: 'pointer' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <Badge tone="accent">{p.tipo}</Badge>
                  <span style={{ fontFamily: 'var(--font-mono), monospace', fontSize: 10.5, color: theme.fgSubtle }}>{p.fonte}</span>
                  <div style={{ flex: 1 }} />
                  <span style={{ fontSize: 11, color: theme.fgSubtle }}>há {p.ha}</span>
                </div>
                <div style={{ fontSize: 13.5, fontWeight: 600, color: theme.fg, lineHeight: 1.4, marginBottom: 10 }}>{p.headline}</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 11, color: theme.fgMuted }}>Confiança IA</span>
                  <div style={{ width: 90, height: 6, borderRadius: 9999, background: theme.hover, overflow: 'hidden' }}>
                    <div style={{ width: `${p.conf}%`, height: '100%', background: barCor, borderRadius: 9999 }} />
                  </div>
                  <span style={{ fontFamily: 'var(--font-mono), monospace', fontSize: 11.5, fontWeight: 700, color: barCor }}>{p.conf}%</span>
                  <Badge tone="warn">Em revisão</Badge>
                </div>
              </button>
            );
          }) : (
            <div style={{ padding: '32px 16px', textAlign: 'center', fontSize: 12.5, color: theme.fgMuted }}>
              Sem itens de demonstração nesta aba. A fila real chega com o agente Prometeus.
            </div>
          )}
        </Card>

        {/* Preview */}
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
            <SectionLabel>Pré-visualização no feed</SectionLabel>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11, fontWeight: 700, color: theme.warn }}><span style={{ width: 6, height: 6, borderRadius: 9999, background: theme.warn }} />Em revisão</span>
          </div>

          <div style={{ border: `1px solid ${theme.border}`, borderRadius: 12, padding: 14, marginBottom: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
              <span style={{ width: 34, height: 34, borderRadius: 9999, background: 'linear-gradient(135deg,#0D2B5E,#2E7DD1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 11, fontWeight: 800 }}>{atual.id.toUpperCase()}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: theme.fg }}>Aquarius</div>
                <div style={{ fontSize: 11, color: theme.fgSubtle }}>{atual.fonte} · há {atual.ha}</div>
              </div>
              <Badge tone="accent">{atual.tipo}</Badge>
            </div>
            <div style={{ fontSize: 14, fontWeight: 600, color: theme.fg, lineHeight: 1.45, marginBottom: 12 }}>{atual.headline}</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '9px 12px', borderRadius: 9, background: theme.hover }}>
              <Icon name="doc" size={13} color={theme.fgMuted} />
              <span style={{ fontSize: 11.5, color: theme.fgMuted }}>Origem: {atual.origem}</span>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: theme.fgSubtle }}>Confiança IA</div>
              <div style={{ marginTop: 4, fontSize: 20, fontWeight: 800, color: atual.conf >= 70 ? theme.pos : theme.warn }}>{atual.conf}%</div>
            </div>
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: theme.fgSubtle }}>Fonte oficial</div>
              <div style={{ marginTop: 4, fontSize: 15, fontWeight: 700, color: theme.fg }}>{atual.fonte}</div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <Button variant="primary" icon="check">Aprovar e publicar</Button>
            <Button variant="secondary" icon="doc">Editar</Button>
            <button style={{ width: 36, height: 36, borderRadius: 8, border: `1px solid ${theme.borderStrong}`, background: 'transparent', color: theme.neg, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Icon name="trash" size={15} color={theme.neg} />
            </button>
          </div>
        </Card>
      </div>
    </>
  );
}
