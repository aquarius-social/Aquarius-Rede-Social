/**
 * Fundação de UI do app — porte FIEL de `aq-foundation.jsx` (Claude Design)
 * para React Native. Mesmas cores, raios, tipografia e componentes.
 */
import React from 'react';
import { View, Text, Pressable, StyleSheet, type ViewStyle, type TextStyle } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Svg, { Path, Circle, Polygon, Line, Rect, G, Text as SvgText, Defs, LinearGradient as SvgGrad, Stop } from 'react-native-svg';
import { cor, raio, fonte, gradienteAvatar, iniciais, shade } from '../lib/tema';
import { PARTIDO_COR } from '../lib/mock';

/* ── Ícones (subconjunto usado no perfil), 24×24, stroke 2 ─────────────── */
type IconName =
  | 'spark' | 'plus' | 'check' | 'doc' | 'chevR' | 'building' | 'star'
  | 'info' | 'back' | 'x' | 'compass' | 'search'
  | 'home' | 'heart' | 'cal' | 'users' | 'flag';

export function Icon({ name, size = 22, color = cor.navy, stroke = 2 }: {
  name: IconName; size?: number; color?: string; stroke?: number;
}) {
  const p = { stroke: color, strokeWidth: stroke, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, fill: 'none' as const };
  const svg = (children: React.ReactNode) => (
    <Svg width={size} height={size} viewBox="0 0 24 24">{children}</Svg>
  );
  switch (name) {
    case 'spark': return svg(<><Path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" {...p} /><Circle cx="12" cy="12" r="4" fill={color} /></>);
    case 'plus': return svg(<Path d="M12 5v14M5 12h14" {...p} />);
    case 'check': return svg(<Path d="M5 12l4 4 10-10" {...p} />);
    case 'doc': return svg(<><Path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" {...p} /><Path d="M14 3v6h6M8 14h8M8 18h5" {...p} /></>);
    case 'chevR': return svg(<Path d="M9 6l6 6-6 6" {...p} />);
    case 'building': return svg(<><Path d="M4 21V7l8-4 8 4v14" {...p} /><Path d="M9 21V11M15 21V11M4 21h16" {...p} /></>);
    case 'star': return svg(<Polygon points="12,3 14.5,9.5 21.5,10 16,14.6 17.8,21 12,17.4 6.2,21 8,14.6 2.5,10 9.5,9.5" {...p} />);
    case 'info': return svg(<><Circle cx="12" cy="12" r="9" {...p} /><Path d="M12 8v.01M11 12h1v5h1" {...p} /></>);
    case 'back': return svg(<Path d="M15 6l-6 6 6 6" {...p} />);
    case 'x': return svg(<Path d="M6 6l12 12M18 6L6 18" {...p} />);
    case 'compass': return svg(<><Circle cx="12" cy="12" r="9" {...p} /><Polygon points="16,8 13,13 8,16 11,11" fill={color} /></>);
    case 'search': return svg(<><Circle cx="11" cy="11" r="7" {...p} /><Path d="m20 20-4.3-4.3" {...p} /></>);
    case 'home': return svg(<Path d="M3 11l9-8 9 8M5 10v10h14V10M9 21v-6h6v6" {...p} />);
    case 'heart': return svg(<Path d="M12 21s-7-4.6-9.4-8.3C.9 10 2.4 5.5 6.2 5.5c2 0 3.2 1.3 3.8 2.3.6-1 1.8-2.3 3.8-2.3 3.8 0 5.3 4.5 3.6 7.2C19 16.4 12 21 12 21Z" {...p} />);
    case 'cal': return svg(<><Rect x="3" y="5" width="18" height="16" rx="2" {...p} /><Path d="M8 3v4M16 3v4M3 11h18" {...p} /></>);
    case 'users': return svg(<><Circle cx="9" cy="8" r="3.5" {...p} /><Path d="M3 21v-1a6 6 0 0 1 12 0v1M17 11a3 3 0 1 0 0-6M22 21v-1a6 6 0 0 0-5-5.9" {...p} /></>);
    case 'flag': return svg(<Path d="M4 21V4M4 4h13l-2 4 2 4H4" {...p} />);
    default: return null;
  }
}

/* ── Logo — porte FIEL de AqLogo (aq-foundation.jsx) ───────────────────────
 * Símbolo: cúpula Câmara + cúpula invertida Senado + 2 torres + "Onda Sky".
 * Wordmark: AQUARIUS em Inter ExtraBold, letterSpacing 0.04em, navy.        */
export function Logo({ height = 22, dark = false, mark = true, wordmark = true }: {
  height?: number; dark?: boolean; mark?: boolean; wordmark?: boolean;
}) {
  const tinta = dark ? cor.white : cor.navy;
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, height }}>
      {mark && (
        <Svg width={height * 1.15} height={height} viewBox="0 0 28 24">
          <Path d="M3 14 Q3 9 8 9 Q8 14 8 14 Z" fill={tinta} />
          <Path d="M16 9 Q21 9 21 14 L16 14 Z" fill={tinta} />
          <Rect x="11" y="2.5" width="2" height="11.5" rx="0.5" fill={tinta} />
          <Rect x="14.5" y="2.5" width="2" height="11.5" rx="0.5" fill={tinta} />
          <Path d="M2 19 Q7 16 12 19 T22 19 T26 19" stroke={cor.sky} strokeWidth="2" fill="none" strokeLinecap="round" />
        </Svg>
      )}
      {wordmark && (
        <Text style={{ fontFamily: fonte.xb, color: tinta, fontSize: height * 0.78, letterSpacing: height * 0.78 * 0.04, lineHeight: height }}>
          AQUARIUS
        </Text>
      )}
    </View>
  );
}

/* ── Avatar — gradiente determinístico navy/sky + iniciais ─────────────── */
export function Avatar({ nome, size = 40, ring = false }: { nome: string; size?: number; ring?: boolean }) {
  const [a, b] = gradienteAvatar(nome);
  return (
    <LinearGradient
      colors={[a, b]}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
      style={{
        width: size, height: size, borderRadius: size / 2,
        alignItems: 'center', justifyContent: 'center',
        ...(ring ? { borderWidth: 3.5, borderColor: cor.sky } : null),
      }}
    >
      <Text style={{ color: cor.white, fontFamily: fonte.b, fontSize: size * 0.36, letterSpacing: 0.4 }}>
        {iniciais(nome)}
      </Text>
    </LinearGradient>
  );
}

/* ── Monograma de partido/órgão (círculo colorido com sigla) ───────────── */
export function Monogram({ sigla, size = 72, color = cor.navy }: { sigla: string; size?: number; color?: string }) {
  const txt = sigla.length > 4 ? sigla.slice(0, 1) : sigla.slice(0, 4);
  return (
    <LinearGradient
      colors={[color, shade(color, -0.18)]}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
      style={{ width: size, height: size, borderRadius: size / 2, alignItems: 'center', justifyContent: 'center' }}
    >
      <Text style={{ color: cor.white, fontFamily: fonte.xb, fontSize: size * 0.34, letterSpacing: -0.3 }}>{txt}</Text>
    </LinearGradient>
  );
}

/* ── Banner cover com onda Sky (cor base opcional p/ partido) ──────────── */
export function Cover({ height = 88, base }: { height?: number; base?: string }) {
  const colors = base ? [base, shade(base, 0.18), cor.sky] : [cor.navy, cor.blue, cor.sky];
  return (
    <View style={{ height, position: 'relative' }}>
      <LinearGradient
        colors={colors as [string, string, string]}
        locations={[0, 0.7, 1]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={StyleSheet.absoluteFill}
      />
      <Svg width="100%" height={height} viewBox="0 0 400 88" preserveAspectRatio="none" style={StyleSheet.absoluteFill}>
        <Path d="M-10 64 Q60 40 130 64 T270 64 T410 64" stroke="rgba(255,255,255,0.4)" strokeWidth={2.5} fill="none" strokeLinecap="round" />
        <Path d="M-10 78 Q60 54 130 78 T270 78 T410 78" stroke="rgba(255,255,255,0.22)" strokeWidth={2.5} fill="none" strokeLinecap="round" />
      </Svg>
    </View>
  );
}

/* ── Party chip ────────────────────────────────────────────────────────── */
export function PartyChip({ sigla, uf }: { sigla: string | null; uf?: string | null }) {
  if (!sigla) return null;
  const dot = PARTIDO_COR[sigla] ?? cor.muted;
  return (
    <View style={s.partyChip}>
      <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: dot }} />
      <Text style={s.partyChipTxt}>{sigla}</Text>
      {uf ? <Text style={s.partyChipUf}>·{uf}</Text> : null}
    </View>
  );
}

/* ── Tag ───────────────────────────────────────────────────────────────── */
type Tone = 'muted' | 'navy' | 'sky' | 'pos' | 'neg' | 'warn' | 'gold';
const TONE: Record<Tone, { bg: string; fg: string }> = {
  muted: { bg: cor.light, fg: cor.muted },
  navy: { bg: cor.navy, fg: cor.white },
  sky: { bg: cor.sky, fg: cor.white },
  pos: { bg: 'rgba(30,142,92,0.12)', fg: cor.pos },
  neg: { bg: 'rgba(198,58,58,0.12)', fg: cor.neg },
  warn: { bg: 'rgba(217,123,46,0.13)', fg: cor.warn },
  gold: { bg: 'rgba(200,164,0,0.16)', fg: '#8C7300' },
};
export function Tag({ children, tone = 'muted' }: { children: React.ReactNode; tone?: Tone }) {
  const t = TONE[tone];
  return (
    <View style={[s.tag, { backgroundColor: t.bg }]}>
      <Text style={[s.tagTxt, { color: t.fg }]}>{children}</Text>
    </View>
  );
}

/* ── Selo de situação (licenciado / suplente em exercício) ─────────────── */
export function SituacaoBadge({ situacao }: { situacao: string | null | undefined }) {
  if (situacao === 'licenciado') return <Tag tone="warn">Licenciado</Tag>;
  if (situacao === 'suplente_em_exercicio') return <Tag tone="sky">Suplente em exercício</Tag>;
  return null; // em exercício (normal) → sem selo
}

/* ── Stat (célula da faixa de KPIs) ────────────────────────────────────── */
export function Stat({ value, label, sub, tone }: { value: React.ReactNode; label: string; sub?: string; tone?: 'pos' | 'neg' }) {
  return (
    <View style={{ flex: 1, minWidth: 0 }}>
      <Text style={s.statValue}>{value}</Text>
      <Text style={s.statLabel}>{label}</Text>
      {sub ? <Text style={[s.statSub, { color: tone === 'pos' ? cor.pos : tone === 'neg' ? cor.neg : cor.muted }]}>{sub}</Text> : null}
    </View>
  );
}

/* ── Card / SectionHeader / Divider / AlignmentBar ─────────────────────── */
export function Card({ children, padding = 14, style }: { children: React.ReactNode; padding?: number; style?: ViewStyle }) {
  return <View style={[s.card, { padding }, style]}>{children}</View>;
}
export function SectionHeader({ title, sub, action }: { title: string; sub?: string; action?: React.ReactNode }) {
  return (
    <View style={s.secHead}>
      <View>
        <Text style={s.secHeadTitle}>{title}</Text>
        {sub ? <Text style={s.secHeadSub}>{sub}</Text> : null}
      </View>
      {action}
    </View>
  );
}
export function Divider({ inset = 0 }: { inset?: number }) {
  return <View style={{ height: 1, backgroundColor: cor.border, marginLeft: inset }} />;
}
export function AlignmentBar({ pct, color = cor.sky, height = 8 }: { pct: number; color?: string; height?: number }) {
  return (
    <View style={{ backgroundColor: cor.light, borderRadius: 9999, height, overflow: 'hidden' }}>
      <View style={{ width: `${pct}%`, height: '100%', backgroundColor: color, borderRadius: 9999 }} />
    </View>
  );
}

/* ── Tratamentos de IA (pill / card / banner) ──────────────────────────── */
export function AIPill({ label, onPress }: { label: string; onPress?: () => void }) {
  return (
    <Pressable onPress={onPress} style={s.aiPill}>
      <Icon name="spark" size={14} color={cor.sky} />
      <Text style={s.aiPillTxt}>{label}</Text>
    </Pressable>
  );
}
export function AICard({ title, body, onAsk }: { title: string; body: string; onAsk?: () => void }) {
  return (
    <LinearGradient colors={[cor.light, cor.white]} start={{ x: 0, y: 0 }} end={{ x: 0, y: 1 }} style={s.aiCard}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 7, marginBottom: 8 }}>
        <View style={s.aiCardBadge}><Icon name="spark" size={13} color={cor.white} /></View>
        <Text style={s.aiCardTitle}>{title}</Text>
      </View>
      <Text style={s.aiCardBody}>{body}</Text>
      <View style={{ flexDirection: 'row', gap: 8, marginTop: 10 }}>
        <Pressable onPress={onAsk} style={s.aiCardBtnPrim}>
          <Icon name="spark" size={13} color={cor.white} />
          <Text style={s.aiCardBtnPrimTxt}>Perguntar</Text>
        </Pressable>
        <Pressable style={s.aiCardBtnGhost}><Text style={s.aiCardBtnGhostTxt}>Regenerar</Text></Pressable>
      </View>
    </LinearGradient>
  );
}
export function AIBanner({ hint, cta = 'Resumir', onPress }: { hint: string; cta?: string; onPress?: () => void }) {
  return (
    <Pressable onPress={onPress} style={s.aiBanner}>
      <View style={s.aiBannerIcon}><Icon name="spark" size={15} color={cor.white} /></View>
      <Text style={s.aiBannerHint}>{hint}</Text>
      <View style={s.aiBannerCta}><Text style={s.aiBannerCtaTxt}>{cta}</Text></View>
    </Pressable>
  );
}

/* ── Botão Seguir (toggle) ─────────────────────────────────────────────── */
export function FollowButton() {
  const [f, setF] = React.useState(false);
  return (
    <Pressable onPress={() => setF((v) => !v)} style={[s.cta, { flex: 1, backgroundColor: f ? cor.light : cor.navy, borderWidth: f ? 1 : 0, borderColor: cor.borderStrong }]}>
      <Icon name={f ? 'check' : 'plus'} size={15} color={f ? cor.navy : cor.white} stroke={2.4} />
      <Text style={[s.ctaTxt, { color: f ? cor.navy : cor.white }]}>{f ? 'Seguindo' : 'Seguir'}</Text>
    </Pressable>
  );
}

/* ── Bottom nav (shell) — 5 abas do protótipo, com IA central ──────────── */
type NavId = 'feed' | 'explorar' | 'interesses' | 'calendario';
export function BottomNav({ active = 'explorar' }: { active?: NavId }) {
  const cel = (id: NavId, icon: IconName, label: string) => {
    const sel = id === active;
    const cl = sel ? cor.navy : cor.mutedSoft;
    return (
      <View key={id} style={s.navCell}>
        <Icon name={icon} size={20} color={cl} />
        <Text style={[s.navCellTxt, { color: cl }]}>{label}</Text>
      </View>
    );
  };
  return (
    <View style={s.nav5}>
      {cel('feed', 'home', 'Feed')}
      {cel('explorar', 'compass', 'Explorar')}
      <View style={s.navCenter}><Icon name="spark" size={22} color={cor.white} /></View>
      {cel('interesses', 'heart', 'Interesses')}
      {cel('calendario', 'cal', 'Calendário')}
    </View>
  );
}

/* ── Charts (SVG) ──────────────────────────────────────────────────────── */
export function Donut({ data, w = 130, valueLabel, sub }: {
  data: { valor: number; cor: string }[]; w?: number; valueLabel: string; sub?: string;
}) {
  const total = data.reduce((s2, d) => s2 + d.valor, 0) || 1;
  const r = w / 2 - 14, cx = w / 2, cy = w / 2, strokeW = 22;
  const C = 2 * Math.PI * r;
  let acc = 0;
  return (
    <Svg width={w} height={w}>
      <Circle cx={cx} cy={cy} r={r} fill="none" stroke={cor.light} strokeWidth={strokeW} />
      {data.map((d, i) => {
        const dash = (d.valor / total) * C;
        const offset = (-acc / total) * C;
        acc += d.valor;
        return (
          <Circle key={i} cx={cx} cy={cy} r={r} fill="none" stroke={d.cor} strokeWidth={strokeW}
            strokeDasharray={`${dash} ${C - dash}`} strokeDashoffset={offset}
            transform={`rotate(-90 ${cx} ${cy})`} />
        );
      })}
      <SvgText x={cx} y={cy + 3} textAnchor="middle" fontFamily="Inter_800ExtraBold" fontSize="18" fill={cor.navy}>{valueLabel}</SvgText>
      {sub ? <SvgText x={cx} y={cy + 16} textAnchor="middle" fontFamily="Inter_600SemiBold" fontSize="9" fill={cor.muted}>{sub}</SvgText> : null}
    </Svg>
  );
}

export function LineChart({ data, labels, w = 320, h = 120, accent = cor.sky, min, max }: {
  data: number[]; labels?: string[]; w?: number; h?: number; accent?: string; min?: number; max?: number;
}) {
  const _min = min ?? Math.min(...data), _max = max ?? Math.max(...data);
  const pad = { l: 8, r: 8, t: 14, b: 18 };
  const iW = w - pad.l - pad.r, iH = h - pad.t - pad.b;
  const pts = data.map((v, i) => [pad.l + (i / (data.length - 1)) * iW, pad.t + (1 - (v - _min) / (_max - _min || 1)) * iH] as const);
  const d = pts.map((pt, i) => (i === 0 ? 'M' : 'L') + pt[0].toFixed(1) + ' ' + pt[1].toFixed(1)).join(' ');
  const dArea = d + ` L${pad.l + iW},${pad.t + iH} L${pad.l},${pad.t + iH} Z`;
  return (
    <Svg width={w} height={h}>
      <Defs>
        <SvgGrad id="lineFill" x1="0" x2="0" y1="0" y2="1">
          <Stop offset="0%" stopColor={accent} stopOpacity={0.22} />
          <Stop offset="100%" stopColor={accent} stopOpacity={0} />
        </SvgGrad>
      </Defs>
      {[0, 0.5, 1].map((g, i) => (
        <Line key={i} x1={pad.l} x2={w - pad.r} y1={pad.t + iH * g} y2={pad.t + iH * g} stroke={cor.border} strokeDasharray={g === 0 ? undefined : '2 3'} />
      ))}
      <Path d={dArea} fill="url(#lineFill)" />
      <Path d={d} fill="none" stroke={accent} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
      {pts.map((pt, i) => (i % 2 === 0 ? <Circle key={i} cx={pt[0]} cy={pt[1]} r={2.5} fill={accent} /> : null))}
      {labels?.map((l, i) => <SvgText key={'l' + i} x={pts[i][0]} y={h - 4} textAnchor="middle" fontSize="9" fill={cor.muted} fontFamily="Inter_600SemiBold">{l}</SvgText>)}
    </Svg>
  );
}

export function BarChart({ data, labels, w = 320, h = 120, accent = cor.navy, max }: {
  data: number[]; labels?: string[]; w?: number; h?: number; accent?: string; max?: number;
}) {
  const m = max ?? Math.max(...data);
  const pad = { l: 8, r: 8, t: 8, b: 18 };
  const iW = w - pad.l - pad.r, iH = h - pad.t - pad.b;
  const step = iW / data.length, bw = step * 0.62;
  return (
    <Svg width={w} height={h}>
      {[0, 0.5, 1].map((g, i) => (
        <Line key={i} x1={pad.l} x2={w - pad.r} y1={pad.t + iH * (1 - g)} y2={pad.t + iH * (1 - g)} stroke={cor.border} strokeDasharray={g === 0 ? undefined : '2 3'} />
      ))}
      {data.map((v, i) => {
        const x = pad.l + step * i + (step - bw) / 2;
        const bh = (v / m) * iH;
        return (
          <G key={i}>
            <Rect x={x} y={pad.t + iH - bh} width={bw} height={bh} rx={3} fill={accent} />
            {labels?.[i] ? <SvgText x={x + bw / 2} y={h - 4} textAnchor="middle" fontSize="9.5" fill={cor.muted} fontFamily="Inter_600SemiBold">{labels[i]}</SvgText> : null}
          </G>
        );
      })}
    </Svg>
  );
}

const s = StyleSheet.create({
  partyChip: { flexDirection: 'row', alignItems: 'center', gap: 5, paddingHorizontal: 7, paddingVertical: 3, borderRadius: 9999, backgroundColor: cor.white, borderWidth: 1, borderColor: cor.border },
  partyChipTxt: { fontSize: 10.5, fontFamily: fonte.sb, color: cor.navy, letterSpacing: 0.2 },
  partyChipUf: { fontSize: 10.5, fontFamily: fonte.m, color: cor.muted },
  tag: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 9999, alignSelf: 'flex-start' },
  tagTxt: { fontSize: 10.5, fontFamily: fonte.sb, letterSpacing: 0.5, textTransform: 'uppercase' },
  statValue: { fontFamily: fonte.xb, fontSize: 20, color: cor.navy, letterSpacing: -0.2 },
  statLabel: { marginTop: 4, fontFamily: fonte.b, fontSize: 9.5, color: cor.muted, letterSpacing: 1, textTransform: 'uppercase' },
  statSub: { marginTop: 3, fontSize: 10.5, fontFamily: fonte.sb },
  card: { backgroundColor: cor.white, borderRadius: raio.card, borderWidth: 1, borderColor: cor.border },
  secHead: { flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 10, paddingLeft: 2 },
  secHeadTitle: { fontFamily: fonte.b, fontSize: 11, color: cor.muted, letterSpacing: 1.4, textTransform: 'uppercase' },
  secHeadSub: { marginTop: 3, fontSize: 12, color: cor.muted },
  aiPill: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 7, paddingVertical: 10, paddingHorizontal: 14, borderRadius: 9999, borderWidth: 1, borderColor: cor.borderStrong, backgroundColor: cor.light },
  aiPillTxt: { fontFamily: fonte.sb, fontSize: 12.5, color: cor.navy },
  aiCard: { borderRadius: raio.card, padding: 14, borderWidth: 1, borderColor: cor.border },
  aiCardBadge: { width: 22, height: 22, borderRadius: 11, backgroundColor: cor.navy, alignItems: 'center', justifyContent: 'center' },
  aiCardTitle: { fontFamily: fonte.b, fontSize: 11, color: cor.navy, letterSpacing: 1.4, textTransform: 'uppercase' },
  aiCardBody: { fontSize: 13.5, lineHeight: 21, color: cor.ink },
  aiCardBtnPrim: { flex: 1, flexDirection: 'row', gap: 6, paddingVertical: 8, borderRadius: 9999, backgroundColor: cor.navy, alignItems: 'center', justifyContent: 'center' },
  aiCardBtnPrimTxt: { color: cor.white, fontFamily: fonte.sb, fontSize: 12 },
  aiCardBtnGhost: { paddingVertical: 8, paddingHorizontal: 12, borderRadius: 9999, borderWidth: 1, borderColor: cor.borderStrong },
  aiCardBtnGhostTxt: { color: cor.navy, fontFamily: fonte.sb, fontSize: 12 },
  aiBanner: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, borderRadius: raio.card, backgroundColor: cor.navy },
  aiBannerIcon: { width: 28, height: 28, borderRadius: 14, backgroundColor: 'rgba(255,255,255,0.14)', alignItems: 'center', justifyContent: 'center' },
  aiBannerHint: { flex: 1, color: cor.white, fontSize: 13, fontFamily: fonte.m, lineHeight: 17 },
  aiBannerCta: { paddingHorizontal: 11, paddingVertical: 5, borderRadius: 9999, backgroundColor: cor.sky },
  aiBannerCtaTxt: { color: cor.white, fontFamily: fonte.sb, fontSize: 11.5, letterSpacing: 0.4 },
  cta: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 7, paddingVertical: 12, borderRadius: 9999 },
  ctaTxt: { fontFamily: fonte.b, fontSize: 12.5 },
  nav5: { position: 'absolute', left: 0, right: 0, bottom: 0, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-around', backgroundColor: cor.white, borderTopWidth: 1, borderTopColor: cor.border, paddingTop: 8, paddingBottom: 20, paddingHorizontal: 4 },
  navCell: { flex: 1, alignItems: 'center', gap: 3 },
  navCellTxt: { fontSize: 10.5, fontFamily: fonte.sb },
  navCenter: { width: 52, height: 52, borderRadius: 26, backgroundColor: cor.navy, alignItems: 'center', justifyContent: 'center', marginTop: -18 },
});
