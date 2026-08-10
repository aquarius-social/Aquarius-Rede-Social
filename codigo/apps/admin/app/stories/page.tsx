'use client';
import { useAdmTheme } from '../../lib/theme';
import { STORIES_KPIS, STORIES_PRODUCAO, STORIES_PUBLICADAS } from '../../lib/demo';
import { Card, PageHeader, SectionLabel, Badge, Selo } from '../../components/ui';
import { KpiCard, Button } from '../../components/charts';
import { Icon } from '../../components/Icon';

export default function Stories() {
  const { theme } = useAdmTheme();
  const acc = [theme.warn, theme.sky, theme.accent, theme.pos];

  return (
    <>
      <PageHeader
        title="Stories da IA"
        subtitle="Resumos diários do Prometeus · publicados no topo do feed, expiram em 24h"
        actions={<>
          <Button variant="secondary" icon="cal">Histórico</Button>
          <Button variant="primary" icon="spark">Gerar edição de hoje</Button>
        </>}
      />

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', borderRadius: 10, background: theme.warnSoft, marginBottom: 14 }}>
        <Icon name="alert" size={15} color={theme.warn} />
        <span style={{ fontSize: 12.5, color: theme.fg }}><b>Demonstração.</b> As stories são geradas pelo agente <b>Prometeus</b> (ainda não ligado); aberturas/conclusão dependem do analytics de produto.</span>
      </div>

      {/* KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 14 }}>
        {STORIES_KPIS.map((k, i) => (
          <KpiCard key={k.label} label={k.label} value={k.value} sub={k.sub} delta={k.delta} trend={k.trend} accent={acc[i]} icon={k.icon} selo="amostra" />
        ))}
      </div>

      {/* Em produção */}
      <Card padding={0} style={{ marginBottom: 14 }}>
        <div style={{ padding: '14px 16px', borderBottom: `1px solid ${theme.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <SectionLabel>Em produção · aguardando publicação</SectionLabel>
            <div style={{ marginTop: 3, fontSize: 11.5, color: theme.fgMuted }}>Revise cada card antes de liberar no feed</div>
          </div>
          <Badge tone="accent">{STORIES_PRODUCAO.length} em produção</Badge>
        </div>
        {STORIES_PRODUCAO.map((s, i) => (
          <div key={s.titulo} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 16px', borderBottom: i < STORIES_PRODUCAO.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
            <div style={{ width: 38, height: 38, borderRadius: 9, background: theme.accentSoft, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <Icon name={s.icon} size={17} color={theme.accent} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 14, fontWeight: 700, color: theme.fg }}>{s.titulo}</span>
                <Badge tone="muted">{s.tipo}</Badge>
              </div>
              <div style={{ marginTop: 3, fontSize: 11.5, color: theme.fgSubtle }}>{s.sub}</div>
            </div>
            {s.estado === 'revisar' ? (
              <div style={{ display: 'flex', gap: 8 }}>
                <Button variant="secondary" icon="eye">Revisar cards</Button>
                <Button variant="primary" icon="check">Publicar</Button>
              </div>
            ) : (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12.5, color: theme.sky, fontWeight: 600 }}>
                <span style={{ width: 8, height: 8, borderRadius: 9999, background: theme.sky }} />Gerando…
              </span>
            )}
          </div>
        ))}
      </Card>

      {/* Publicadas */}
      <Card padding={0}>
        <div style={{ display: 'grid', gridTemplateColumns: '2.2fr 0.9fr 1.6fr 0.7fr 0.8fr', padding: '11px 16px', fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: theme.fgSubtle, borderBottom: `1px solid ${theme.border}` }}>
          <span>Edição</span><span>Tipo</span><span>Aberturas · Conclusão</span><span style={{ textAlign: 'right' }}>Conf. IA</span><span style={{ textAlign: 'right' }}>Publicado</span>
        </div>
        {STORIES_PUBLICADAS.map((s, i) => (
          <div key={s.titulo} style={{ display: 'grid', gridTemplateColumns: '2.2fr 0.9fr 1.6fr 0.7fr 0.8fr', alignItems: 'center', padding: '13px 16px', borderBottom: i < STORIES_PUBLICADAS.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
              <Icon name="star" size={15} color={theme.warn} />
              <span style={{ fontSize: 13, fontWeight: 600, color: theme.fg, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.titulo}</span>
            </span>
            <span><Badge tone="muted">{s.tipo}</Badge></span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontFamily: 'var(--font-mono), monospace', fontSize: 12.5, fontWeight: 600, color: theme.fg, minWidth: 44 }}>{s.aberturas}</span>
              <span style={{ flex: 1, height: 5, borderRadius: 9999, background: theme.hover, overflow: 'hidden' }}><span style={{ display: 'block', width: `${s.conclusao}%`, height: '100%', background: theme.sky, borderRadius: 9999 }} /></span>
              <span style={{ fontFamily: 'var(--font-mono), monospace', fontSize: 11.5, color: theme.fgMuted }}>{s.conclusao}%</span>
            </span>
            <span style={{ textAlign: 'right', fontFamily: 'var(--font-mono), monospace', fontSize: 12.5, fontWeight: 700, color: theme.pos }}>{s.conf}%</span>
            <span style={{ textAlign: 'right', fontSize: 11, color: theme.fgSubtle }}>{s.quando}</span>
          </div>
        ))}
      </Card>
    </>
  );
}
