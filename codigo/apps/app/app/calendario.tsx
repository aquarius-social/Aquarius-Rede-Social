import { useEffect, useMemo, useState } from 'react';
import { View, Text, Pressable, ScrollView, ActivityIndicator, Linking, StyleSheet } from 'react-native';
import { listarEventos, type Evento } from '../lib/dados';
import { frescor } from '../lib/formato';
import { fonte, type Tema } from '../lib/tema';
import { useTemaEstilos } from '../lib/theme';
import { Icon, Card, Tag, BottomNav } from '../components/base';
import { AqHeader } from '../components/header';

const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
const DIAS = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb'];

function partesData(iso: string | null): { chave: string; dia: string; hora: string } {
  if (!iso) return { chave: 'sem-data', dia: 'Sem data', hora: '' };
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?/.exec(iso);
  if (!m) return { chave: iso, dia: iso, hora: '' };
  const [, y, mo, d, hh, mm] = m;
  const dt = new Date(Number(y), Number(mo) - 1, Number(d));
  const wd = DIAS[dt.getDay()] ?? '';
  return {
    chave: `${y}-${mo}-${d}`,
    dia: `${wd} · ${Number(d)} ${MESES[Number(mo) - 1]} ${y}`,
    hora: hh && mm ? `${hh}:${mm}` : '',
  };
}

export default function Calendario() {
  const { cor, st } = useTemaEstilos(criarSt);
  const [eventos, setEventos] = useState<Evento[] | null>(null);
  const [casa, setCasa] = useState<'camara' | 'senado' | null>(null);

  useEffect(() => { listarEventos().then(setEventos).catch(() => setEventos([])); }, []);

  const grupos = useMemo(() => {
    if (!eventos) return [];
    const filtrados = casa ? eventos.filter((e) => e.casa === casa) : eventos;
    const mapa = new Map<string, { dia: string; itens: Evento[] }>();
    for (const e of filtrados) {
      const { chave, dia } = partesData(e.inicio);
      const g = mapa.get(chave) ?? { dia, itens: [] };
      g.itens.push(e);
      mapa.set(chave, g);
    }
    return [...mapa.values()];
  }, [eventos, casa]);

  const frescorGeral = eventos && eventos.length ? frescor(eventos[0]?.syncedAt) : null;

  return (
    <View style={{ flex: 1, backgroundColor: cor.surface }}>
      <AqHeader variant="home" />

      <View style={{ paddingHorizontal: 16, paddingTop: 10 }}>
        <Text style={st.h1}>Calendário</Text>
        <Text style={st.sub}>Agenda das duas casas{frescorGeral ? ` · ${frescorGeral}` : ''}</Text>
        <View style={st.chips}>
          {([['Todas', null], ['Câmara', 'camara'], ['Senado', 'senado']] as const).map(([l, v]) => {
            const on = casa === v;
            return (
              <Pressable key={l} onPress={() => setCasa(v)} style={[st.chip, on && { backgroundColor: cor.navy, borderColor: cor.navy }]}>
                <Text style={[st.chipTxt, on && { color: cor.white }]}>{l}</Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      {eventos === null ? (
        <ActivityIndicator color={cor.blue} style={{ marginTop: 40 }} />
      ) : grupos.length === 0 ? (
        <VazioAgenda />
      ) : (
        <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 110 }}>
          {grupos.map((g) => (
            <View key={g.dia} style={{ marginBottom: 18 }}>
              <Text style={st.diaTit}>{g.dia}</Text>
              <View style={st.timeline}>
                {g.itens.map((e) => <EventoCard key={e.id} ev={e} />)}
              </View>
            </View>
          ))}
        </ScrollView>
      )}

      <BottomNav active="calendario" />
    </View>
  );
}

function EventoCard({ ev }: { ev: Evento }) {
  const { cor, st } = useTemaEstilos(criarSt);
  const { hora } = partesData(ev.inicio);
  const corCasa = ev.casa === 'senado' ? cor.sky : cor.navy;
  const cancelada = /cancel/i.test(ev.situacao ?? '');
  return (
    <View style={st.evRow}>
      <Text style={st.hora}>{hora || '—'}</Text>
      <View style={[st.ponto, { borderColor: corCasa }]} />
      <Card padding={12} style={{ flex: 1 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 5, flexWrap: 'wrap' }}>
          {ev.tipo ? <View style={[st.tipoTag, { backgroundColor: corCasa }]}><Text style={st.tipoTxt}>{ev.tipo}</Text></View> : null}
          <Tag tone={ev.casa === 'senado' ? 'sky' : 'navy'}>{ev.casa === 'senado' ? 'Senado' : 'Câmara'}</Tag>
          {ev.situacao ? <Text style={[st.situacao, cancelada && { color: cor.neg }]}>{ev.situacao}</Text> : null}
        </View>
        <Text style={st.evTit}>{ev.titulo || ev.tipo || 'Evento'}</Text>
        {ev.orgaoNome || ev.orgaoSigla ? <Text style={st.evOrgao}>{ev.orgaoSigla ? `${ev.orgaoSigla} · ` : ''}{ev.orgaoNome ?? ''}</Text> : null}
        {ev.local ? <Text style={st.evLocal}>{ev.local}</Text> : null}
        {ev.url ? (
          <Pressable onPress={() => Linking.openURL(ev.url!)} style={{ marginTop: 8, flexDirection: 'row', alignItems: 'center', gap: 5 }}>
            <Icon name="doc" size={13} color={cor.sky} />
            <Text style={st.link}>Ver na fonte oficial</Text>
          </Pressable>
        ) : null}
      </Card>
    </View>
  );
}

function VazioAgenda() {
  const { cor, st } = useTemaEstilos(criarSt);
  return (
    <View style={st.empty}>
      <View style={st.emptyIcon}><Icon name="cal" size={20} color={cor.sky} /></View>
      <Text style={st.emptyTit}>Agenda ainda não ingerida</Text>
      <Text style={st.emptyTxt}>
        O coletor de eventos das duas casas existe, mas a agenda foi deixada de fora da base atual por
        espaço. Ela entra quando ligarmos as áreas pesadas (Supabase Pro).
      </Text>
    </View>
  );
}

const criarSt = (cor: Tema) => StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 16, paddingTop: 14, paddingBottom: 10, borderBottomWidth: 1, borderBottomColor: cor.border, backgroundColor: cor.surface },
  h1: { fontSize: 26, fontFamily: fonte.xb, color: cor.texto, letterSpacing: -0.5, marginTop: 4 },
  sub: { marginTop: 2, fontFamily: fonte.r, fontSize: 12.5, color: cor.muted },
  chips: { flexDirection: 'row', gap: 6, marginTop: 12 },
  chip: { paddingHorizontal: 13, paddingVertical: 7, borderRadius: 9999, backgroundColor: cor.cartao, borderWidth: 1, borderColor: cor.border },
  chipTxt: { fontFamily: fonte.sb, fontSize: 12, color: cor.texto },
  diaTit: { fontFamily: fonte.b, fontSize: 11.5, color: cor.muted, letterSpacing: 0.6, textTransform: 'uppercase', marginBottom: 10 },
  timeline: { paddingLeft: 4 },
  evRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, marginBottom: 10 },
  hora: { width: 40, textAlign: 'right', fontFamily: fonte.b, fontSize: 11, color: cor.muted, paddingTop: 12 },
  ponto: { width: 12, height: 12, borderRadius: 9999, borderWidth: 2.5, backgroundColor: cor.cartao, marginTop: 12 },
  tipoTag: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 9999 },
  tipoTxt: { fontFamily: fonte.b, fontSize: 9, color: cor.white, letterSpacing: 0.4, textTransform: 'uppercase' },
  situacao: { fontFamily: fonte.sb, fontSize: 10.5, color: cor.muted },
  evTit: { fontFamily: fonte.b, fontSize: 13.5, color: cor.texto, lineHeight: 18 },
  evOrgao: { marginTop: 3, fontFamily: fonte.m, fontSize: 11.5, color: cor.ink },
  evLocal: { marginTop: 2, fontFamily: fonte.r, fontSize: 11, color: cor.muted },
  link: { fontFamily: fonte.b, fontSize: 11.5, color: cor.sky },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, paddingBottom: 80 },
  emptyIcon: { width: 48, height: 48, borderRadius: 9999, backgroundColor: cor.light, alignItems: 'center', justifyContent: 'center', marginBottom: 12 },
  emptyTit: { fontFamily: fonte.b, fontSize: 15, color: cor.texto },
  emptyTxt: { marginTop: 6, fontFamily: fonte.r, fontSize: 13, color: cor.muted, textAlign: 'center', lineHeight: 19 },
});
