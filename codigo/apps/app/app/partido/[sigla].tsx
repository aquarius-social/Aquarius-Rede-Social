import { useEffect, useState, useMemo } from 'react';
import { View, Text, ScrollView, ActivityIndicator, Pressable, StyleSheet } from 'react-native';
import { useLocalSearchParams, Link } from 'expo-router';
import {
  obterPartido, membrosDoPartido, resumoEmendasPartido,
  type Partido, type Parlamentar, type ResumoEmendasPartido,
} from '../../lib/dados';
import { reais, kbr, frescor } from '../../lib/formato';
import { cor, raio, fonte } from '../../lib/tema';
import {
  Cover, Monogram, Avatar, PartyChip, Tag, SituacaoBadge, Stat, Card, SectionHeader, Divider,
  AlignmentBar, AIPill, AICard, BottomNav, Icon,
} from '../../components/base';
import {
  PARTIDO_KPI_PLACEHOLDER, PARTIDO_COESAO, PARTIDO_LIDERANCAS, PROPOSICOES,
  PARTIDO_COR,
} from '../../lib/mock';

const TABS = [
  { id: 'membros', label: 'Membros' }, { id: 'liderancas', label: 'Lideranças' },
  { id: 'proposicoes', label: 'Proposições' }, { id: 'emendas', label: 'Emendas' },
] as const;
type TabId = (typeof TABS)[number]['id'];
const PALETA = ['#0D2B5E', '#1A4FA0', '#2E7DD1', '#5FA0E0', '#7AB1E6', '#A0C9EF', '#C7DDF4'];

export default function PartidoScreen() {
  const { sigla } = useLocalSearchParams<{ sigla: string }>();
  const [pt, setPt] = useState<Partido | null>(null);
  const [membros, setMembros] = useState<Parlamentar[]>([]);
  const [emd, setEmd] = useState<ResumoEmendasPartido | null>(null);
  const [tab, setTab] = useState<TabId>('membros');
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!sigla) return;
    let vivo = true;
    (async () => {
      try {
        const [p, ms] = await Promise.all([obterPartido(sigla), membrosDoPartido(sigla)]);
        if (!vivo) return;
        setPt(p); setMembros(ms);
        const ee = await resumoEmendasPartido(ms.map((m) => m.id));
        if (!vivo) return;
        setEmd(ee);
      } catch (e: any) { if (vivo) setErro(e?.message ?? 'Falha ao carregar'); }
      finally { if (vivo) setCarregando(false); }
    })();
    return () => { vivo = false; };
  }, [sigla]);

  const corPt = PARTIDO_COR[sigla ?? ''] ?? cor.navy;
  const camara = membros.filter((m) => m.casa_atual === 'camara').length;
  const senado = membros.filter((m) => m.casa_atual === 'senado').length;
  const ufs = useMemo(() => [...new Set(membros.map((m) => m.uf_atual).filter(Boolean))] as string[], [membros]);

  if (carregando) return <View style={st.centro}><ActivityIndicator color={cor.blue} /></View>;
  if (erro || !pt) return <View style={st.centro}><Text style={st.erro}>{erro ?? 'Partido não encontrado.'}</Text></View>;

  return (
    <View style={{ flex: 1, backgroundColor: cor.surface }}>
      <ScrollView contentContainerStyle={{ paddingBottom: 96 }}>
        {/* Header */}
        <View style={{ backgroundColor: cor.white }}>
          <Cover height={88} base={corPt} />
          <View style={{ paddingHorizontal: 16, paddingBottom: 16, marginTop: -30 }}>
            <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 14 }}>
              <View style={st.monoRing}><Monogram sigla={pt.sigla_atual} size={72} color={corPt} /></View>
              <View style={{ flex: 1, paddingBottom: 6 }}>
                {pt.numero_urna ? <Tag tone="navy">{`Nº ${pt.numero_urna}`}</Tag> : null}
              </View>
            </View>
            <Text style={st.nome}>
              {pt.sigla_atual} <Text style={st.nomeSub}>· {pt.nome_atual}</Text>
            </Text>
            <Text style={st.sub}>{membros.length} parlamentares · {ufs.length} UFs</Text>

            <View style={st.stats}>
              <Stat value={membros.length} label="Bancada" />
              <View style={st.statDiv} />
              <Stat value={`${PARTIDO_KPI_PLACEHOLDER.coesao}%`} label="Coesão" />
              <View style={st.statDiv} />
              <Stat value={kbr(emd?.totalPago ?? 0)} label="Emendas pagas" tone="pos" />
            </View>

            <Pressable style={[st.cta, { backgroundColor: cor.navy }]}>
              <Icon name="spark" size={16} color={cor.white} />
              <Text style={st.ctaTxt}>Perguntar ao Prometeus sobre o {pt.sigla_atual}</Text>
            </Pressable>
          </View>
        </View>

        {/* Abas */}
        <View style={st.tabsWrap}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: 8, paddingVertical: 6 }}>
            {TABS.map((t) => {
              const sel = t.id === tab;
              return (
                <Pressable key={t.id} onPress={() => setTab(t.id)} style={st.tab}>
                  <Text style={[st.tabTxt, { color: sel ? cor.navy : cor.muted, fontFamily: sel ? fonte.b : fonte.sb }]}>{t.label}</Text>
                  {sel ? <View style={st.tabUnderline} /> : null}
                </Pressable>
              );
            })}
          </ScrollView>
        </View>

        {tab === 'membros' && <TabMembros membros={membros} camara={camara} senado={senado} ufs={ufs} />}
        {tab === 'liderancas' && <TabLiderancas sigla={pt.sigla_atual} />}
        {tab === 'proposicoes' && <TabProposicoes />}
        {tab === 'emendas' && <TabEmendas emd={emd} />}
      </ScrollView>
      <BottomNav active="explorar" />
    </View>
  );
}

function Fonte({ texto }: { texto: string }) { return <Text style={st.fonte}>{texto}</Text>; }

/* ── MEMBROS (REAL) ── */
function TabMembros({ membros, camara, senado, ufs }: { membros: Parlamentar[]; camara: number; senado: number; ufs: string[] }) {
  const [uf, setUf] = useState<string | null>(null);
  const lista = uf ? membros.filter((m) => m.uf_atual === uf) : membros;
  return (
    <View style={{ padding: 14 }}>
      <View style={{ flexDirection: 'row', gap: 8, marginBottom: 12 }}>
        <Card padding={12} style={{ flex: 1 }}><Text style={st.kpiVal}>{camara}</Text><Text style={st.kpiLbl}>Câmara</Text></Card>
        <Card padding={12} style={{ flex: 1 }}><Text style={st.kpiVal}>{senado}</Text><Text style={st.kpiLbl}>Senado</Text></Card>
        <Card padding={12} style={{ flex: 1 }}><Text style={st.kpiVal}>{PARTIDO_KPI_PLACEHOLDER.presenca}%</Text><Text style={st.kpiLbl}>Presença*</Text></Card>
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 12 }}>
        {[null, ...ufs].map((u) => {
          const sel = u === uf;
          return (
            <Pressable key={u ?? 'todas'} onPress={() => setUf(u)} style={[st.filtro, { backgroundColor: sel ? cor.navy : cor.white, borderColor: sel ? cor.navy : cor.border }]}>
              <Text style={{ color: sel ? cor.white : cor.navy, fontFamily: fonte.sb, fontSize: 11.5 }}>{u ?? 'Todas UFs'}</Text>
            </Pressable>
          );
        })}
      </ScrollView>
      <Card padding={0}>
        {lista.map((m, i) => (
          <View key={m.id}>
            <Link href={{ pathname: '/parlamentar/[id]', params: { id: m.id } }} asChild>
              <Pressable style={{ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 11 }}>
                <Avatar nome={m.nome} size={40} />
                <View style={{ flex: 1, gap: 4 }}>
                  <Text style={{ fontSize: 13.5, fontFamily: fonte.b, color: cor.navy }}>{m.nome}</Text>
                  <View style={{ flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: 6 }}>
                    <PartyChip sigla={m.partido_sigla_atual} uf={m.uf_atual} />
                    <Text style={{ fontSize: 10.5, color: cor.mutedSoft }}>{m.casa_atual === 'senado' ? 'Senado' : 'Câmara'}</Text>
                    <SituacaoBadge situacao={m.situacao} />
                  </View>
                </View>
                <Icon name="chevR" size={15} color={cor.mutedSoft} />
              </Pressable>
            </Link>
            {i < lista.length - 1 ? <Divider inset={64} /> : null}
          </View>
        ))}
        {lista.length === 0 ? <Text style={[st.vazio, { padding: 14 }]}>Nenhum membro nesta UF.</Text> : null}
      </Card>
      <Fonte texto="* Presença é placeholder — área ainda não ingerida. Bancada e UFs são dado real." />
    </View>
  );
}

/* ── LIDERANÇAS (placeholder) ── */
function TabLiderancas({ sigla }: { sigla: string }) {
  return (
    <View style={{ padding: 14 }}>
      <AICard title="Estrutura de comando" body={`O ${sigla} tem presidência, líderes na Câmara e no Senado, vice-líderes e secretaria-geral, com coesão de voto medida nas votações nominais.`} />
      <View style={{ height: 14 }} />
      <SectionHeader title="Direção" />
      <Card padding={0}>
        {PARTIDO_LIDERANCAS.map((l, i) => (
          <View key={l.cargo}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12 }}>
              <Avatar nome={l.nome} size={40} />
              <View style={{ flex: 1 }}>
                <Text style={{ fontSize: 13.5, fontFamily: fonte.b, color: cor.navy }}>{l.nome}</Text>
                <Text style={{ fontSize: 11, color: cor.muted, marginTop: 3 }}>{l.mandato}º mandato</Text>
              </View>
              <Tag tone={l.cargo.startsWith('Líder') ? 'navy' : 'sky'}>{l.cargo}</Tag>
            </View>
            {i < PARTIDO_LIDERANCAS.length - 1 ? <Divider inset={66} /> : null}
          </View>
        ))}
      </Card>
      <View style={{ height: 14 }} />
      <SectionHeader title="Coesão de voto" sub="132 votações nominais · 2025" />
      <Card padding={14}>
        {PARTIDO_COESAO.map((b) => (
          <View key={b.label} style={{ marginBottom: 8 }}>
            <View style={st.rowBetween}><Text style={st.barLabel}>{b.label}</Text><Text style={st.barVal}>{b.pct}%</Text></View>
            <AlignmentBar pct={b.pct} color={b.color} />
          </View>
        ))}
      </Card>
      <Fonte texto="Dados de exemplo — lideranças e coesão ainda não ingeridas nesta base." />
    </View>
  );
}

/* ── PROPOSIÇÕES (placeholder) ── */
function TabProposicoes() {
  return (
    <View style={{ padding: 14 }}>
      <AIPill label="Resumir proposições do partido com IA" />
      <View style={{ height: 14 }} />
      <Card padding={0}>
        {PROPOSICOES.map((pl, i) => (
          <View key={pl.id}>
            <View style={{ padding: 14 }}>
              <Text style={st.plNum}>{pl.tipo} {pl.numero}</Text>
              <Text style={st.plEmenta} numberOfLines={2}>{pl.ementa}</Text>
            </View>
            {i < PROPOSICOES.length - 1 ? <Divider inset={14} /> : null}
          </View>
        ))}
      </Card>
      <Fonte texto="Dados de exemplo — proposições ainda não ingeridas nesta base." />
    </View>
  );
}

/* ── EMENDAS (REAL) ── */
function TabEmendas({ emd }: { emd: ResumoEmendasPartido | null }) {
  if (!emd) return <View style={{ padding: 14 }}><ActivityIndicator color={cor.blue} /></View>;
  const max = emd.areas[0]?.total ?? 0;
  return (
    <View style={{ padding: 14 }}>
      <View style={{ flexDirection: 'row', gap: 8, marginBottom: 12 }}>
        <Card padding={12} style={{ flex: 1 }}><Text style={st.kpiVal2}>{kbr(emd.totalEmpenhado)}</Text><Text style={st.kpiLbl}>Empenhado</Text></Card>
        <Card padding={12} style={{ flex: 1 }}><Text style={st.kpiVal2}>{kbr(emd.totalPago)}</Text><Text style={st.kpiLbl}>Pago</Text></Card>
        <Card padding={12} style={{ flex: 1 }}><Text style={st.kpiVal2}>{emd.quantidade}</Text><Text style={st.kpiLbl}>Emendas</Text></Card>
      </View>
      {emd.quantidade === 0 ? (
        <Card padding={16}><Text style={st.vazio}>Nenhuma emenda individual atribuída aos membros deste partido nesta base.</Text></Card>
      ) : (
        <>
          <AIPill label="Comparar com a média dos partidos" />
          <View style={{ height: 14 }} />
          <SectionHeader title="Por área funcional" />
          <Card padding={14}>
            {emd.areas.slice(0, 8).map((a, i) => (
              <View key={a.funcao} style={{ marginBottom: 10 }}>
                <View style={st.rowBetween}>
                  <Text style={st.barLabel} numberOfLines={1}>{a.funcao}</Text>
                  <Text style={st.barVal}>{kbr(a.total)}</Text>
                </View>
                <View style={st.trilho}>
                  <View style={[st.preenche, { width: `${max ? (a.total / max) * 100 : 0}%`, backgroundColor: PALETA[i % PALETA.length] }]} />
                </View>
              </View>
            ))}
          </Card>
        </>
      )}
      <Fonte texto={`Portal da Transparência · dado real · estágios nunca somados · ${frescor(emd.frescor)}`} />
    </View>
  );
}

const st = StyleSheet.create({
  centro: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: cor.surface },
  erro: { color: cor.neg, textAlign: 'center', paddingHorizontal: 24 },
  monoRing: { borderRadius: 9999, borderWidth: 3, borderColor: cor.white },
  nome: { marginTop: 12, fontFamily: fonte.xb, fontSize: 24, color: cor.navy, letterSpacing: -0.4 },
  nomeSub: { color: cor.muted, fontFamily: fonte.sb, fontSize: 18 },
  sub: { fontSize: 12.5, color: cor.muted, fontFamily: fonte.m, marginTop: 2 },
  stats: { marginTop: 14, flexDirection: 'row', gap: 6, backgroundColor: cor.light, borderRadius: raio.card, paddingVertical: 12, paddingHorizontal: 14 },
  statDiv: { width: 1, backgroundColor: cor.border },
  cta: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 12, paddingVertical: 12, borderRadius: 9999 },
  ctaTxt: { color: cor.white, fontFamily: fonte.b, fontSize: 13 },
  tabsWrap: { backgroundColor: cor.surface, borderBottomWidth: 1, borderBottomColor: cor.border },
  tab: { paddingHorizontal: 14, paddingVertical: 10, position: 'relative' },
  tabTxt: { fontSize: 13 },
  tabUnderline: { position: 'absolute', left: 14, right: 14, bottom: 0, height: 2, backgroundColor: cor.navy, borderRadius: 9999 },
  fonte: { fontSize: 11, color: cor.mutedSoft, marginTop: 12, fontStyle: 'italic' },
  kpiVal: { fontFamily: fonte.xb, fontSize: 18, color: cor.navy },
  kpiVal2: { fontFamily: fonte.xb, fontSize: 16, color: cor.navy },
  kpiLbl: { marginTop: 4, fontFamily: fonte.b, fontSize: 9.5, color: cor.muted, letterSpacing: 0.8, textTransform: 'uppercase' },
  filtro: { paddingHorizontal: 11, paddingVertical: 5, borderRadius: 9999, borderWidth: 1, marginRight: 6 },
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between' },
  barLabel: { flex: 1, fontSize: 12, color: cor.navy, fontFamily: fonte.sb, marginBottom: 4 },
  barVal: { fontSize: 12, color: cor.navy, fontFamily: fonte.b },
  trilho: { height: 8, borderRadius: 4, backgroundColor: cor.light, overflow: 'hidden' },
  preenche: { height: 8, borderRadius: 4 },
  plNum: { fontFamily: fonte.xb, fontSize: 11.5, color: cor.navy, letterSpacing: 0.4, marginBottom: 4 },
  plEmenta: { fontSize: 12.5, color: cor.ink, lineHeight: 17 },
  vazio: { fontSize: 13, color: cor.muted, lineHeight: 19 },
});
