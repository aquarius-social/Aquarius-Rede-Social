'use client';
import { useEffect, useMemo, useState } from 'react';
import { useAdmTheme } from '../../lib/theme';
import { contagens, despesasTotal, type Contagens } from '../../lib/dados';
import { PIPES, type Pipe, type EstadoPipe as Estado } from '../../lib/pipelines';
import { Card, PageHeader, SectionLabel, Badge } from '../../components/ui';
import { StatusDot, Button, admFmtK } from '../../components/charts';
import { Icon, type IconName } from '../../components/Icon';

const ROTULO: Record<Estado, { tone: 'pos' | 'warn' | 'neg'; l: string }> = {
  ok: { tone: 'pos', l: 'OK' }, parcial: { tone: 'warn', l: 'WARN' }, fora: { tone: 'neg', l: 'FORA' },
};

export default function Pipelines() {
  const { theme } = useAdmTheme();
  const [c, setC] = useState<Contagens | null>(null);
  const [desp, setDesp] = useState<number>(0);
  const [aba, setAba] = useState<'todas' | 'ok' | 'parcial' | 'fora'>('todas');
  const [busca, setBusca] = useState('');
  const [sel, setSel] = useState<string>('despesas');

  useEffect(() => {
    contagens().then(setC).catch(() => {});
    despesasTotal().then(setDesp).catch(() => {});
  }, []);

  const okN = PIPES.filter((p) => p.estado === 'ok').length;
  const warnN = PIPES.filter((p) => p.estado === 'parcial').length;
  const foraN = PIPES.filter((p) => p.estado === 'fora').length;

  const lista = useMemo(() => PIPES.filter((p) => {
    if (aba !== 'todas' && p.estado !== aba) return false;
    if (busca && !p.nome.toLowerCase().includes(busca.toLowerCase())) return false;
    return true;
  }), [aba, busca]);

  const atual = PIPES.find((p) => p.id === sel) ?? PIPES[0];
  const regDe = (p: Pipe) => (c ? p.reg(c, desp) : null);

  return (
    <>
      <PageHeader
        title="Pipelines"
        subtitle={`Saúde da ingestão de dados · ${PIPES.length} pipelines · Câmara, Senado, Portal, IA`}
        actions={<>
          <Button variant="secondary" icon="sync">Recarregar</Button>
          <Button variant="primary" icon="sync">Sincronizar todas</Button>
        </>}
      />

      {/* Stat cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 14 }}>
        <Stat icon="pipe" cor={theme.sky} n={PIPES.length} label="Total" />
        <Stat icon="check" cor={theme.pos} n={okN} label="OK" />
        <Stat icon="alert" cor={theme.warn} n={warnN} label="Avisos" />
        <Stat icon="x" cor={theme.neg} n={foraN} label="Falhas" />
        <Stat icon="sync" cor={theme.fgMuted} n={0} label="Em curso" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.7fr 1fr', gap: 12, alignItems: 'start' }}>
        {/* Tabela */}
        <Card padding={0}>
          <div style={{ padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 12, borderBottom: `1px solid ${theme.border}`, flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', gap: 4, flex: 1 }}>
              {([['todas', 'Todas', PIPES.length], ['ok', 'OK', okN], ['parcial', 'Avisos', warnN], ['fora', 'Falhas', foraN]] as const).map(([id, l, n]) => (
                <button key={id} onClick={() => setAba(id)} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 10px', borderRadius: 8, border: 'none', cursor: 'pointer', background: aba === id ? theme.hover : 'transparent', color: aba === id ? theme.fg : theme.fgMuted, fontSize: 12.5, fontWeight: aba === id ? 700 : 500 }}>
                  {l}<span style={{ fontSize: 11, color: theme.fgSubtle }}>{n}</span>
                </button>
              ))}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px', borderRadius: 8, border: `1px solid ${theme.border}`, background: theme.bg, minWidth: 180 }}>
              <Icon name="search" size={14} color={theme.fgSubtle} />
              <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Filtrar…" style={{ flex: 1, border: 'none', outline: 'none', background: 'transparent', color: theme.fg, fontSize: 12.5 }} />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', padding: '9px 14px', fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: theme.fgSubtle, borderBottom: `1px solid ${theme.border}` }}>
            <span>Pipeline</span><span>Frequência</span><span style={{ textAlign: 'right' }}>Registros</span><span style={{ textAlign: 'right' }}>Estado</span>
          </div>

          {lista.map((p) => {
            const on = p.id === atual.id;
            const reg = regDe(p);
            return (
              <button key={p.id} onClick={() => setSel(p.id)} style={{ width: '100%', display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', alignItems: 'center', padding: '11px 14px', border: 'none', borderLeft: `2px solid ${on ? theme.sky : 'transparent'}`, borderBottom: `1px solid ${theme.border}`, background: on ? theme.hover : 'transparent', cursor: 'pointer', textAlign: 'left' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
                  <StatusDot status={p.estado} />
                  <span style={{ minWidth: 0 }}>
                    <span style={{ display: 'block', fontSize: 12.5, fontWeight: 600, color: theme.fg }}>{p.nome}</span>
                    <span style={{ display: 'block', marginTop: 2, fontFamily: 'var(--font-mono), monospace', fontSize: 10, color: theme.fgSubtle }}>{p.fonte}</span>
                  </span>
                </span>
                <span style={{ fontSize: 12, color: theme.fgMuted }}>{p.freq}</span>
                <span style={{ textAlign: 'right', fontFamily: 'var(--font-mono), monospace', fontSize: 12.5, fontWeight: 600, color: reg == null ? theme.fgSubtle : theme.fg }}>{reg == null ? '—' : admFmtK(reg)}</span>
                <span style={{ textAlign: 'right' }}><Badge tone={ROTULO[p.estado].tone}>{ROTULO[p.estado].l}</Badge></span>
              </button>
            );
          })}
        </Card>

        {/* Detalhe */}
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <StatusDot status={atual.estado} />
              <span style={{ fontSize: 15, fontWeight: 800, color: theme.fg }}>{atual.nome}</span>
            </div>
            <Badge tone={ROTULO[atual.estado].tone}>{ROTULO[atual.estado].l}</Badge>
          </div>
          <div style={{ fontFamily: 'var(--font-mono), monospace', fontSize: 11, color: theme.fgSubtle, marginBottom: 14 }}>{atual.fonte}</div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
            <Kv theme={theme} k="Registros na base" v={c ? (regDe(atual) == null ? '—' : admFmtK(regDe(atual)!)) : '…'} />
            <Kv theme={theme} k="Frequência" v={atual.freq} />
            <Kv theme={theme} k="Último run" v="—" />
            <Kv theme={theme} k="Tempo de execução" v="—" />
          </div>

          {atual.obs ? (
            <div style={{ padding: '10px 12px', borderRadius: 10, background: theme[atual.estado === 'fora' ? 'negSoft' : atual.estado === 'parcial' ? 'warnSoft' : 'infoSoft'], marginBottom: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                <Icon name="alert" size={13} color={atual.estado === 'fora' ? theme.neg : atual.estado === 'parcial' ? theme.warn : theme.info} />
                <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: atual.estado === 'fora' ? theme.neg : atual.estado === 'parcial' ? theme.warn : theme.info }}>Atenção</span>
              </div>
              <div style={{ fontSize: 12, color: theme.fg, lineHeight: 1.5 }}>{atual.obs}</div>
            </div>
          ) : null}

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <SectionLabel>Histórico · 30 dias</SectionLabel>
            <Badge tone="muted">telemetria em breve</Badge>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(15, 1fr)', gap: 4, marginBottom: 14 }}>
            {Array.from({ length: 30 }).map((_, i) => <div key={i} style={{ paddingTop: '100%', borderRadius: 3, background: theme.hover }} />)}
          </div>
          <div style={{ fontSize: 11, color: theme.fgSubtle, lineHeight: 1.5, marginBottom: 14 }}>
            Telemetria por execução (tempo, falhas, histórico) ainda não é coletada — entra com o agendador de ingestão.
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <Button variant="primary" icon="sync">Sync manual</Button>
            <Button variant="secondary" icon="pause">Pausar</Button>
          </div>
        </Card>
      </div>
    </>
  );
}

function Stat({ icon, cor, n, label }: { icon: IconName; cor: string; n: number; label: string }) {
  const { theme } = useAdmTheme();
  return (
    <Card padding={14}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ width: 34, height: 34, borderRadius: 9, background: `${cor}22`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icon name={icon} size={17} color={cor} />
        </div>
        <div>
          <div style={{ fontSize: 22, fontWeight: 800, color: theme.fg, lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>{n}</div>
          <div style={{ marginTop: 4, fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: theme.fgMuted }}>{label}</div>
        </div>
      </div>
    </Card>
  );
}

function Kv({ theme, k, v }: { theme: ReturnType<typeof useAdmTheme>['theme']; k: string; v: string }) {
  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: theme.fgSubtle }}>{k}</div>
      <div style={{ marginTop: 4, fontSize: 15, fontWeight: 700, color: theme.fg, fontVariantNumeric: 'tabular-nums' }}>{v}</div>
    </div>
  );
}
