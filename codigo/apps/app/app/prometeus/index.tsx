import { View, Text, Pressable, ScrollView, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { raio, fonte, type Tema } from '../../lib/tema';
import { useTemaEstilos } from '../../lib/theme';
import { Icon, SectionHeader, BottomNav, type IconName } from '../../components/base';

const SUGESTOES: { t: string; icon: IconName }[] = [
  { t: 'Como votou meu deputado em 2025?', icon: 'doc' },
  { t: 'Emendas no meu município', icon: 'search' },
  { t: 'Relatório semanal do Senado', icon: 'download' },
  { t: 'Compare gastos do PT e do PL', icon: 'building' },
];

export default function PrometeusLista() {
  const { cor, st } = useTemaEstilos(criarSt);
  const router = useRouter();
  const abrir = (prompt?: string) =>
    router.push({ pathname: '/prometeus/chat', params: prompt ? { prompt } : {} });

  return (
    <View style={{ flex: 1, backgroundColor: cor.surface }}>
      <ScrollView contentContainerStyle={{ paddingBottom: 110 }}>
        {/* Cabeçalho */}
        <View style={st.head}>
          <View style={{ flex: 1 }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <View style={st.badge}><Icon name="spark" size={15} color={cor.white} /></View>
              <Text style={st.titulo}>Prometeus</Text>
            </View>
            <Text style={st.sub}>IA conversacional · acesso direto ao banco do Congresso</Text>
          </View>
          <Pressable onPress={() => abrir()} style={st.novo}><Icon name="plus" size={18} color={cor.white} stroke={2.5} /></Pressable>
        </View>

        {/* Sugestões */}
        <View style={{ paddingHorizontal: 16, marginTop: 6 }}>
          <SectionHeader title="Sugestões" />
        </View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: 16, gap: 8 }}>
          {SUGESTOES.map((s) => (
            <Pressable key={s.t} onPress={() => abrir(s.t)} style={st.sugCard}>
              <View style={st.sugIcon}><Icon name={s.icon} size={14} color={cor.texto} /></View>
              <Text style={st.sugTxt}>{s.t}</Text>
            </Pressable>
          ))}
        </ScrollView>

        {/* Conversas (histórico ainda não persistido) */}
        <View style={{ paddingHorizontal: 16, marginTop: 20 }}>
          <SectionHeader title="Conversas" sub="O histórico chega junto do agente" />
          <View style={st.empty}>
            <View style={st.emptyIcon}><Icon name="spark" size={20} color={cor.texto} /></View>
            <Text style={st.emptyTit}>Nenhuma conversa ainda</Text>
            <Text style={st.emptyTxt}>Toque em uma sugestão ou no + para começar. O Prometeus responde com dados reais do banco — sempre com fonte.</Text>
          </View>
        </View>
      </ScrollView>

      <BottomNav active="prometeus" />
    </View>
  );
}

const criarSt = (cor: Tema) => StyleSheet.create({
  head: { flexDirection: 'row', alignItems: 'flex-end', gap: 12, paddingHorizontal: 16, paddingTop: 14 },
  badge: { width: 30, height: 30, borderRadius: 9999, backgroundColor: cor.navy, alignItems: 'center', justifyContent: 'center' },
  titulo: { fontFamily: fonte.xb, fontSize: 24, color: cor.texto, letterSpacing: -0.5 },
  sub: { marginTop: 8, fontFamily: fonte.m, fontSize: 12, color: cor.muted },
  novo: { width: 38, height: 38, borderRadius: 9999, backgroundColor: cor.navy, alignItems: 'center', justifyContent: 'center' },
  sugCard: { width: 172, padding: 14, borderRadius: raio.card, backgroundColor: cor.cartao, borderWidth: 1, borderColor: cor.border, gap: 8 },
  sugIcon: { width: 28, height: 28, borderRadius: 8, backgroundColor: cor.light, alignItems: 'center', justifyContent: 'center' },
  sugTxt: { fontFamily: fonte.sb, fontSize: 12.5, color: cor.texto, lineHeight: 17 },
  empty: { alignItems: 'center', paddingVertical: 26, paddingHorizontal: 16 },
  emptyIcon: { width: 46, height: 46, borderRadius: 9999, backgroundColor: cor.light, alignItems: 'center', justifyContent: 'center', marginBottom: 12 },
  emptyTit: { fontFamily: fonte.b, fontSize: 14.5, color: cor.texto },
  emptyTxt: { marginTop: 6, fontFamily: fonte.r, fontSize: 12.5, color: cor.muted, textAlign: 'center', lineHeight: 18, maxWidth: 300 },
});
