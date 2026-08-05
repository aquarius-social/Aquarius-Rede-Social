import { useEffect, useState } from 'react';
import { View, Text, ScrollView, ActivityIndicator, Pressable, Linking, StyleSheet } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import {
  obterParlamentar, resumoDespesas, resumoEmendas, ANO_DESPESAS,
  type Parlamentar, type ResumoDespesas, type ResumoEmendas,
} from '../../lib/dados';
import { reais, kbr, dataBR, URL_EMENDAS_CONSULTA, frescor } from '../../lib/formato';
import { cor, raio } from '../../lib/tema';
import {
  Avatar, Cover, PartyChip, Tag, Stat, Card, SectionHeader, Divider, AlignmentBar,
  AIPill, AICard, AIBanner, FollowButton, BottomNav, Icon, Donut, LineChart, BarChart,
} from '../../components/base';
import {
  KPI_PLACEHOLDER, PROPOSICOES, VOTACOES, ALINHAMENTO, PRESENCA, PRESENCA_LABELS,
  PRESENCA_POR_SESSAO, DISCURSOS, DISCURSO_TEMAS, AGENDA, ORGAOS,
} from '../../lib/mock';

const TABS = [
  { id: 'feed', label: 'Feed' }, { id: 'proposicoes', label: 'Proposições' },
  { id: 'votacoes', label: 'Votações' }, { id: 'presenca', label: 'Presença' },
  { id: 'despesas', label: 'Despesas' }, { id: 'emendas', label: 'Emendas' },
  { id: 'discursos', label: 'Discursos' }, { id: 'agenda', label: 'Agenda' },
  { id: 'orgaos', label: 'Órgãos' },
] as const;
type TabId = (typeof TABS)[number]['id'];

const PALETA = ['#0D2B5E', '#1A4FA0', '#2E7DD1', '#5FA0E0', '#7AB1E6', '#A0C9EF', '#C7DDF4'];

function primeiroNome(n: string) { return n.trim().split(/\s+/)[0] ?? n; }
function rotuloCargo(oc: string | null) {
  if (!oc) return 'PARLAMENTAR';
  const m: Record<string, string> = { titular: 'Deputado(a) Federal', suplente_em_exercicio: 'Suplente em exercício' };
  return m[oc] ?? oc;
}

export default function PerfilParlamentar() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [p, setP] = useState<Parlamentar | null>(null);
  const [desp, setDesp] = useState<ResumoDespesas | null>(null);
  const [emd, setEmd] = useState<ResumoEmendas | null>(null);
  const [tab, setTab] = useState<TabId>('despesas');
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let vivo = true;
    (async () => {
      try {
        const [pp, dd, ee] = await Promise.all([obterParlamentar(id), resumoDespesas(id), resumoEmendas(id)]);
        if (!vivo) return;
        setP(pp); setDesp(dd); setEmd(ee);
      } catch (e: any) { if (vivo) setErro(e?.message ?? 'Falha ao carregar'); }
      finally { if (vivo) setCarregando(false); }
    })();
    return () => { vivo = false; };
  }, [id]);

  if (carregando) return <View style={st.centro}><ActivityIndicator color={cor.blue} /></View>;
  if (erro || !p) return <View style={st.centro}><Text style={st.erro}>{erro ?? 'Parlamentar não encontrado.'}</Text></View>;

  return (
    <View style={{ flex: 1, backgroundColor: cor.surface }}>
      <ScrollView contentContainerStyle={{ paddingBottom: 96 }}>
        {/* ── Header cover ── */}
        <View style={{ backgroundColor: cor.white }}>
          <Cover height={88} />
          <View style={{ paddingHorizontal: 16, paddingBottom: 16, marginTop: -30 }}>
            <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 14 }}>
              <View style={st.avatarRing}><Avatar nome={p.nome} size={72} /></View>
              <View style={{ flex: 1, paddingBottom: 6 }}>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
                  <PartyChip sigla={p.partido_sigla_atual} uf={p.uf_atual} />
                  <Tag tone="muted">{rotuloCargo(p.ocupacao_atual)}</Tag>
                </View>
              </View>
            </View>
            <Text style={st.nome}>{p.nome}</Text>
            <Text style={st.sub}>{p.legislatura ? `${p.legislatura}ª legislatura` : 'Legislatura atual'}</Text>

            {/* Stats — presença/aliado/proposições ainda são placeholder do design */}
            <View style={st.stats}>
              <Stat value={`${KPI_PLACEHOLDER.presenca}%`} label="Presença" tone="pos" sub="acima da média" />
              <View style={st.statDiv} />
              <Stat value={`${KPI_PLACEHOLDER.alinhamentoPart}%`} label={`Aliado ${p.partido_sigla_atual ?? ''}`} />
              <View style={st.statDiv} />
              <Stat value={KPI_PLACEHOLDER.proposicoesAuto} label="Proposições" />
            </View>

            <View style={{ flexDirection: 'row', gap: 8, marginTop: 12 }}>
              <FollowButton />
              <Pressable style={st.ctaGhost}>
                <Icon name="spark" size={15} color={cor.navy} />
                <Text style={st.ctaGhostTxt}>Perguntar à IA</Text>
              </Pressable>
            </View>
          </View>
        </View>

        {/* ── Abas ── */}
        <View style={st.tabsWrap}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: 8, paddingVertical: 6 }}>
            {TABS.map((t) => {
              const sel = t.id === tab;
              return (
                <Pressable key={t.id} onPress={() => setTab(t.id)} style={st.tab}>
                  <Text style={[st.tabTxt, { color: sel ? cor.navy : cor.muted, fontWeight: sel ? '700' : '600' }]}>{t.label}</Text>
                  {sel ? <View style={st.tabUnderline} /> : null}
                </Pressable>
              );
            })}
          </ScrollView>
        </View>

        {/* ── Conteúdo ── */}
        {tab === 'feed' && <TabFeed nome={p.nome} />}
        {tab === 'proposicoes' && <TabProposicoes />}
        {tab === 'votacoes' && <TabVotacoes />}
        {tab === 'presenca' && <TabPresenca />}
        {tab === 'despesas' && <TabDespesas desp={desp} />}
        {tab === 'emendas' && <TabEmendas emd={emd} />}
        {tab === 'discursos' && <TabDiscursos />}
        {tab === 'agenda' && <TabAgenda />}
        {tab === 'orgaos' && <TabOrgaos />}
      </ScrollView>
      <BottomNav active="explorar" />
    </View>
  );
}

function Fonte({ texto }: { texto: string }) {
  return <Text style={st.fonte}>{texto}</Text>;
}

/* ── FEED ── */
function TabFeed({ nome }: { nome: string }) {
  return (
    <View style={{ padding: 14 }}>
      <View style={st.infoNote}>
        <Icon name="info" size={14} color={cor.muted} />
        <Text style={st.infoNoteTxt}>Registros da plataforma sobre a atividade de {primeiroNome(nome)}, em 3ª pessoa. O perfil não publica diretamente.</Text>
      </View>
      <Text style={st.vazioCentro}>Sem registros recentes.</Text>
    </View>
  );
}

/* ── PROPOSIÇÕES (protótipo) ── */
function TabProposicoes() {
  return (
    <View style={{ padding: 14 }}>
      <AIPill label="Analisar 47 proposições com IA" />
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginVertical: 12 }}>
        {['Todos', 'PL', 'PEC', 'REQ', 'PDL'].map((c, i) => (
          <View key={c} style={[st.filtro, { backgroundColor: i === 0 ? cor.navy : cor.white, borderColor: i === 0 ? cor.navy : cor.border }]}>
            <Text style={{ color: i === 0 ? cor.white : cor.navy, fontWeight: '600', fontSize: 11.5 }}>{c}</Text>
          </View>
        ))}
      </ScrollView>
      <Card padding={0}>
        {PROPOSICOES.map((pl, i) => (
          <View key={pl.id}>
            <View style={{ flexDirection: 'row', gap: 12, padding: 14 }}>
              <View style={{ flex: 1 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <Text style={st.plNum}>{pl.tipo} {pl.numero}</Text>
                  {pl.resumoIA ? <View style={st.iaBadge}><Text style={st.iaBadgeTxt}>✦ resumo IA</Text></View> : null}
                </View>
                <Text style={st.plEmenta} numberOfLines={2}>{pl.ementa}</Text>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 6 }}>
                  <Text style={st.plMeta}>{pl.tema}</Text>
                  <View style={st.dot} />
                  <Text style={st.plMeta}>{pl.dataApres}</Text>
                </View>
              </View>
              <Tag tone={pl.situacao.includes('Aprovado') ? 'pos' : pl.situacao === 'Arquivado' ? 'neg' : pl.situacao === 'Aguardando relator' ? 'warn' : 'muted'}>
                {pl.situacao.split(' ')[0]}
              </Tag>
            </View>
            {i < PROPOSICOES.length - 1 ? <Divider inset={14} /> : null}
          </View>
        ))}
      </Card>
      <Fonte texto="Dados de exemplo — proposições ainda não ingeridas nesta base." />
    </View>
  );
}

/* ── VOTAÇÕES (protótipo) ── */
function TabVotacoes() {
  const sims = VOTACOES.filter((v) => v.voto === 'Sim').length;
  const naos = VOTACOES.filter((v) => v.voto === 'Não').length;
  const absts = VOTACOES.filter((v) => v.voto === 'Abstenção').length;
  return (
    <View style={{ padding: 14 }}>
      <Card padding={14}>
        <Text style={st.secHeadTitle}>Alinhamento em 132 votações nominais · 2025–2026</Text>
        <View style={{ marginTop: 14, gap: 11 }}>
          {ALINHAMENTO.map((b) => (
            <View key={b.label}>
              <View style={st.rowBetween}>
                <Text style={st.barLabel}>{b.label}</Text>
                <Text style={st.barVal}>{b.pct}%</Text>
              </View>
              <AlignmentBar pct={b.pct} color={b.color} />
            </View>
          ))}
        </View>
      </Card>
      <View style={{ height: 12 }} />
      <AICard title="Padrão de voto · IA" body="Alinhou-se ao PSB em 89% das votações de 2025. Desalinhou em 3 pautas: MP 1227 (ICMS), PL 4188 (saneamento) e REQ 1023." />
      <View style={{ flexDirection: 'row', gap: 6, marginTop: 14 }}>
        <View style={[st.distSeg, { flex: sims, backgroundColor: cor.pos, borderTopLeftRadius: 9999, borderBottomLeftRadius: 9999 }]}><Text style={st.distTxt}>{sims} SIM</Text></View>
        <View style={[st.distSeg, { flex: naos, backgroundColor: cor.neg }]}><Text style={st.distTxt}>{naos} NÃO</Text></View>
        <View style={[st.distSeg, { flex: absts, backgroundColor: cor.abst, borderTopRightRadius: 9999, borderBottomRightRadius: 9999 }]}><Text style={st.distTxt}>{absts} ABST.</Text></View>
      </View>
      <View style={{ gap: 8, marginTop: 14 }}>
        {VOTACOES.map((v) => {
          const tone = v.voto === 'Sim' ? 'pos' : v.voto === 'Não' ? 'neg' : 'abst';
          const c = tone === 'pos' ? cor.pos : tone === 'neg' ? cor.neg : cor.abst;
          return (
            <Card key={v.id} padding={12} style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
              <View style={[st.votoBox, { backgroundColor: tone === 'pos' ? 'rgba(30,142,92,0.12)' : tone === 'neg' ? 'rgba(198,58,58,0.12)' : 'rgba(107,114,128,0.12)' }]}>
                <Text style={{ color: c, fontWeight: '800', fontSize: 11, letterSpacing: 0.4 }}>{v.voto === 'Abstenção' ? 'ABST' : v.voto.toUpperCase()}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={st.votoTitulo} numberOfLines={2}>{v.titulo}</Text>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 5 }}>
                  <Text style={st.plMeta}>{v.data}</Text>
                  <View style={st.dot} />
                  <Tag tone={v.resultado === 'Aprovada' ? 'pos' : v.resultado === 'Rejeitada' ? 'neg' : 'muted'}>{v.resultado}</Tag>
                </View>
              </View>
            </Card>
          );
        })}
      </View>
      <Fonte texto="Dados de exemplo — votações ainda não ingeridas nesta base." />
    </View>
  );
}

/* ── PRESENÇA (protótipo) ── */
function TabPresenca() {
  const media = (PRESENCA.reduce((s, v) => s + v, 0) / PRESENCA.length).toFixed(1);
  return (
    <View style={{ padding: 14 }}>
      <AICard title="Resumo do Prometeus" body={`Presença média de ${media}% nos últimos 12 meses — 4,2 p.p. acima da bancada do PSB. Maior ausência em julho.`} />
      <View style={{ height: 12 }} />
      <Card padding={14}>
        <View style={[st.rowBetween, { alignItems: 'baseline', marginBottom: 10 }]}>
          <View>
            <Text style={st.bigPct}>{media}<Text style={{ fontSize: 16 }}>%</Text></Text>
            <Text style={st.secHeadTitle}>Presença · 12 meses</Text>
          </View>
          <Tag tone="pos">+4,2 p.p. vs PSB</Tag>
        </View>
        <LineChart data={PRESENCA} labels={PRESENCA_LABELS} w={310} h={120} accent={cor.sky} min={80} max={100} />
      </Card>
      <View style={{ height: 12 }} />
      <Card padding={14}>
        <Text style={[st.secHeadTitle, { marginBottom: 10 }]}>Presença por tipo de sessão</Text>
        {PRESENCA_POR_SESSAO.map((s2) => (
          <View key={s2.label} style={{ marginBottom: 10 }}>
            <View style={st.rowBetween}><Text style={st.barLabel}>{s2.label}</Text><Text style={st.barVal}>{s2.pct}%</Text></View>
            <AlignmentBar pct={s2.pct} color={cor.navy} />
          </View>
        ))}
      </Card>
      <Fonte texto="Dados de exemplo — presença ainda não ingerida nesta base." />
    </View>
  );
}

/* ── DESPESAS (REAL) ── */
function TabDespesas({ desp }: { desp: ResumoDespesas | null }) {
  const [catAberta, setCatAberta] = useState<string | null>(null);
  if (!desp) return <View style={{ padding: 14 }}><ActivityIndicator color={cor.blue} /></View>;
  const donutData = desp.categorias.slice(0, 7).map((c, i) => ({ valor: c.total, cor: PALETA[i % PALETA.length] }));
  const temMensal = desp.mensal.some((v) => v > 0);
  const media = temMensal ? desp.mensal.filter((v) => v > 0).reduce((s, v) => s + v, 0) / desp.mensal.filter((v) => v > 0).length : 0;
  const pico = Math.max(0, ...desp.mensal);
  return (
    <View style={{ padding: 14 }}>
      {desp.lancamentos === 0 ? (
        <Card padding={16}><Text style={st.vazio}>Sem despesas de cota parlamentar registradas em {ANO_DESPESAS}.</Text></Card>
      ) : (
        <>
          <Card padding={14}>
            <View style={{ flexDirection: 'row', gap: 14, alignItems: 'center' }}>
              <Donut data={donutData} w={130} valueLabel={kbr(desp.totalLiquido)} sub={`${ANO_DESPESAS} · ANO`} />
              <View style={{ flex: 1 }}>
                <Text style={st.secHeadTitle}>Cota Parlamentar</Text>
                <Text style={{ marginTop: 6, fontSize: 12.5, color: cor.muted, lineHeight: 19 }}>
                  {desp.lancamentos} lançamentos líquidos em {ANO_DESPESAS}, verificados pela identidade documento − glosa = líquido.
                </Text>
              </View>
            </View>
          </Card>
          <View style={{ height: 12 }} />
          <AIBanner hint="Comparar com a média do partido e da bancada" cta="Analisar" />
          <View style={{ height: 14 }} />
          <SectionHeader title="Por categoria" sub="toque para ver os lançamentos" />
          <Card padding={0}>
            {desp.categorias.map((c, i) => {
              const aberta = catAberta === c.tipo;
              return (
                <View key={c.tipo}>
                  <Pressable onPress={() => setCatAberta(aberta ? null : c.tipo)} style={{ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14 }}>
                    <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: PALETA[i % PALETA.length] }} />
                    <View style={{ flex: 1 }}>
                      <Text style={{ fontSize: 13, fontWeight: '600', color: cor.navy }} numberOfLines={1}>{c.tipo}</Text>
                      <Text style={{ fontSize: 10.5, color: cor.mutedSoft, marginTop: 2 }}>{c.itens.length} lançamento{c.itens.length !== 1 ? 's' : ''}</Text>
                    </View>
                    <View style={{ alignItems: 'flex-end' }}>
                      <Text style={{ fontSize: 13, fontWeight: '700', color: cor.navy }}>{kbr(c.total)}</Text>
                      <Text style={{ fontSize: 10.5, color: cor.muted, marginTop: 2 }}>{((c.total / desp.totalLiquido) * 100).toFixed(1).replace('.', ',')}%</Text>
                    </View>
                    <View style={{ transform: [{ rotate: aberta ? '90deg' : '0deg' }] }}>
                      <Icon name="chevR" size={16} color={cor.mutedSoft} />
                    </View>
                  </Pressable>
                  {aberta ? (
                    <View style={{ backgroundColor: cor.surface, paddingHorizontal: 14, paddingBottom: 6, paddingTop: 2 }}>
                      {c.itens.slice(0, 15).map((it, j) => (
                        <View key={j} style={st.lancamento}>
                          <View style={{ flex: 1 }}>
                            <Text style={{ fontSize: 12.5, color: cor.ink, fontWeight: '600' }} numberOfLines={1}>{it.fornecedor ?? 'Fornecedor não informado'}</Text>
                            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 2 }}>
                              <Text style={st.plMeta}>{dataBR(it.data)}</Text>
                              {it.urlDocumento ? (
                                <Pressable onPress={() => Linking.openURL(it.urlDocumento!)}>
                                  <Text style={st.link}>ver nota fiscal ↗</Text>
                                </Pressable>
                              ) : null}
                            </View>
                          </View>
                          <Text style={{ fontSize: 12.5, fontWeight: '700', color: cor.navy }}>{reais(it.valorLiquido)}</Text>
                        </View>
                      ))}
                      {c.itens.length > 15 ? <Text style={st.maisItens}>+ {c.itens.length - 15} outros lançamentos</Text> : null}
                    </View>
                  ) : null}
                  {i < desp.categorias.length - 1 ? <Divider inset={34} /> : null}
                </View>
              );
            })}
          </Card>
          {temMensal ? (
            <>
              <View style={{ height: 14 }} />
              <SectionHeader title={`Histórico mensal · ${ANO_DESPESAS}`} />
              <Card padding={14}>
                <BarChart data={desp.mensal} labels={['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']} w={310} h={120} accent={cor.navy} />
                <View style={[st.rowBetween, { marginTop: 10 }]}>
                  <Text style={st.plMeta}>Média mensal: {kbr(media)}</Text>
                  <Text style={st.plMeta}>Pico: {kbr(pico)}</Text>
                </View>
              </Card>
            </>
          ) : null}
        </>
      )}
      <Fonte texto={`Cota parlamentar (CEAP) · dado real · ${frescor(desp.frescor)}`} />
    </View>
  );
}

/* ── EMENDAS (REAL) ── */
function EstagioLinha({ rotulo, valor, forte }: { rotulo: string; valor: number | null; forte?: boolean }) {
  if (valor === null || valor === 0) return null;
  return (
    <View style={st.estagioLinha}>
      <Text style={[st.estagioRot, forte ? { color: cor.navy, fontWeight: '700' } : null]}>{rotulo}</Text>
      <Text style={[st.estagioVal, forte ? { color: cor.pos } : null]}>{reais(valor)}</Text>
    </View>
  );
}

function TabEmendas({ emd }: { emd: ResumoEmendas | null }) {
  const [aberta, setAberta] = useState<string | null>(null);
  if (!emd) return <View style={{ padding: 14 }}><ActivityIndicator color={cor.blue} /></View>;

  const abrirGov = () => Linking.openURL(URL_EMENDAS_CONSULTA);

  return (
    <View style={{ padding: 14 }}>
      <View style={{ flexDirection: 'row', gap: 8, marginBottom: 14 }}>
        <Card padding={12} style={{ flex: 1 }}><Text style={st.kpiVal}>{kbr(emd.totalEmpenhado)}</Text><Text style={st.kpiLbl}>Empenhado</Text></Card>
        <Card padding={12} style={{ flex: 1 }}><Text style={st.kpiVal}>{kbr(emd.totalPago)}</Text><Text style={st.kpiLbl}>Pago</Text></Card>
        <Card padding={12} style={{ flex: 1 }}><Text style={st.kpiVal}>{emd.quantidade}</Text><Text style={st.kpiLbl}>Emendas</Text></Card>
      </View>
      {emd.quantidade === 0 ? (
        <Card padding={16}><Text style={st.vazio}>Nenhuma emenda atribuída a este parlamentar (autoria individual). Emendas de bancada/comissão são coletivas.</Text></Card>
      ) : (
        <>
          <SectionHeader title="Emendas individuais" sub="toque para ver o detalhe e a fonte oficial" />
          <Card padding={0}>
            {emd.linhas.slice(0, 20).map((e, i, arr) => {
              const ab = aberta === e.id;
              return (
                <View key={e.id}>
                  <Pressable onPress={() => setAberta(ab ? null : e.id)} style={{ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14 }}>
                    <View style={{ flex: 1 }}>
                      <Text style={{ fontSize: 13, fontWeight: '600', color: cor.navy }} numberOfLines={1}>{e.finalidade ?? 'Área não informada'}</Text>
                      <Text style={{ fontSize: 11, color: cor.muted, marginTop: 2 }} numberOfLines={1}>
                        {[e.subfuncao, e.uf, String(e.ano)].filter(Boolean).join(' · ')}
                      </Text>
                    </View>
                    <Text style={{ fontSize: 14, fontWeight: '700', color: cor.navy }}>{kbr(e.pago ?? 0)}</Text>
                    <View style={{ transform: [{ rotate: ab ? '90deg' : '0deg' }] }}><Icon name="chevR" size={16} color={cor.mutedSoft} /></View>
                  </Pressable>
                  {ab ? (
                    <View style={st.emendaDet}>
                      {/* Área / destino — o que a fonte federal descreve */}
                      <View style={st.detRow}><Text style={st.detK}>Área</Text><Text style={st.detV}>{[e.finalidade, e.subfuncao].filter(Boolean).join(' › ') || '—'}</Text></View>
                      <View style={st.detRow}><Text style={st.detK}>Destino</Text><Text style={st.detV}>{e.uf ?? '—'}</Text></View>
                      <View style={st.detRow}><Text style={st.detK}>Código</Text><Text selectable style={[st.detV, { fontVariant: ['tabular-nums'] }]}>{e.codigo ?? '—'}</Text></View>

                      {/* Estágios — NUNCA somados entre si (§13) */}
                      <Text style={[st.secHeadTitle, { marginTop: 10, marginBottom: 6 }]}>Execução orçamentária</Text>
                      <EstagioLinha rotulo="Empenhado" valor={e.empenhado} />
                      <EstagioLinha rotulo="Liquidado" valor={e.liquidado} />
                      <EstagioLinha rotulo="Pago" valor={e.pago} forte />
                      <EstagioLinha rotulo="Restos inscritos" valor={e.restoInscrito} />
                      <EstagioLinha rotulo="Restos pagos" valor={e.restoPago} />

                      <Text style={st.fonteOficial}>Fonte: Portal da Transparência.</Text>
                      <Pressable onPress={abrirGov} style={st.govBtn}>
                        <Icon name="doc" size={14} color={cor.white} />
                        <Text style={st.govBtnTxt}>Ver no Portal — filtre por autor e ano ↗</Text>
                      </Pressable>
                    </View>
                  ) : null}
                  {i < arr.length - 1 ? <Divider inset={14} /> : null}
                </View>
              );
            })}
          </Card>
          {emd.linhas.length > 20 ? <Text style={st.maisItens}>+ {emd.linhas.length - 20} outras emendas</Text> : null}
        </>
      )}
      <Fonte texto={`Portal da Transparência · dado real · estágios nunca somados · ${frescor(emd.frescor)}`} />
    </View>
  );
}

/* ── DISCURSOS (protótipo) ── */
function TabDiscursos() {
  return (
    <View style={{ padding: 14 }}>
      <AIPill label="Analisar temas dos discursos" />
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginVertical: 12 }}>
        {DISCURSO_TEMAS.map((t, i) => (
          <View key={t} style={[st.filtro, { backgroundColor: i === 0 ? cor.navy : cor.white, borderColor: i === 0 ? cor.navy : cor.border }]}>
            <Text style={{ color: i === 0 ? cor.white : cor.navy, fontWeight: '600', fontSize: 11 }}>{t}</Text>
          </View>
        ))}
      </ScrollView>
      <View style={{ gap: 10 }}>
        {DISCURSOS.map((d) => (
          <Card key={d.id} padding={14}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <Tag tone="muted">{d.tipo}</Tag>
              <Tag tone="sky">{d.tema}</Tag>
              <Text style={{ marginLeft: 'auto', fontSize: 10.5, color: cor.muted, fontWeight: '600' }}>{d.data} · {d.dur}</Text>
            </View>
            <Text style={{ fontSize: 13, color: cor.ink, lineHeight: 20 }}>{d.resumo}</Text>
          </Card>
        ))}
      </View>
      <Fonte texto="Dados de exemplo — discursos ainda não ingeridos nesta base." />
    </View>
  );
}

/* ── AGENDA (protótipo) ── */
function TabAgenda() {
  return (
    <View style={{ padding: 14 }}>
      <SectionHeader title="Próximos compromissos" sub="Agenda pública oficial" />
      <View style={{ paddingLeft: 24, position: 'relative' }}>
        <View style={st.timeline} />
        {AGENDA.map((e, i) => (
          <View key={i} style={{ marginBottom: 14, position: 'relative' }}>
            <View style={st.timelineDot} />
            <Card padding={12}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                <Tag tone={e.tipo === 'Comissão' ? 'navy' : e.tipo === 'Externa' ? 'sky' : 'muted'}>{e.tipo}</Tag>
                <Text style={{ fontSize: 10.5, color: cor.muted, fontWeight: '700', letterSpacing: 0.6 }}>{e.data.toUpperCase()}</Text>
              </View>
              <Text style={{ fontWeight: '700', fontSize: 13.5, color: cor.navy }}>{e.titulo}</Text>
              <Text style={{ marginTop: 4, fontSize: 11.5, color: cor.muted }}>{e.local}</Text>
            </Card>
          </View>
        ))}
      </View>
      <Fonte texto="Dados de exemplo — agenda ainda não ingerida nesta base." />
    </View>
  );
}

/* ── ÓRGÃOS (protótipo) ── */
function TabOrgaos() {
  return (
    <View style={{ padding: 14 }}>
      <SectionHeader title="Comissões e frentes" />
      <View style={{ gap: 8 }}>
        {ORGAOS.map((o) => (
          <Card key={o.id} padding={12}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
              <View style={[st.orgIcon, { backgroundColor: o.cor }]}>
                <Icon name={o.nome.startsWith('Frente') ? 'star' : 'building'} size={18} color={cor.white} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={{ fontWeight: '700', fontSize: 13, color: cor.navy, lineHeight: 17 }}>{o.nome}</Text>
                <View style={{ marginTop: 3, flexDirection: 'row' }}>
                  <Tag tone={o.cargo.includes('Coord') || o.cargo.includes('Vice') ? 'sky' : 'muted'}>{o.cargo}</Tag>
                </View>
              </View>
              <Icon name="chevR" size={15} color={cor.mutedSoft} />
            </View>
          </Card>
        ))}
      </View>
      <Fonte texto="Dados de exemplo — órgãos ainda não ingeridos nesta base." />
    </View>
  );
}

const st = StyleSheet.create({
  centro: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: cor.surface },
  erro: { color: cor.neg, textAlign: 'center', paddingHorizontal: 24 },
  avatarRing: { borderRadius: 9999, borderWidth: 3, borderColor: cor.white },
  nome: { marginTop: 12, fontWeight: '800', fontSize: 24, color: cor.navy, letterSpacing: -0.4 },
  sub: { fontSize: 12.5, color: cor.muted, fontWeight: '500', marginTop: 2 },
  stats: { marginTop: 14, flexDirection: 'row', gap: 6, backgroundColor: cor.light, borderRadius: raio.card, paddingVertical: 12, paddingHorizontal: 14 },
  statDiv: { width: 1, backgroundColor: cor.border },
  ctaGhost: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 7, paddingVertical: 12, borderRadius: 9999, backgroundColor: cor.white, borderWidth: 1, borderColor: cor.borderStrong },
  ctaGhostTxt: { fontWeight: '700', fontSize: 12.5, color: cor.navy },
  tabsWrap: { backgroundColor: cor.surface, borderBottomWidth: 1, borderBottomColor: cor.border },
  tab: { paddingHorizontal: 14, paddingVertical: 10, position: 'relative' },
  tabTxt: { fontSize: 13 },
  tabUnderline: { position: 'absolute', left: 14, right: 14, bottom: 0, height: 2, backgroundColor: cor.navy, borderRadius: 9999 },
  fonte: { fontSize: 11, color: cor.mutedSoft, marginTop: 12, fontStyle: 'italic' },
  infoNote: { flexDirection: 'row', gap: 8, alignItems: 'center', padding: 12, borderRadius: 12, backgroundColor: cor.light, borderWidth: 1, borderColor: cor.border, marginBottom: 12 },
  infoNoteTxt: { flex: 1, fontSize: 11, color: cor.muted, lineHeight: 16 },
  vazioCentro: { textAlign: 'center', paddingVertical: 30, fontSize: 13, color: cor.muted },
  vazio: { fontSize: 13, color: cor.muted, lineHeight: 19 },
  filtro: { paddingHorizontal: 11, paddingVertical: 5, borderRadius: 9999, borderWidth: 1, marginRight: 6 },
  plNum: { fontWeight: '800', fontSize: 11.5, color: cor.navy, letterSpacing: 0.4 },
  plEmenta: { fontSize: 12.5, color: cor.ink, lineHeight: 17 },
  plMeta: { fontSize: 10.5, color: cor.muted, fontWeight: '500' },
  iaBadge: { paddingHorizontal: 6, paddingVertical: 1, borderRadius: 9999, backgroundColor: 'rgba(46,125,209,0.12)' },
  iaBadgeTxt: { color: cor.sky, fontWeight: '700', fontSize: 9.5, letterSpacing: 0.4 },
  dot: { width: 3, height: 3, borderRadius: 2, backgroundColor: cor.border },
  secHeadTitle: { fontWeight: '700', fontSize: 11, color: cor.muted, letterSpacing: 1.2, textTransform: 'uppercase' },
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between' },
  barLabel: { fontSize: 12, color: cor.navy, fontWeight: '600', marginBottom: 4 },
  barVal: { fontSize: 12, color: cor.navy, fontWeight: '700' },
  distSeg: { paddingVertical: 7, paddingHorizontal: 10, justifyContent: 'center' },
  distTxt: { color: cor.white, fontSize: 10.5, fontWeight: '700', letterSpacing: 0.4 },
  votoBox: { width: 48, height: 48, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  votoTitulo: { fontSize: 12.5, fontWeight: '600', color: cor.navy, lineHeight: 16 },
  bigPct: { fontWeight: '800', fontSize: 30, color: cor.navy, letterSpacing: -0.6 },
  kpiVal: { fontWeight: '800', fontSize: 17, color: cor.navy },
  kpiLbl: { marginTop: 4, fontWeight: '700', fontSize: 9.5, color: cor.muted, letterSpacing: 0.8, textTransform: 'uppercase' },
  timeline: { position: 'absolute', left: 6, top: 6, bottom: 6, width: 2, backgroundColor: cor.border },
  timelineDot: { position: 'absolute', left: -22, top: 8, width: 14, height: 14, borderRadius: 7, backgroundColor: cor.white, borderWidth: 2.5, borderColor: cor.sky },
  orgIcon: { width: 38, height: 38, borderRadius: 9, alignItems: 'center', justifyContent: 'center' },
  // drill-down despesas
  lancamento: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: cor.border },
  link: { fontSize: 11, fontWeight: '600', color: cor.sky },
  maisItens: { fontSize: 11.5, color: cor.mutedSoft, textAlign: 'center', paddingVertical: 10, fontStyle: 'italic' },
  // drill-down emendas
  emendaDet: { backgroundColor: cor.surface, paddingHorizontal: 14, paddingTop: 6, paddingBottom: 14 },
  detRow: { flexDirection: 'row', paddingVertical: 4, gap: 12 },
  detK: { width: 64, fontSize: 12, color: cor.mutedSoft, fontWeight: '600' },
  detV: { flex: 1, fontSize: 12.5, color: cor.ink, fontWeight: '600' },
  estagioLinha: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 },
  estagioRot: { fontSize: 12.5, color: cor.muted },
  estagioVal: { fontSize: 12.5, color: cor.navy, fontWeight: '600' },
  fonteOficial: { fontSize: 11.5, color: cor.mutedSoft, marginTop: 12 },
  govBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 7, marginTop: 8, paddingVertical: 10, borderRadius: 9999, backgroundColor: cor.navy },
  govBtnTxt: { color: cor.white, fontWeight: '700', fontSize: 12.5 },
});
