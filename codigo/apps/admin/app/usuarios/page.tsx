'use client';
import { useState } from 'react';
import { useAdmTheme } from '../../lib/theme';
import { Card, PageHeader, SectionLabel, Badge } from '../../components/ui';
import { KpiCard, Button } from '../../components/charts';
import { Icon, type IconName } from '../../components/Icon';
import { HORA, DIA, DURACAO, FUNIL, ADOCAO } from '../../lib/demo/usuarios';

type Aba = 'comportamento' | 'diretorio' | 'interesses' | 'daas';
const ABAS: { id: Aba; icon: IconName; label: string }[] = [
  { id: 'comportamento', icon: 'trend', label: 'Comportamento' },
  { id: 'diretorio', icon: 'users', label: 'Diretório' },
  { id: 'interesses', icon: 'spark', label: 'Interesses & Segmentos' },
  { id: 'daas', icon: 'globe', label: 'Data as a Service' },
];

const DIAS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];

export default function Usuarios() {
  const { theme } = useAdmTheme();
  const [aba, setAba] = useState<Aba>('comportamento');

  return (
    <>
      <PageHeader
        title="Usuários"
        subtitle="165.722 membros · comportamento, interesses e audiências de dados"
        actions={<>
          <Button variant="secondary" icon="download">Exportar agregado</Button>
          <Button variant="primary" icon="plus">Criar segmento</Button>
        </>}
      />

      {/* Abas */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 14, flexWrap: 'wrap' }}>
        {ABAS.map((a) => (
          <button key={a.id} onClick={() => setAba(a.id)} style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: '9px 14px', borderRadius: 9, border: `1px solid ${aba === a.id ? theme.borderStrong : 'transparent'}`, background: aba === a.id ? theme.surface : 'transparent', color: aba === a.id ? theme.fg : theme.fgMuted, cursor: 'pointer', fontSize: 13, fontWeight: aba === a.id ? 700 : 500 }}>
            <Icon name={a.icon} size={15} color={aba === a.id ? theme.sky : theme.fgMuted} />{a.label}
          </button>
        ))}
      </div>

      {/* Banner honesto */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', borderRadius: 10, background: theme.warnSoft, marginBottom: 14 }}>
        <Icon name="alert" size={15} color={theme.warn} />
        <span style={{ fontSize: 12.5, color: theme.fg }}>
          <b>Demonstração.</b> Métricas de uso são ilustrativas — o analytics de produto ainda não é coletado. Contagem real de contas depende da auth/role de admin (backlog).
        </span>
      </div>

      {aba !== 'comportamento' ? (
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '18px 4px' }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: theme.accentSoft, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Icon name={ABAS.find((a) => a.id === aba)!.icon} size={20} color={theme.accent} />
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: theme.fg }}>{ABAS.find((a) => a.id === aba)!.label} — em construção</div>
              <div style={{ marginTop: 3, fontSize: 12.5, color: theme.fgMuted, lineHeight: 1.5 }}>
                {aba === 'daas'
                  ? 'A vitrine de Data as a Service (audiências agregadas, k-anonimato) só faz sentido com base de usuários consentidos em escala.'
                  : 'Depende de ler contas reais (auth) e das preferências dos usuários — entra com a auth/role de admin.'}
              </div>
            </div>
          </div>
        </Card>
      ) : (
        <>
          {/* KPIs demo */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 14 }}>
            <KpiCard label="Membros ativos · 30d" value="165,7K" sub="base total da comunidade" delta={18.6} trend={[120, 128, 134, 141, 149, 156, 162, 166]} accent={theme.sky} icon="users" />
            <KpiCard label="Tempo no app · dia" value="19m 08s" sub="por membro ativo" delta={5.4} trend={[15, 16, 16, 17, 18, 18, 19]} accent={theme.accent} icon="trend" />
            <KpiCard label="Sessão média" value="6m 42s" sub="9.4 sessões/semana" delta={3.2} accent={theme.pos} icon="cal" />
            <KpiCard label="Stickiness · DAU/MAU" value="38%" sub="frequência de retorno" delta={1.6} accent={theme.warn} icon="spark" />
          </div>

          {/* Heatmap + Duração */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 12, marginBottom: 14, alignItems: 'start' }}>
            <Card>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                <SectionLabel>Quando a comunidade usa o app · 7 dias × 24h</SectionLabel>
                <Badge tone="accent">pico 18h–20h</Badge>
              </div>
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
            </Card>

            <Card>
              <SectionLabel>Duração das sessões</SectionLabel>
              <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 12 }}>
                {DURACAO.map(([l, p]) => <BarRow key={l} label={l} pct={p} theme={theme} />)}
              </div>
              <div style={{ marginTop: 14, paddingTop: 12, borderTop: `1px solid ${theme.border}`, fontSize: 11.5, color: theme.fgSubtle, lineHeight: 1.5 }}>
                48% das sessões duram entre 6 e 20 minutos — leitura de feed + stories.
              </div>
            </Card>
          </div>

          {/* Funil + Adoção */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 12, alignItems: 'start' }}>
            <Card>
              <SectionLabel>Ritual diário · funil de uma sessão típica</SectionLabel>
              <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
                {FUNIL.map(([l, v, p]) => (
                  <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span style={{ width: 150, fontSize: 12.5, color: theme.fg }}>{l}</span>
                    <div style={{ flex: 1, height: 26, borderRadius: 7, background: theme.hover, overflow: 'hidden', position: 'relative' }}>
                      <div style={{ width: `${p}%`, height: '100%', background: `linear-gradient(90deg, ${theme.sky}, ${theme.skySoft})`, borderRadius: 7, display: 'flex', alignItems: 'center', paddingLeft: 10 }}>
                        <span style={{ fontFamily: 'var(--font-mono), monospace', fontSize: 11.5, fontWeight: 700, color: '#fff' }}>{v}</span>
                      </div>
                    </div>
                    <span style={{ width: 48, textAlign: 'right', fontFamily: 'var(--font-mono), monospace', fontSize: 12, color: theme.fgMuted }}>{p}%</span>
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <SectionLabel>Adoção de funcionalidades · 30d</SectionLabel>
              <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 16 }}>
                {ADOCAO.map(([l, ic, p]) => (
                  <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ width: 30, height: 30, borderRadius: 8, background: theme.hover, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                      <Icon name={ic as IconName} size={15} color={theme.fg} />
                    </div>
                    <span style={{ width: 96, fontSize: 13, fontWeight: 600, color: theme.fg }}>{l}</span>
                    <div style={{ flex: 1, height: 8, borderRadius: 9999, background: theme.hover, overflow: 'hidden' }}>
                      <div style={{ width: `${p}%`, height: '100%', background: theme.sky, borderRadius: 9999 }} />
                    </div>
                    <span style={{ width: 40, textAlign: 'right', fontFamily: 'var(--font-mono), monospace', fontSize: 12, color: theme.fgMuted }}>{p}%</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </>
      )}
    </>
  );
}

function BarRow({ label, pct, theme }: { label: string; pct: number; theme: ReturnType<typeof useAdmTheme>['theme'] }) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
        <span style={{ fontSize: 12.5, fontWeight: 600, color: theme.fg }}>{label}</span>
        <span style={{ fontFamily: 'var(--font-mono), monospace', fontSize: 12, color: theme.fgMuted }}>{pct}%</span>
      </div>
      <div style={{ height: 8, borderRadius: 9999, background: theme.hover, overflow: 'hidden' }}>
        <div style={{ width: `${pct * 3.4}%`, maxWidth: '100%', height: '100%', background: theme.sky, borderRadius: 9999 }} />
      </div>
    </div>
  );
}
