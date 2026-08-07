import { useState } from 'react';
import { View, Text, TextInput, Pressable, ScrollView, ActivityIndicator, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../lib/auth';
import { cor, raio, fonte } from '../lib/tema';
import { Avatar, Icon, Card } from '../components/base';

export default function EditarPerfil() {
  const router = useRouter();
  const { prefs, atualizarPrefs } = useAuth();
  const [nome, setNome] = useState(prefs.nome ?? '');
  const [cep, setCep] = useState(prefs.cep ?? '');
  const [idade, setIdade] = useState(prefs.idade ?? '');
  const [genero, setGenero] = useState(prefs.genero ?? '');
  const [escolaridade, setEscolaridade] = useState(prefs.escolaridade ?? '');
  const [renda, setRenda] = useState(prefs.renda ?? '');
  const [ocupacao, setOcupacao] = useState(prefs.ocupacao ?? '');
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const total = [cep, idade, genero, escolaridade, renda, ocupacao].filter(Boolean).length;
  const pct = Math.round((total / 6) * 100);

  const salvar = async () => {
    setErro(null); setSalvando(true);
    try {
      await atualizarPrefs({ nome, cep, idade, genero, escolaridade, renda, ocupacao });
      router.back();
    } catch {
      setErro('Não deu para salvar agora. Tente novamente.');
    } finally { setSalvando(false); }
  };

  const setCepFmt = (t: string) => {
    const d = t.replace(/\D/g, '').slice(0, 8);
    setCep(d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d);
  };

  return (
    <View style={{ flex: 1, backgroundColor: cor.surface }}>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 40 }}>
        {/* Barra de completude */}
        <View style={st.compl}>
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 9 }}>
            <Text style={st.complTit}>Perfil {pct}% completo</Text>
            <Text style={[st.complSub, pct >= 100 && { color: cor.sky }]}>
              {pct >= 100 ? 'Tudo pronto 🎉' : `${6 - total} campo(s) restante(s)`}
            </Text>
          </View>
          <View style={st.barraBase}><View style={[st.barraFill, { width: `${pct}%` }]} /></View>
        </View>

        <View style={{ alignItems: 'center', gap: 10, marginBottom: 22 }}>
          <Avatar nome={nome || 'Você'} size={84} />
          <Pressable onPress={() => {}}><Text style={st.alterarFoto}>Alterar foto</Text></Pressable>
        </View>

        <Card padding={16}>
          <Campo label="Nome">
            <TextInput style={st.input} value={nome} onChangeText={setNome} placeholder="Seu nome" placeholderTextColor={cor.mutedSoft} />
          </Campo>
          <Campo label="Região (CEP)">
            <TextInput style={st.input} value={cep} onChangeText={setCepFmt} placeholder="00000-000" placeholderTextColor={cor.mutedSoft} keyboardType="number-pad" inputMode="numeric" />
            <View style={{ marginTop: 7, flexDirection: 'row', alignItems: 'center', gap: 6 }}>
              <Icon name="compass" size={13} color={cor.sky} />
              <Text style={st.hint}>Usado para mostrar quem representa você</Text>
            </View>
          </Campo>
          <Campo label="Faixa etária">
            <Seg value={idade} set={setIdade} options={['16–24', '25–34', '35–44', '45–59', '60+']} />
          </Campo>
          <Campo label="Identificação de gênero" ultimo>
            <Seg value={genero} set={setGenero} options={['Mulher', 'Homem', 'Outro', 'Prefiro não dizer']} />
          </Campo>
        </Card>

        <View style={st.opcHead}>
          <Text style={st.opcTit}>Dados opcionais</Text>
          <View style={st.opcTag}><Icon name="spark" size={11} color={cor.sky} /><Text style={st.opcTagTxt}>Completa seu perfil</Text></View>
        </View>
        <Card padding={16}>
          <Campo label="Escolaridade">
            <Seg value={escolaridade} set={setEscolaridade} options={['Fundamental', 'Médio', 'Superior', 'Pós-graduação']} />
          </Campo>
          <Campo label="Faixa de renda familiar">
            <Seg value={renda} set={setRenda} options={['Até 2 SM', '2–5 SM', '5–10 SM', '10+ SM']} />
          </Campo>
          <Campo label="Ocupação" ultimo>
            <Seg value={ocupacao} set={setOcupacao} options={['Estudante', 'CLT / Assalariado', 'Autônomo', 'Servidor público', 'Empresário', 'Aposentado', 'Outro']} />
          </Campo>
        </Card>

        <Text style={st.lgpd}>
          Esses dados ajudam o algoritmo a contextualizar pautas que afetam você. São tratados de forma agregada e anônima (LGPD).
        </Text>
        {erro ? <Text style={st.erro}>{erro}</Text> : null}

        <Pressable onPress={salvar} disabled={salvando} style={[st.salvar, salvando && { opacity: 0.6 }]}>
          {salvando ? <ActivityIndicator color={cor.white} /> : <Text style={st.salvarTxt}>Salvar alterações</Text>}
        </Pressable>
      </ScrollView>
    </View>
  );
}

function Campo({ label, children, ultimo }: { label: string; children: React.ReactNode; ultimo?: boolean }) {
  return (
    <View style={{ marginBottom: ultimo ? 0 : 18 }}>
      <Text style={st.campoLabel}>{label}</Text>
      {children}
    </View>
  );
}

function Seg({ value, set, options }: { value: string; set: (v: string) => void; options: string[] }) {
  return (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
      {options.map((o) => {
        const on = value === o;
        return (
          <Pressable key={o} onPress={() => set(on ? '' : o)}
            style={[st.seg, on && { backgroundColor: cor.navy, borderColor: cor.navy }]}>
            <Text style={[st.segTxt, on && { color: cor.white }]}>{o}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const st = StyleSheet.create({
  compl: { marginBottom: 18, padding: 13, borderRadius: raio.card, backgroundColor: cor.white, borderWidth: 1, borderColor: cor.border },
  complTit: { fontFamily: fonte.b, fontSize: 13, color: cor.navy },
  complSub: { fontFamily: fonte.sb, fontSize: 11.5, color: cor.muted },
  barraBase: { backgroundColor: cor.light, borderRadius: 9999, height: 8, overflow: 'hidden' },
  barraFill: { height: '100%', borderRadius: 9999, backgroundColor: cor.sky },
  alterarFoto: { fontFamily: fonte.b, fontSize: 12.5, color: cor.sky },
  campoLabel: { fontFamily: fonte.b, fontSize: 12, color: cor.navy, marginBottom: 9 },
  input: { paddingHorizontal: 14, paddingVertical: 12, borderRadius: raio.input, borderWidth: 1.5, borderColor: cor.border, backgroundColor: cor.surface, fontFamily: fonte.sb, fontSize: 14, color: cor.navy },
  hint: { fontFamily: fonte.m, fontSize: 11.5, color: cor.muted },
  seg: { paddingHorizontal: 15, paddingVertical: 9, borderRadius: 9999, backgroundColor: cor.white, borderWidth: 1.5, borderColor: cor.border },
  segTxt: { fontFamily: fonte.sb, fontSize: 13, color: cor.navy },
  opcHead: { marginTop: 18, marginBottom: 10, flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 4 },
  opcTit: { fontFamily: fonte.xb, fontSize: 12.5, color: cor.navy },
  opcTag: { flexDirection: 'row', alignItems: 'center', gap: 5, paddingHorizontal: 9, paddingVertical: 3, borderRadius: 9999, backgroundColor: cor.light },
  opcTagTxt: { fontFamily: fonte.b, fontSize: 10, color: cor.sky },
  lgpd: { marginTop: 10, paddingHorizontal: 4, fontFamily: fonte.r, fontSize: 11, color: cor.muted, lineHeight: 16 },
  erro: { marginTop: 10, paddingHorizontal: 4, fontFamily: fonte.m, fontSize: 12.5, color: cor.neg },
  salvar: { marginTop: 18, paddingVertical: 14, borderRadius: 9999, backgroundColor: cor.navy, alignItems: 'center', justifyContent: 'center' },
  salvarTxt: { fontFamily: fonte.b, fontSize: 14, color: cor.white },
});
