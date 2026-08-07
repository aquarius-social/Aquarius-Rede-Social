import { useEffect, useState } from 'react';
import { View, Text, ScrollView, Pressable, StyleSheet } from 'react-native';
import { Link } from 'expo-router';
import { contagens, type Contagens } from '../lib/dados';
import { cor, raio } from '../lib/tema';
import { Avatar, Icon, BottomNav } from '../components/base';

type IconeEnt = 'users' | 'flag' | 'building' | 'star' | 'doc';

function EntCard({ icon, cor: c, titulo, sub, href, wide }: {
  icon: IconeEnt; cor: string; titulo: string; sub: string; href?: string; wide?: boolean;
}) {
  const conteudo = (
    <View style={[st.entCard, wide && { width: '100%' }]}>
      <View style={[st.entIcon, { backgroundColor: c }]}>
        <Icon name={icon} size={20} color={cor.white} />
      </View>
      <Text style={st.entTitulo}>{titulo}</Text>
      <Text style={st.entSub}>{sub}</Text>
    </View>
  );
  if (!href) return <View style={[st.cell, wide && { width: '100%' }]}>{conteudo}</View>;
  return (
    <Link href={href} asChild>
      <Pressable style={[st.cell, wide && { width: '100%' }]}>{conteudo}</Pressable>
    </Link>
  );
}

export default function Explorar() {
  const [c, setC] = useState<Contagens | null>(null);
  useEffect(() => { contagens().then(setC).catch(() => {}); }, []);

  return (
    <View style={{ flex: 1, backgroundColor: cor.surface }}>
      {/* Header */}
      <View style={st.header}>
        <Text style={st.marca}>AQUARIUS</Text>
        <Avatar nome="José Carvalho" size={32} />
      </View>

      <ScrollView contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 100 }}>
        <Text style={st.eyebrow}>57ª LEGISLATURA</Text>
        <Text style={st.h1}>Explore o Congresso.</Text>

        <View style={st.grid}>
          <EntCard icon="users" cor={cor.navy} titulo="Parlamentares"
            sub={c ? `${c.parlamentares} no exercício` : '…'} href="/listagem/parlamentares" />
          <EntCard icon="flag" cor={cor.blue} titulo="Partidos"
            sub={c ? `${c.partidos} com bancada` : '…'} href="/listagem/partidos" />
          <EntCard icon="building" cor={cor.sky} titulo="Comissões" sub="em breve" href="/listagem/comissoes" />
          <EntCard icon="star" cor={cor.skySoft} titulo="Frentes" sub="em breve" href="/listagem/frentes" />
          <EntCard icon="doc" cor={cor.muted} titulo="Proposições" sub="em breve · área legislativa" href="/listagem/proposicoes" wide />
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

const st = StyleSheet.create({
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 16, paddingTop: 14, paddingBottom: 12,
    borderBottomWidth: 1, borderBottomColor: cor.border, backgroundColor: cor.surface,
  },
  marca: { fontSize: 18, fontWeight: '800', color: cor.navy, letterSpacing: 1 },
  eyebrow: { marginTop: 16, fontSize: 11.5, fontWeight: '700', color: cor.mutedSoft, letterSpacing: 1.4 },
  h1: { fontSize: 30, fontWeight: '800', color: cor.navy, letterSpacing: -0.6, marginTop: 4, marginBottom: 18 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  cell: { width: '47%', flexGrow: 1 },
  entCard: {
    backgroundColor: cor.white, borderRadius: raio.cardGrande, borderWidth: 1, borderColor: cor.border,
    padding: 16, minHeight: 116, justifyContent: 'flex-start',
  },
  entIcon: { width: 40, height: 40, borderRadius: raio.cardPequeno, alignItems: 'center', justifyContent: 'center', marginBottom: 14 },
  entTitulo: { fontSize: 16, fontWeight: '800', color: cor.navy },
  entSub: { fontSize: 12.5, color: cor.muted, marginTop: 3 },
  nota: { marginTop: 20, fontSize: 11.5, color: cor.mutedSoft, lineHeight: 17, fontStyle: 'italic' },
});
