import { useEffect, useState } from 'react';
import { View, Text, ScrollView, Pressable, StyleSheet, type ViewStyle } from 'react-native';
import { useRouter } from 'expo-router';
import { contagens, type Contagens } from '../lib/dados';
import { useAuth } from '../lib/auth';
import { raio, fonte, type Tema } from '../lib/tema';
import { useTemaEstilos } from '../lib/theme';
import { Icon, BottomNav } from '../components/base';
import { AqHeader } from '../components/header';

type IconeEnt = 'users' | 'flag' | 'building' | 'star' | 'doc';

const MESES = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ'];

function EntCard({ icon, cor: c, titulo, sub, tipo, wide }: {
  icon: IconeEnt; cor: string; titulo: string; sub: string; tipo?: string; wide?: boolean;
}) {
  const { cor, st } = useTemaEstilos(criarSt);
  const router = useRouter();
  const cellStyle = StyleSheet.flatten([st.cell, wide && { width: '100%' as const }]) as ViewStyle;
  const conteudo = (
    <View style={st.entCard}>
      <View style={[st.entIcon, { backgroundColor: c }]}>
        <Icon name={icon} size={20} color={cor.white} />
      </View>
      <Text style={st.entTitulo}>{titulo}</Text>
      <Text style={st.entSub}>{sub}</Text>
    </View>
  );
  if (!tipo) return <View style={cellStyle}>{conteudo}</View>;
  // Navegação via router.push (não Link+asChild): no web, o Pressable virando <a>
  // pelo Link dispara "indexed property [0]" no react-dom. onPress evita o <a>.
  return (
    <Pressable style={cellStyle} onPress={() => router.push({ pathname: '/listagem/[tipo]', params: { tipo } })}>
      {conteudo}
    </Pressable>
  );
}

export default function Explorar() {
  const { cor, st } = useTemaEstilos(criarSt);
  const router = useRouter();
  const { session, prefs } = useAuth();
  const [c, setC] = useState<Contagens | null>(null);
  useEffect(() => { contagens().then(setC).catch(() => {}); }, []);

  // Data corrente no eyebrow (masthead), como no protótipo "57ª LEGISLATURA · 23 MAI 2026".
  const hoje = new Date();
  const dataHoje = `${hoje.getDate()} ${MESES[hoje.getMonth()]} ${hoje.getFullYear()}`;

  return (
    <View style={{ flex: 1, backgroundColor: cor.surface }}>
      <AqHeader variant="home" />

      <ScrollView contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 100 }}>
        <Text style={st.eyebrow}>57ª LEGISLATURA · {dataHoje}</Text>
        <Text style={st.h1}>Explore o Congresso.</Text>

        <View style={st.grid}>
          <EntCard icon="users" cor={cor.navy} titulo="Parlamentares"
            sub={c ? `${c.parlamentares} ativos` : '…'} tipo="parlamentares" />
          <EntCard icon="flag" cor={cor.blue} titulo="Partidos"
            sub={c ? `${c.partidos} com bancada` : '…'} tipo="partidos" />
          <EntCard icon="building" cor={cor.sky} titulo="Comissões"
            sub={c ? `${c.comissoes} colegiados` : '…'} tipo="comissoes" />
          <EntCard icon="star" cor={cor.skySoft} titulo="Frentes"
            sub={c ? `${c.frentes} frentes` : '…'} tipo="frentes" />
          <EntCard icon="doc" cor={cor.muted} titulo="Proposições" sub="em breve · área legislativa" tipo="proposicoes" wide />
        </View>

        <Text style={st.nota}>
          As seções "Em destaque" e "Em votação" do protótipo dependem de dados que ainda não ingerimos
          (uso/votações) — entram quando essas áreas existirem. Rankings são gerados pelo Prometeus sob demanda.
        </Text>
      </ScrollView>

      <BottomNav active="explorar" />
    </View>
  );
}

const criarSt = (cor: Tema) => StyleSheet.create({
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 16, paddingTop: 14, paddingBottom: 12,
    borderBottomWidth: 1, borderBottomColor: cor.border, backgroundColor: cor.surface,
  },
  eyebrow: { marginTop: 16, fontSize: 11.5, fontFamily: fonte.b, color: cor.mutedSoft, letterSpacing: 1.4 },
  h1: { fontSize: 30, fontFamily: fonte.xb, color: cor.texto, letterSpacing: -0.6, marginTop: 4, marginBottom: 18 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  cell: { width: '47%', flexGrow: 1 },
  entCard: {
    backgroundColor: cor.cartao, borderRadius: raio.cardGrande, borderWidth: 1, borderColor: cor.border,
    padding: 16, minHeight: 116, justifyContent: 'flex-start',
  },
  entIcon: { width: 40, height: 40, borderRadius: raio.cardPequeno, alignItems: 'center', justifyContent: 'center', marginBottom: 14 },
  entTitulo: { fontSize: 16, fontFamily: fonte.xb, color: cor.texto },
  entSub: { fontSize: 12.5, color: cor.muted, marginTop: 3 },
  nota: { marginTop: 20, fontSize: 11.5, color: cor.mutedSoft, lineHeight: 17, fontStyle: 'italic' },
});
