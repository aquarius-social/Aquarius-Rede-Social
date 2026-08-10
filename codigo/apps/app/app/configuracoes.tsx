import { useState } from 'react';
import { View, Text, Pressable, ScrollView, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import Svg, { Circle } from 'react-native-svg';
import { useAuth } from '../lib/auth';
import { cor, raio, fonte } from '../lib/tema';
import { Avatar, Icon, Card, SectionHeader, Divider, Tag, type IconName } from '../components/base';

export default function Configuracoes() {
  const router = useRouter();
  const { session, prefs, sair } = useAuth();
  const [aviso, setAviso] = useState<string | null>(null);

  const email = session?.user?.email ?? '—';
  const nome = prefs.nome || email.split('@')[0] || 'Você';

  const campos = ['cep', 'idade', 'genero', 'escolaridade', 'renda', 'ocupacao'] as const;
  const preenchidos = campos.filter((k) => Boolean((prefs as Record<string, unknown>)[k])).length;
  const pct = Math.round((preenchidos / campos.length) * 100);

  const emBreve = (o: string) => { setAviso(`${o} — em breve`); setTimeout(() => setAviso(null), 1800); };

  return (
    <View style={{ flex: 1, backgroundColor: cor.surface }}>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 40 }}>
        {/* Card do usuário */}
        <Card padding={14}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
            <Avatar nome={nome} size={52} />
            <View style={{ flex: 1, minWidth: 0 }}>
              <Text style={st.nome} numberOfLines={1}>{nome}</Text>
              <Text style={st.email} numberOfLines={1}>{email}</Text>
              <View style={{ marginTop: 6, flexDirection: 'row' }}><Tag tone="sky">Plano Free</Tag></View>
            </View>
          </View>
          <Pressable onPress={() => emBreve('Premium')} style={st.premium}>
            <Text style={st.premiumTxt}>Assinar Premium · R$ 9,99/mês</Text>
          </Pressable>
        </Card>

        {/* Complete seu perfil (anel) */}
        {pct < 100 ? (
          <Pressable onPress={() => router.push('/editar-perfil')} style={st.completeCard}>
            <Anel pct={pct} />
            <View style={{ flex: 1 }}>
              <Text style={st.completeTit}>Complete seu perfil</Text>
              <Text style={st.completeSub}>Faltam alguns dados opcionais — ajudam a contextualizar pautas que afetam você.</Text>
            </View>
            <Icon name="chevR" size={18} color={cor.mutedSoft} />
          </Pressable>
        ) : null}

        <View style={{ height: 18 }} />
        <SectionHeader title="Seu feed personalizado" sub="O que o algoritmo usa para montar as recomendações" />
        <Card padding={0}>
          <View style={st.feedInfo}>
            <View style={st.feedIcon}><Icon name="spark" size={16} color={cor.white} /></View>
            <Text style={st.feedInfoTxt}>
              Seu feed é montado a partir das preferências abaixo e da sua região. Curtir posts e seguir
              parlamentares, partidos, comissões ou PLs refina as recomendações com o tempo.
            </Text>
          </View>
          <ChipBloco titulo="Temas que você acompanha" itens={prefs.temas ?? []} vazio="Nenhum tema ainda" hashtag onEdit={() => emBreve('Editar temas')} />
          <Divider />
          <ChipBloco titulo="Partidos seguidos" itens={prefs.partidos ?? []} vazio="Nenhum partido ainda" onEdit={() => emBreve('Editar partidos')} />
        </Card>

        <View style={{ height: 18 }} />
        <SectionHeader title="Conta" />
        <Grupo linhas={[
          { icon: 'gear', label: 'Editar perfil', onPress: () => router.push('/editar-perfil') },
          { icon: 'bell', label: 'Notificações', onPress: () => emBreve('Notificações') },
        ]} />

        <View style={{ height: 14 }} />
        <SectionHeader title="Privacidade & LGPD" sub="Em conformidade com a Lei Geral de Proteção de Dados" />
        <Grupo linhas={[
          { icon: 'download', label: 'Exportar meus dados', onPress: () => emBreve('Exportar dados') },
          { icon: 'trash', label: 'Deletar conta', tone: 'neg', onPress: () => emBreve('Deletar conta') },
        ]} />

        <View style={{ height: 14 }} />
        <SectionHeader title="App" />
        <Grupo linhas={[
          { icon: 'info', label: 'Sobre o Aquarius', onPress: () => emBreve('Sobre') },
          { icon: 'doc', label: 'Termos de uso', onPress: () => emBreve('Termos') },
          { icon: 'doc', label: 'Política de privacidade', onPress: () => emBreve('Política') },
        ]} />

        <Pressable onPress={sair} style={st.sair}>
          <Icon name="logout" size={15} color={cor.neg} />
          <Text style={st.sairTxt}>Sair</Text>
        </Pressable>
        <Text style={st.versao}>Aquarius Beta · v0.9 · Base Aquarius © 2026</Text>
      </ScrollView>

      {aviso ? (
        <View style={st.toast} pointerEvents="none"><Text style={st.toastTxt}>{aviso}</Text></View>
      ) : null}
    </View>
  );
}

function Anel({ pct }: { pct: number }) {
  const R = 22, C = 2 * Math.PI * R, off = C * (1 - pct / 100);
  return (
    <View style={{ width: 54, height: 54 }}>
      <Svg width={54} height={54} viewBox="0 0 54 54">
        <Circle cx={27} cy={27} r={R} fill="none" stroke={cor.border} strokeWidth={5} />
        <Circle cx={27} cy={27} r={R} fill="none" stroke={cor.sky} strokeWidth={5} strokeLinecap="round"
          strokeDasharray={C} strokeDashoffset={off} transform="rotate(-90 27 27)" />
      </Svg>
      <Text style={st.anelTxt}>{pct}%</Text>
    </View>
  );
}

function ChipBloco({ titulo, itens, vazio, onEdit, hashtag }: { titulo: string; itens: string[]; vazio: string; onEdit: () => void; hashtag?: boolean }) {
  return (
    <View style={{ padding: 12 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 9 }}>
        <Text style={st.blocoTit}>{titulo}</Text>
        <Pressable onPress={onEdit}><Text style={st.editar}>Editar</Text></Pressable>
      </View>
      {itens.length ? (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 7 }}>
          {itens.map((t) => <View key={t} style={st.chip}><Text style={st.chipTxt}>{hashtag ? `# ${t}` : t}</Text></View>)}
        </View>
      ) : <Text style={st.vazio}>{vazio}</Text>}
    </View>
  );
}

function Grupo({ linhas }: { linhas: { icon: IconName; label: string; tone?: 'neg'; onPress: () => void }[] }) {
  return (
    <Card padding={0}>
      {linhas.map((l, i) => (
        <View key={l.label}>
          <Pressable onPress={l.onPress} style={st.linha}>
            <View style={st.linhaIcon}><Icon name={l.icon} size={15} color={l.tone === 'neg' ? cor.neg : cor.navy} /></View>
            <Text style={[st.linhaLabel, l.tone === 'neg' && { color: cor.neg }]}>{l.label}</Text>
            <Icon name="chevR" size={15} color={cor.mutedSoft} />
          </Pressable>
          {i < linhas.length - 1 ? <Divider inset={56} /> : null}
        </View>
      ))}
    </Card>
  );
}

const st = StyleSheet.create({
  nome: { fontFamily: fonte.b, fontSize: 15, color: cor.navy },
  email: { marginTop: 3, fontFamily: fonte.r, fontSize: 12, color: cor.muted },
  premium: { marginTop: 12, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 11, borderRadius: 9999, backgroundColor: cor.navy },
  premiumTxt: { color: cor.white, fontFamily: fonte.b, fontSize: 13 },
  completeCard: { marginTop: 12, flexDirection: 'row', alignItems: 'center', gap: 14, padding: 13, borderRadius: raio.cardGrande, borderWidth: 1, borderColor: cor.border, backgroundColor: cor.light },
  completeTit: { fontFamily: fonte.b, fontSize: 14, color: cor.navy },
  completeSub: { marginTop: 3, fontFamily: fonte.r, fontSize: 12, color: cor.muted, lineHeight: 17 },
  anelTxt: { position: 'absolute', width: 54, height: 54, textAlign: 'center', lineHeight: 54, fontFamily: fonte.xb, fontSize: 14, color: cor.navy },
  feedInfo: { flexDirection: 'row', gap: 10, alignItems: 'flex-start', padding: 13, borderBottomWidth: 1, borderBottomColor: cor.border },
  feedIcon: { width: 30, height: 30, borderRadius: 9999, backgroundColor: cor.navy, alignItems: 'center', justifyContent: 'center' },
  feedInfoTxt: { flex: 1, fontFamily: fonte.r, fontSize: 12, color: cor.ink, lineHeight: 18 },
  blocoTit: { flex: 1, fontFamily: fonte.b, fontSize: 12, color: cor.navy },
  editar: { fontFamily: fonte.b, fontSize: 11.5, color: cor.sky },
  chip: { paddingHorizontal: 11, paddingVertical: 6, borderRadius: 9999, backgroundColor: cor.light },
  chipTxt: { fontFamily: fonte.sb, fontSize: 11.5, color: cor.navy },
  vazio: { fontFamily: fonte.r, fontSize: 12, color: cor.mutedSoft },
  linha: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12 },
  linhaIcon: { width: 30, height: 30, borderRadius: 8, backgroundColor: cor.light, alignItems: 'center', justifyContent: 'center' },
  linhaLabel: { flex: 1, fontFamily: fonte.m, fontSize: 13.5, color: cor.navy },
  sair: { marginTop: 18, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 12, borderRadius: 9999, borderWidth: 1, borderColor: cor.border },
  sairTxt: { fontFamily: fonte.sb, fontSize: 13, color: cor.neg },
  versao: { marginTop: 14, textAlign: 'center', fontFamily: fonte.m, fontSize: 10.5, color: cor.muted },
  toast: { position: 'absolute', bottom: 34, alignSelf: 'center', backgroundColor: cor.navy, paddingHorizontal: 16, paddingVertical: 10, borderRadius: 9999 },
  toastTxt: { color: cor.white, fontFamily: fonte.sb, fontSize: 12.5 },
});
