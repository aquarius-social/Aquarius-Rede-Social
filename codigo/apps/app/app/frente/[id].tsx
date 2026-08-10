import { useEffect, useState } from 'react';
import { View, Text, ScrollView, ActivityIndicator, StyleSheet } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { obterFrente, type Frente } from '../../lib/dados';
import { frescor } from '../../lib/formato';
import { raio, fonte, type Tema } from '../../lib/tema';
import { useTemaEstilos } from '../../lib/theme';
import { Cover, Tag, Card, SectionHeader, Divider, Icon, FollowButton } from '../../components/base';

// Composição e atividade da frente dependem de dados ainda NÃO ingeridos.
const PENDENTES = [
  { icon: 'users', label: 'Composição', nota: 'parlamentares que assinam a frente' },
  { icon: 'star', label: 'Atividade', nota: 'atuação e proposições relacionadas' },
] as const;

export default function FrenteScreen() {
  const { cor, st } = useTemaEstilos(criarSt);
  const { id } = useLocalSearchParams<{ id: string }>();
  const [f, setF] = useState<Frente | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let vivo = true;
    obterFrente(id)
      .then((r) => { if (vivo) setF(r); })
      .catch((e) => { if (vivo) setErro(e?.message ?? 'Falha ao carregar'); })
      .finally(() => { if (vivo) setCarregando(false); });
    return () => { vivo = false; };
  }, [id]);

  if (carregando) return <View style={st.centro}><ActivityIndicator color={cor.blue} /></View>;
  if (erro || !f) return <View style={st.centro}><Text style={st.erro}>{erro ?? 'Frente não encontrada.'}</Text></View>;

  return (
    <View style={{ flex: 1, backgroundColor: cor.surface }}>
      <ScrollView contentContainerStyle={{ paddingBottom: 32 }}>
        <View style={{ backgroundColor: cor.cartao }}>
          <Cover height={88} base={cor.sky} />
          <View style={{ paddingHorizontal: 16, paddingBottom: 16, marginTop: -30 }}>
            <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 14 }}>
              <View style={st.iconRing}><View style={st.icon}><Icon name="star" size={30} color={cor.white} /></View></View>
              <View style={{ flex: 1, paddingBottom: 6 }}>
                <Tag tone="sky">Frente parlamentar</Tag>
              </View>
            </View>
            <Text style={st.nome}>{f.nome}</Text>
            <Text style={st.fonte}>Fonte: {f.source} · {frescor(f.synced_at)}</Text>
            <View style={{ flexDirection: 'row', marginTop: 12 }}>
              <FollowButton tipo="frente" refId={f.id} rotulo={f.nome} />
            </View>
          </View>
        </View>

        <View style={{ padding: 14 }}>
          <SectionHeader title="Ainda não disponível" sub="Só temos a identidade oficial desta frente nesta base. A composição (quem assina) é dado eleitoral/legislativo ainda não ingerido." />
          <Card padding={0}>
            {PENDENTES.map((p, i, arr) => (
              <View key={p.label}>
                <View style={st.pendLinha}>
                  <View style={st.pendIcon}><Icon name={p.icon} size={16} color={cor.mutedSoft} /></View>
                  <View style={{ flex: 1 }}>
                    <Text style={st.pendLabel}>{p.label}</Text>
                    <Text style={st.pendNota}>{p.nota}</Text>
                  </View>
                  <Tag tone="muted">em breve</Tag>
                </View>
                {i < arr.length - 1 ? <Divider inset={58} /> : null}
              </View>
            ))}
          </Card>
        </View>
      </ScrollView>
    </View>
  );
}

const criarSt = (cor: Tema) => StyleSheet.create({
  centro: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: cor.surface, padding: 24 },
  erro: { color: cor.muted, textAlign: 'center' },
  iconRing: { borderRadius: 9999, borderWidth: 3, borderColor: cor.white, backgroundColor: cor.white },
  icon: { width: 66, height: 66, borderRadius: 33, backgroundColor: cor.skySoft, alignItems: 'center', justifyContent: 'center' },
  nome: { marginTop: 12, fontSize: 19, fontFamily: fonte.xb, color: cor.texto, letterSpacing: -0.3, lineHeight: 25 },
  fonte: { marginTop: 8, fontSize: 11.5, color: cor.mutedSoft },
  pendLinha: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14 },
  pendIcon: { width: 34, height: 34, borderRadius: raio.cardPequeno, backgroundColor: cor.light, alignItems: 'center', justifyContent: 'center' },
  pendLabel: { fontSize: 14, fontFamily: fonte.b, color: cor.texto },
  pendNota: { fontSize: 12, color: cor.muted, marginTop: 2 },
});
