import { useEffect, useState } from 'react';
import { View, Text, ScrollView, ActivityIndicator, StyleSheet } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { obterComissao, type Comissao } from '../../lib/dados';
import { frescor } from '../../lib/formato';
import { raio, fonte, type Tema } from '../../lib/tema';
import { useTemaEstilos } from '../../lib/theme';
import { Cover, Monogram, Tag, Card, SectionHeader, Divider, Icon, FollowButton } from '../../components/base';

// Seções do protótipo (mesa/membros/agenda/votações) que dependem de dados ainda
// NÃO ingeridos (⛔Pro/⛔fonte). Mostradas rotuladas, sem inventar conteúdo.
const PENDENTES = [
  { icon: 'users', label: 'Composição e mesa diretora', nota: 'quem integra e preside' },
  { icon: 'cal', label: 'Agenda de reuniões', nota: 'pauta e calendário' },
  { icon: 'check', label: 'Votações', nota: 'deliberações do colegiado' },
  { icon: 'doc', label: 'Emendas de comissão', nota: 'destino do recurso' },
] as const;

export default function ComissaoScreen() {
  const { cor, st } = useTemaEstilos(criarSt);
  const { id } = useLocalSearchParams<{ id: string }>();
  const [c, setC] = useState<Comissao | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let vivo = true;
    obterComissao(id)
      .then((r) => { if (vivo) setC(r); })
      .catch((e) => { if (vivo) setErro(e?.message ?? 'Falha ao carregar'); })
      .finally(() => { if (vivo) setCarregando(false); });
    return () => { vivo = false; };
  }, [id]);

  if (carregando) return <View style={st.centro}><ActivityIndicator color={cor.blue} /></View>;
  if (erro || !c) return <View style={st.centro}><Text style={st.erro}>{erro ?? 'Comissão não encontrada.'}</Text></View>;

  return (
    <View style={{ flex: 1, backgroundColor: cor.surface }}>
      <ScrollView contentContainerStyle={{ paddingBottom: 32 }}>
        <View style={{ backgroundColor: cor.cartao }}>
          <Cover height={88} />
          <View style={{ paddingHorizontal: 16, paddingBottom: 16, marginTop: -30 }}>
            <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 14 }}>
              <View style={st.monoRing}><Monogram sigla={c.sigla ?? c.nome.slice(0, 2)} size={72} color={cor.navy} /></View>
              <View style={{ flex: 1, paddingBottom: 6, flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
                <Tag tone="navy">Comissão</Tag>
                {c.sigla ? <Tag tone="muted">{c.sigla}</Tag> : null}
              </View>
            </View>
            <Text style={st.nome}>{c.nome}</Text>
            <Text style={st.fonte}>Fonte: {c.source} · {frescor(c.synced_at)}</Text>
            <View style={{ flexDirection: 'row', marginTop: 12 }}>
              <FollowButton tipo="comissao" refId={c.id} rotulo={c.sigla ?? c.nome} meta={{ nome: c.nome }} />
            </View>
          </View>
        </View>

        <View style={{ padding: 14 }}>
          <SectionHeader title="Ainda não disponível" sub="Só temos a identidade oficial desta comissão nesta base. O que falta depende de reingestão das áreas legislativa e de composição." />
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
  monoRing: { borderRadius: 9999, borderWidth: 3, borderColor: cor.cartao, backgroundColor: cor.cartao },
  nome: { marginTop: 12, fontSize: 20, fontFamily: fonte.xb, color: cor.texto, letterSpacing: -0.3, lineHeight: 26 },
  fonte: { marginTop: 8, fontSize: 11.5, color: cor.mutedSoft },
  pendLinha: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14 },
  pendIcon: { width: 34, height: 34, borderRadius: raio.cardPequeno, backgroundColor: cor.light, alignItems: 'center', justifyContent: 'center' },
  pendLabel: { fontSize: 14, fontFamily: fonte.b, color: cor.texto },
  pendNota: { fontSize: 12, color: cor.muted, marginTop: 2 },
});
