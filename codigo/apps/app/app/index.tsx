import { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  FlatList,
  Pressable,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { Link } from 'expo-router';
import { listarParlamentares, type Parlamentar } from '../lib/dados';
import { Avatar, PartyChip, SituacaoBadge } from '../components/base';
import { cor, raio } from '../lib/tema';

export default function ListaParlamentares() {
  const [busca, setBusca] = useState('');
  const [itens, setItens] = useState<Parlamentar[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async (q: string) => {
    setCarregando(true);
    setErro(null);
    try {
      setItens(await listarParlamentares(q));
    } catch (e: any) {
      setErro(e?.message ?? 'Falha ao carregar');
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => carregar(busca), 250);
    return () => clearTimeout(t);
  }, [busca, carregar]);

  return (
    <View style={estilo.tela}>
      <TextInput
        style={estilo.busca}
        placeholder="Buscar parlamentar…"
        placeholderTextColor={cor.mutedSoft}
        value={busca}
        onChangeText={setBusca}
        autoCorrect={false}
      />
      {erro ? (
        <Text style={estilo.erro}>{erro}</Text>
      ) : carregando ? (
        <ActivityIndicator color={cor.blue} style={{ marginTop: 32 }} />
      ) : (
        <FlatList
          data={itens}
          keyExtractor={(p) => p.id}
          contentContainerStyle={{ paddingBottom: 24 }}
          ListEmptyComponent={<Text style={estilo.vazio}>Nenhum parlamentar encontrado.</Text>}
          renderItem={({ item }) => (
            <Link href={{ pathname: '/parlamentar/[id]', params: { id: item.id } }} asChild>
              <Pressable style={estilo.linha}>
                <Avatar nome={item.nome} size={44} />
                <View style={{ flex: 1, gap: 5 }}>
                  <Text style={estilo.nome}>{item.nome}</Text>
                  <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
                    <PartyChip sigla={item.partido_sigla_atual} uf={item.uf_atual} />
                    <SituacaoBadge situacao={item.situacao} />
                  </View>
                </View>
                <Text style={estilo.seta}>›</Text>
              </Pressable>
            </Link>
          )}
        />
      )}
    </View>
  );
}

const estilo = StyleSheet.create({
  tela: { flex: 1, backgroundColor: cor.surface, paddingHorizontal: 14, paddingTop: 12 },
  busca: {
    backgroundColor: cor.white,
    borderRadius: raio.input ?? 10,
    borderWidth: 1,
    borderColor: cor.border,
    paddingHorizontal: 14,
    paddingVertical: 11,
    fontSize: 15,
    color: cor.ink,
    marginBottom: 10,
  },
  linha: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: cor.white,
    borderRadius: raio.card,
    borderWidth: 1,
    borderColor: cor.border,
    padding: 12,
    marginBottom: 8,
  },
  nome: { fontSize: 15, fontWeight: '700', color: cor.navy },
  sub: { fontSize: 12.5, color: cor.muted, marginTop: 2 },
  seta: { fontSize: 22, color: cor.mutedSoft, fontWeight: '700' },
  erro: { color: cor.neg, marginTop: 24, textAlign: 'center', paddingHorizontal: 20 },
  vazio: { color: cor.muted, marginTop: 32, textAlign: 'center' },
});
