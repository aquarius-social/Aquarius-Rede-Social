import { useEffect, useState } from 'react';
import { View, Text, Pressable, ScrollView, ActivityIndicator, Linking, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { destaquesFeed, type FeedPost } from '../lib/dados';
import { useAuth } from '../lib/auth';
import { reais, frescor, URL_EMENDAS_CONSULTA } from '../lib/formato';
import { raio, fonte, type Tema } from '../lib/tema';
import { useTemaEstilos } from '../lib/theme';
import { Avatar, Icon, PartyChip, Tag, BottomNav } from '../components/base';
import { AqHeader } from '../components/header';

type Aba = 'voce' | 'seguindo';

export default function Feed() {
  const { cor, st } = useTemaEstilos(criarSt);
  const router = useRouter();
  const { session, prefs } = useAuth();
  const [posts, setPosts] = useState<FeedPost[] | null>(null);
  const [aba, setAba] = useState<Aba>('voce');

  useEffect(() => { destaquesFeed().then(setPosts).catch(() => setPosts([])); }, []);

  return (
    <View style={{ flex: 1, backgroundColor: cor.surface }}>
      <AqHeader variant="home" bell />

      {/* Abas */}
      <View style={st.tabs}>
        <TabBtn label="Para Você" on={aba === 'voce'} onPress={() => setAba('voce')} />
        <TabBtn label="Seguindo" on={aba === 'seguindo'} onPress={() => setAba('seguindo')} />
      </View>

      {aba === 'seguindo' ? (
        <Seguindo router={router} />
      ) : posts === null ? (
        <ActivityIndicator color={cor.blue} style={{ marginTop: 40 }} />
      ) : (
        <ScrollView contentContainerStyle={{ padding: 14, paddingBottom: 110 }}>
          <View style={st.nota}>
            <Icon name="info" size={14} color={cor.sky} />
            <Text style={st.notaTxt}>
              Destaques factuais do dinheiro público (maiores emendas), direto da fonte oficial. Os posts
              editoriais gerados pelo Prometeus entram quando o agente for ligado.
            </Text>
          </View>
          {posts.map((p) => <PostCard key={p.id} post={p} router={router} />)}
          <View style={st.fimRow}>
            <View style={st.pontoOk} />
            <Text style={st.fimTxt}>Você está em dia · fonte: Portal da Transparência</Text>
          </View>
        </ScrollView>
      )}

      <BottomNav active="feed" />
    </View>
  );
}

function TabBtn({ label, on, onPress }: { label: string; on: boolean; onPress: () => void }) {
  const { cor, st } = useTemaEstilos(criarSt);
  return (
    <Pressable onPress={onPress} style={st.tab}>
      <Text style={[st.tabTxt, on && { color: cor.texto, fontFamily: fonte.xb }]}>{label}</Text>
      {on ? <View style={st.tabUnder} /> : null}
    </Pressable>
  );
}

function Seguindo({ router }: { router: ReturnType<typeof useRouter> }) {
  const { cor, st } = useTemaEstilos(criarSt);
  return (
    <View style={st.empty}>
      <View style={st.emptyIcon}><Icon name="heart" size={20} color={cor.sky} /></View>
      <Text style={st.emptyTit}>Seu feed de quem você segue</Text>
      <Text style={st.emptyTxt}>
        Escolha temas e partidos em Interesses — quando o sistema de "seguir" e o Prometeus chegarem,
        este feed mostra só o que é seu.
      </Text>
      <Pressable onPress={() => router.push('/interesses')} style={st.emptyCta}>
        <Text style={st.emptyCtaTxt}>Ir para Interesses</Text>
      </Pressable>
    </View>
  );
}

function PostCard({ post, router }: { post: FeedPost; router: ReturnType<typeof useRouter> }) {
  const { cor, st } = useTemaEstilos(criarSt);
  const perguntar = () => router.push({
    pathname: '/prometeus/chat',
    params: { prompt: `Explique a emenda de ${post.autorNome} de ${reais(post.valorEmpenhado)} para ${post.area}${post.local ? ' em ' + post.local : ''}.` },
  });
  return (
    <View style={st.card}>
      {/* Fonte + frescor */}
      <View style={st.fonteRow}>
        <View style={st.fonteBadge}><Text style={st.fonteBadgeTxt}>{post.fonte}</Text></View>
        <Text style={st.frescor}>{frescor(post.syncedAt)}</Text>
      </View>

      {/* Autor */}
      {post.autorId ? (
        <Pressable style={st.autor} onPress={() => router.push({ pathname: '/parlamentar/[id]', params: { id: post.autorId! } })}>
          <Avatar nome={post.autorNome} size={38} />
          <View style={{ flex: 1 }}>
            <Text style={st.autorNome}>{post.autorNome}</Text>
            <View style={{ flexDirection: 'row', marginTop: 3 }}>
              <PartyChip sigla={post.autorSigla} uf={post.autorUf} />
            </View>
          </View>
          <Text style={st.autorRole}>Autoria</Text>
        </Pressable>
      ) : null}

      <Text style={st.headline}>{post.headline}</Text>
      <Text style={st.body}>{post.body}</Text>

      {/* Payload da emenda */}
      <View style={st.payload}>
        <View style={{ flex: 1 }}>
          <Text style={st.payloadValor}>{reais(post.valorEmpenhado)}</Text>
          <Text style={st.payloadLabel}>EMPENHADO · {post.ano}</Text>
        </View>
        <View style={{ gap: 4, alignItems: 'flex-end' }}>
          <Tag tone="sky">{post.area}</Tag>
          {post.valorPago > 0 ? <Text style={st.pago}>{reais(post.valorPago)} pagos</Text> : <Text style={st.pagoZero}>ainda não pago</Text>}
        </View>
      </View>

      {/* Ações */}
      <View style={st.acoes}>
        <Pressable style={st.acaoBtn} onPress={() => Linking.openURL(URL_EMENDAS_CONSULTA)}>
          <Icon name="doc" size={14} color={cor.texto} />
          <Text style={st.acaoTxt}>Ver no Portal</Text>
        </Pressable>
        <Pressable style={[st.acaoBtn, st.acaoPrometeus]} onPress={perguntar}>
          <Icon name="spark" size={14} color={cor.white} />
          <Text style={[st.acaoTxt, { color: cor.white }]}>Perguntar ao Prometeus</Text>
        </Pressable>
      </View>
    </View>
  );
}

const criarSt = (cor: Tema) => StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 16, paddingTop: 14, paddingBottom: 10, borderBottomWidth: 1, borderBottomColor: cor.border, backgroundColor: cor.surface },
  bell: { width: 36, height: 36, borderRadius: 9999, borderWidth: 1, borderColor: cor.border, backgroundColor: cor.cartao, alignItems: 'center', justifyContent: 'center' },
  tabs: { flexDirection: 'row', paddingHorizontal: 10, borderBottomWidth: 1, borderBottomColor: cor.border, backgroundColor: cor.surface },
  tab: { paddingHorizontal: 13, paddingVertical: 12, alignItems: 'center' },
  tabTxt: { fontFamily: fonte.sb, fontSize: 13.5, color: cor.muted },
  tabUnder: { position: 'absolute', left: 13, right: 13, bottom: 0, height: 2.5, borderRadius: 9999, backgroundColor: cor.texto },
  nota: { flexDirection: 'row', gap: 8, alignItems: 'flex-start', padding: 12, marginBottom: 12, borderRadius: raio.card, backgroundColor: cor.light },
  notaTxt: { flex: 1, fontFamily: fonte.r, fontSize: 11.5, color: cor.muted, lineHeight: 16 },
  card: { backgroundColor: cor.cartao, borderRadius: raio.cardGrande, borderWidth: 1, borderColor: cor.border, padding: 14, marginBottom: 12 },
  fonteRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 },
  fonteBadge: { paddingHorizontal: 9, paddingVertical: 3, borderRadius: 9999, backgroundColor: cor.navy },
  fonteBadgeTxt: { fontFamily: fonte.b, fontSize: 9.5, color: cor.white, letterSpacing: 0.4, textTransform: 'uppercase' },
  frescor: { fontFamily: fonte.m, fontSize: 10.5, color: cor.mutedSoft },
  autor: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 10 },
  autorNome: { fontFamily: fonte.b, fontSize: 13.5, color: cor.texto },
  autorRole: { fontFamily: fonte.b, fontSize: 10, color: cor.mutedSoft, letterSpacing: 0.6, textTransform: 'uppercase' },
  headline: { fontFamily: fonte.xb, fontSize: 16.5, color: cor.texto, letterSpacing: -0.3, lineHeight: 22 },
  body: { marginTop: 6, fontFamily: fonte.r, fontSize: 13.5, color: cor.ink, lineHeight: 20 },
  payload: { flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: 12, padding: 12, borderRadius: raio.card, backgroundColor: cor.light },
  payloadValor: { fontFamily: fonte.xb, fontSize: 19, color: cor.texto, letterSpacing: -0.4 },
  payloadLabel: { marginTop: 3, fontFamily: fonte.b, fontSize: 9.5, color: cor.muted, letterSpacing: 0.8 },
  pago: { fontFamily: fonte.sb, fontSize: 11, color: cor.pos },
  pagoZero: { fontFamily: fonte.m, fontSize: 11, color: cor.mutedSoft },
  acoes: { flexDirection: 'row', gap: 8, marginTop: 12 },
  acaoBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 10, borderRadius: 9999, borderWidth: 1, borderColor: cor.border, backgroundColor: cor.cartao },
  acaoPrometeus: { backgroundColor: cor.navy, borderColor: cor.navy },
  acaoTxt: { fontFamily: fonte.b, fontSize: 12, color: cor.texto },
  fimRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 10 },
  pontoOk: { width: 6, height: 6, borderRadius: 9999, backgroundColor: cor.pos },
  fimTxt: { fontFamily: fonte.sb, fontSize: 11.5, color: cor.muted },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32 },
  emptyIcon: { width: 48, height: 48, borderRadius: 9999, backgroundColor: cor.light, alignItems: 'center', justifyContent: 'center', marginBottom: 12 },
  emptyTit: { fontFamily: fonte.b, fontSize: 15, color: cor.texto },
  emptyTxt: { marginTop: 6, fontFamily: fonte.r, fontSize: 13, color: cor.muted, textAlign: 'center', lineHeight: 19 },
  emptyCta: { marginTop: 16, paddingHorizontal: 18, paddingVertical: 11, borderRadius: 9999, backgroundColor: cor.navy },
  emptyCtaTxt: { fontFamily: fonte.b, fontSize: 13, color: cor.white },
});
