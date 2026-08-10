import { useState } from 'react';
import { View, Text, Pressable, ScrollView, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../lib/auth';
import { raio, fonte, type Tema } from '../lib/tema';
import { useTemaEstilos } from '../lib/theme';
import { Icon, Card, SectionHeader, Divider, Monogram, BottomNav } from '../components/base';
import { PARTIDO_COR } from '../lib/mock';
import { TEMAS, PARTIDOS } from '../lib/catalogos';

export default function Interesses() {
  const { cor, st } = useTemaEstilos(criarSt);
  const router = useRouter();
  const { prefs, atualizarPrefs } = useAuth();
  const [temas, setTemas] = useState<string[]>(prefs.temas ?? []);
  const [partidos, setPartidos] = useState<string[]>(prefs.partidos ?? []);
  const [addTema, setAddTema] = useState(false);
  const [addPartido, setAddPartido] = useState(false);

  // Atualiza local (snappy) e persiste no perfil em background.
  const salvarTemas = (novos: string[]) => { setTemas(novos); atualizarPrefs({ temas: novos }).catch(() => {}); };
  const salvarPartidos = (novos: string[]) => { setPartidos(novos); atualizarPrefs({ partidos: novos }).catch(() => {}); };

  const temasRestantes = TEMAS.filter((t) => !temas.includes(t));
  const partidosRestantes = PARTIDOS.filter((p) => !partidos.includes(p));

  return (
    <View style={{ flex: 1, backgroundColor: cor.surface }}>
      <ScrollView contentContainerStyle={{ paddingHorizontal: 16, paddingTop: 12, paddingBottom: 100 }}>
        <Text style={st.h1}>Interesses</Text>
        <Text style={st.sub}>Seus temas e partidos guiam o feed. Ajuste quando quiser.</Text>

        {/* Temas */}
        <View style={{ height: 16 }} />
        <SectionHeader title="Seus temas" action={
          <Pressable onPress={() => setAddTema((v) => !v)}><Text style={st.acao}>{addTema ? 'Fechar' : 'Adicionar'}</Text></Pressable>
        } />
        {addTema ? (
          <View style={st.picker}>
            {temasRestantes.length ? temasRestantes.map((t) => (
              <Pressable key={t} onPress={() => salvarTemas([...temas, t])} style={st.pickerChip}>
                <Icon name="plus" size={12} color={cor.sky} /><Text style={st.pickerChipTxt}>{t}</Text>
              </Pressable>
            )) : <Text style={st.vazioMini}>Você já segue todos os temas.</Text>}
          </View>
        ) : null}
        {temas.length ? (
          <View style={st.chipsWrap}>
            {temas.map((t) => (
              <Pressable key={t} onPress={() => salvarTemas(temas.filter((x) => x !== t))} style={st.chip}>
                <Text style={st.chipTxt}>#{t}</Text><Icon name="x" size={11} color={cor.mutedSoft} />
              </Pressable>
            ))}
          </View>
        ) : <EmptyMini texto="Nenhum tema ainda. Toque em Adicionar." />}

        {/* Partidos */}
        <View style={{ height: 20 }} />
        <SectionHeader title="Seus partidos" action={
          <Pressable onPress={() => setAddPartido((v) => !v)}><Text style={st.acao}>{addPartido ? 'Fechar' : 'Adicionar'}</Text></Pressable>
        } />
        {addPartido ? (
          <View style={st.picker}>
            {partidosRestantes.length ? partidosRestantes.map((p) => (
              <Pressable key={p} onPress={() => salvarPartidos([...partidos, p])} style={st.pickerChip}>
                <Icon name="plus" size={12} color={cor.sky} /><Text style={st.pickerChipTxt}>{p}</Text>
              </Pressable>
            )) : <Text style={st.vazioMini}>Você já segue todos os partidos da lista.</Text>}
          </View>
        ) : null}
        {partidos.length ? (
          <Card padding={0}>
            {partidos.map((p, i) => (
              <View key={p}>
                <View style={st.linha}>
                  <Pressable style={st.linhaMain} onPress={() => router.push({ pathname: '/partido/[sigla]', params: { sigla: p } })}>
                    <Monogram sigla={p} size={40} color={PARTIDO_COR[p] ?? cor.navy} />
                    <Text style={st.linhaNome}>{p}</Text>
                    <Icon name="chevR" size={16} color={cor.mutedSoft} />
                  </Pressable>
                  <Pressable onPress={() => salvarPartidos(partidos.filter((x) => x !== p))} hitSlop={8} style={st.remover}>
                    <Icon name="x" size={15} color={cor.mutedSoft} />
                  </Pressable>
                </View>
                {i < partidos.length - 1 ? <Divider inset={66} /> : null}
              </View>
            ))}
          </Card>
        ) : <EmptyMini texto="Nenhum partido ainda. Toque em Adicionar." />}

        {/* Follow-based (futuro com o Feed) */}
        <View style={{ height: 20 }} />
        <SectionHeader title="Parlamentares e proposições" />
        <View style={st.empty}>
          <View style={st.emptyIcon}><Icon name="heart" size={18} color={cor.sky} /></View>
          <Text style={st.emptyTit}>Seguir chega junto do Feed</Text>
          <Text style={st.emptyTxt}>
            Em breve você vai seguir parlamentares e proposições direto no perfil — eles aparecem aqui
            com alertas de novidades.
          </Text>
        </View>
      </ScrollView>

      <BottomNav active="interesses" />
    </View>
  );
}

function EmptyMini({ texto }: { texto: string }) {
  const { st } = useTemaEstilos(criarSt);
  return <Text style={st.vazio}>{texto}</Text>;
}

const criarSt = (cor: Tema) => StyleSheet.create({
  h1: { fontSize: 26, fontFamily: fonte.xb, color: cor.texto, letterSpacing: -0.5, marginTop: 4 },
  sub: { marginTop: 2, fontSize: 12.5, fontFamily: fonte.r, color: cor.muted },
  acao: { fontFamily: fonte.b, fontSize: 12, color: cor.sky },
  chipsWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 4 },
  chip: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 12, paddingVertical: 8, borderRadius: 9999, backgroundColor: cor.light },
  chipTxt: { fontFamily: fonte.sb, fontSize: 12.5, color: cor.texto },
  picker: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 12, padding: 12, borderRadius: raio.card, borderWidth: 1, borderColor: cor.border, backgroundColor: cor.cartao },
  pickerChip: { flexDirection: 'row', alignItems: 'center', gap: 5, paddingHorizontal: 11, paddingVertical: 7, borderRadius: 9999, backgroundColor: cor.cartao, borderWidth: 1, borderStyle: 'dashed', borderColor: cor.borderStrong },
  pickerChipTxt: { fontFamily: fonte.b, fontSize: 12, color: cor.sky },
  linha: { flexDirection: 'row', alignItems: 'center' },
  linhaMain: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 11, paddingLeft: 12 },
  linhaNome: { flex: 1, fontFamily: fonte.b, fontSize: 14, color: cor.texto },
  remover: { paddingHorizontal: 14, paddingVertical: 12 },
  vazio: { marginTop: 4, fontFamily: fonte.r, fontSize: 12.5, color: cor.mutedSoft },
  vazioMini: { fontFamily: fonte.r, fontSize: 12, color: cor.mutedSoft },
  empty: { alignItems: 'center', paddingVertical: 22, paddingHorizontal: 16 },
  emptyIcon: { width: 44, height: 44, borderRadius: 9999, backgroundColor: cor.light, alignItems: 'center', justifyContent: 'center', marginBottom: 10 },
  emptyTit: { fontFamily: fonte.b, fontSize: 14, color: cor.texto },
  emptyTxt: { marginTop: 5, fontFamily: fonte.r, fontSize: 12.5, color: cor.muted, textAlign: 'center', lineHeight: 18 },
});
