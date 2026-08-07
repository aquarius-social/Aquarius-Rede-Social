import { useEffect, useMemo, useState } from 'react';
import { View, Text, TextInput, ScrollView, FlatList, Pressable, ActivityIndicator, StyleSheet } from 'react-native';
import { useLocalSearchParams, Link } from 'expo-router';
import { listarParlamentares, listarPartidos, type Parlamentar, type Partido } from '../../lib/dados';
import { cor, raio, fonte } from '../../lib/tema';
import { Avatar, Monogram, PartyChip, SituacaoBadge, Icon } from '../../components/base';
import { PARTIDO_COR } from '../../lib/mock';

const norm = (s: string) => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');

export default function Listagem() {
  const { tipo } = useLocalSearchParams<{ tipo: string }>();
  if (tipo === 'partidos') return <ListaPartidos />;
  if (tipo === 'parlamentares') return <ListaParlamentares />;
  return (
    <View style={st.centro}>
      <Text style={st.emBreveTit}>Em breve</Text>
      <Text style={st.emBreveTxt}>
        {tipo === 'proposicoes'
          ? 'Proposições precisam da área legislativa reingerida (fora da base de dinheiro atual).'
          : 'Esta área ainda não foi ingerida nesta base.'}
      </Text>
    </View>
  );
}

/* ── Chips de filtro ── */
function ChipRow({ opcoes, sel, onSel }: { opcoes: { v: string | null; l: string }[]; sel: string | null; onSel: (v: string | null) => void }) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 8 }} contentContainerStyle={{ gap: 6 }}>
      {opcoes.map((o) => {
        const s = o.v === sel;
        return (
          <Pressable key={o.l} onPress={() => onSel(o.v)} style={[st.chip, { backgroundColor: s ? cor.navy : cor.white, borderColor: s ? cor.navy : cor.border }]}>
            <Text style={{ color: s ? cor.white : cor.navy, fontFamily: fonte.sb, fontSize: 11.5 }}>{o.l}</Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

/* ── PARLAMENTARES (com filtros) ── */
function ListaParlamentares() {
  const [todos, setTodos] = useState<Parlamentar[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [busca, setBusca] = useState('');
  const [casa, setCasa] = useState<string | null>(null);
  const [situacao, setSituacao] = useState<string | null>(null);
  const [uf, setUf] = useState<string | null>(null);
  const [partido, setPartido] = useState<string | null>(null);

  useEffect(() => { listarParlamentares().then(setTodos).finally(() => setCarregando(false)); }, []);

  const ufs = useMemo(() => [...new Set(todos.map((p) => p.uf_atual).filter(Boolean))].sort() as string[], [todos]);
  const partidos = useMemo(() => [...new Set(todos.map((p) => p.partido_sigla_atual).filter(Boolean))].sort() as string[], [todos]);

  const lista = todos.filter((p) => {
    if (busca && !norm(p.nome).includes(norm(busca))) return false;
    if (casa && p.casa_atual !== casa) return false;
    if (situacao && p.situacao !== situacao) return false;
    if (uf && p.uf_atual !== uf) return false;
    if (partido && p.partido_sigla_atual !== partido) return false;
    return true;
  });

  return (
    <View style={st.tela}>
      <TextInput style={st.busca} placeholder="Buscar por nome…" placeholderTextColor={cor.mutedSoft} value={busca} onChangeText={setBusca} autoCorrect={false} />
      <ChipRow sel={casa} onSel={setCasa} opcoes={[{ v: null, l: 'Todas as casas' }, { v: 'camara', l: 'Câmara' }, { v: 'senado', l: 'Senado' }]} />
      <ChipRow sel={situacao} onSel={setSituacao} opcoes={[
        { v: null, l: 'Todas as situações' }, { v: 'em_exercicio', l: 'Em exercício' },
        { v: 'licenciado', l: 'Licenciado' }, { v: 'suplente_em_exercicio', l: 'Suplente' }]} />
      <ChipRow sel={uf} onSel={setUf} opcoes={[{ v: null, l: 'Todas UFs' }, ...ufs.map((u) => ({ v: u, l: u }))]} />
      <ChipRow sel={partido} onSel={setPartido} opcoes={[{ v: null, l: 'Todos partidos' }, ...partidos.map((s) => ({ v: s, l: s }))]} />

      {carregando ? (
        <ActivityIndicator color={cor.blue} style={{ marginTop: 32 }} />
      ) : (
        <FlatList
          data={lista}
          keyExtractor={(p) => p.id}
          contentContainerStyle={{ paddingVertical: 8, paddingBottom: 24 }}
          ListHeaderComponent={<Text style={st.contador}>{lista.length} parlamentar{lista.length !== 1 ? 'es' : ''}</Text>}
          ListEmptyComponent={<Text style={st.vazio}>Nenhum parlamentar com esses filtros.</Text>}
          renderItem={({ item }) => (
            <Link href={{ pathname: '/parlamentar/[id]', params: { id: item.id } }} asChild>
              <Pressable style={st.linha}>
                <Avatar nome={item.nome} size={44} />
                <View style={{ flex: 1, gap: 5 }}>
                  <Text style={st.nome}>{item.nome}</Text>
                  <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
                    <PartyChip sigla={item.partido_sigla_atual} uf={item.uf_atual} />
                    <SituacaoBadge situacao={item.situacao} />
                  </View>
                </View>
                <Icon name="chevR" size={16} color={cor.mutedSoft} />
              </Pressable>
            </Link>
          )}
        />
      )}
    </View>
  );
}

/* ── PARTIDOS ── */
function ListaPartidos() {
  const [todos, setTodos] = useState<Partido[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [busca, setBusca] = useState('');
  useEffect(() => { listarPartidos().then(setTodos).finally(() => setCarregando(false)); }, []);
  const lista = todos.filter((p) => !busca || norm(p.sigla_atual + ' ' + p.nome_atual).includes(norm(busca)));

  return (
    <View style={st.tela}>
      <TextInput style={st.busca} placeholder="Buscar partido…" placeholderTextColor={cor.mutedSoft} value={busca} onChangeText={setBusca} autoCorrect={false} />
      {carregando ? (
        <ActivityIndicator color={cor.blue} style={{ marginTop: 32 }} />
      ) : (
        <FlatList
          data={lista}
          keyExtractor={(p) => p.id}
          contentContainerStyle={{ paddingVertical: 8, paddingBottom: 24 }}
          ListEmptyComponent={<Text style={st.vazio}>Nenhum partido.</Text>}
          renderItem={({ item }) => (
            <Link href={{ pathname: '/partido/[sigla]', params: { sigla: item.sigla_atual } }} asChild>
              <Pressable style={st.linha}>
                <Monogram sigla={item.sigla_atual} size={44} color={PARTIDO_COR[item.sigla_atual] ?? cor.navy} />
                <View style={{ flex: 1 }}>
                  <Text style={st.nome}>{item.sigla_atual}</Text>
                  <Text style={st.sub} numberOfLines={1}>{item.nome_atual}{item.numero_urna ? ` · nº ${item.numero_urna}` : ''}</Text>
                </View>
                <Icon name="chevR" size={16} color={cor.mutedSoft} />
              </Pressable>
            </Link>
          )}
        />
      )}
    </View>
  );
}

const st = StyleSheet.create({
  tela: { flex: 1, backgroundColor: cor.surface, paddingHorizontal: 14, paddingTop: 12 },
  centro: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: cor.surface, padding: 32 },
  emBreveTit: { fontSize: 18, fontFamily: fonte.xb, color: cor.navy },
  emBreveTxt: { fontSize: 13, color: cor.muted, textAlign: 'center', marginTop: 8, lineHeight: 19 },
  busca: { backgroundColor: cor.white, borderRadius: raio.input, borderWidth: 1, borderColor: cor.border, paddingHorizontal: 14, paddingVertical: 11, fontSize: 15, color: cor.ink, marginBottom: 10 },
  chip: { paddingHorizontal: 11, paddingVertical: 6, borderRadius: 9999, borderWidth: 1 },
  contador: { fontSize: 11.5, color: cor.mutedSoft, fontFamily: fonte.b, letterSpacing: 0.4, marginBottom: 6, paddingLeft: 2, textTransform: 'uppercase' },
  linha: { flexDirection: 'row', alignItems: 'center', gap: 12, backgroundColor: cor.white, borderRadius: raio.card, borderWidth: 1, borderColor: cor.border, padding: 12, marginBottom: 8 },
  nome: { fontSize: 15, fontFamily: fonte.b, color: cor.navy },
  sub: { fontSize: 12.5, color: cor.muted, marginTop: 3 },
  vazio: { color: cor.muted, marginTop: 32, textAlign: 'center' },
});
