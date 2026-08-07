import { useEffect, useRef, useState } from 'react';
import {
  View, Text, TextInput, Pressable, ScrollView, Animated, Easing,
  KeyboardAvoidingView, Platform, StyleSheet,
} from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { cor, raio, fonte } from '../../lib/tema';
import { Icon } from '../../components/base';

type Papel = 'user' | 'assistant';
interface Msg { papel: Papel; texto: string }

const INTRO: Msg = {
  papel: 'assistant',
  texto: 'Sou o **Prometeus**. Pergunte sobre parlamentares, proposições, emendas, votações ou peça um relatório.',
};

// Resposta provisória e HONESTA — o agente real entra no próximo passo.
const PLACEHOLDER =
  'Ainda não estou ligado ao banco — o **agente Prometeus** entra no próximo passo. ' +
  'Quando conectar, respondo com dados reais do Congresso (despesas, emendas, votações), **sempre com a fonte oficial**.';

export default function PrometeusChat() {
  const { prompt } = useLocalSearchParams<{ prompt?: string }>();
  const [msgs, setMsgs] = useState<Msg[]>([INTRO]);
  const [input, setInput] = useState('');
  const [digitando, setDigitando] = useState(false);
  const scroll = useRef<ScrollView>(null);
  const jaEnviou = useRef(false);

  const enviar = (texto: string) => {
    const t = texto.trim();
    if (!t || digitando) return;
    setMsgs((m) => [...m, { papel: 'user', texto: t }]);
    setInput('');
    setDigitando(true);
    setTimeout(() => {
      setMsgs((m) => [...m, { papel: 'assistant', texto: PLACEHOLDER }]);
      setDigitando(false);
    }, 700);
  };

  // Se veio de uma sugestão, dispara a pergunta uma vez.
  useEffect(() => {
    if (prompt && !jaEnviou.current) { jaEnviou.current = true; enviar(prompt); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prompt]);

  useEffect(() => { scroll.current?.scrollToEnd({ animated: true }); }, [msgs, digitando]);

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: cor.surface }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView ref={scroll} contentContainerStyle={{ padding: 14, gap: 12 }}>
        {msgs.map((m, i) => <Bolha key={i} msg={m} />)}
        {digitando ? <Digitando /> : null}
      </ScrollView>

      <View style={st.barra}>
        <View style={st.inputRow}>
          <TextInput
            style={st.input}
            value={input}
            onChangeText={setInput}
            placeholder="Pergunte ao Prometeus…"
            placeholderTextColor={cor.mutedSoft}
            multiline
            onSubmitEditing={() => enviar(input)}
          />
          <Pressable onPress={() => enviar(input)} disabled={!input.trim()}
            style={[st.send, { backgroundColor: input.trim() ? cor.navy : cor.light }]}>
            <Icon name="send" size={16} color={input.trim() ? cor.white : cor.mutedSoft} />
          </Pressable>
        </View>
        <View style={st.chips}>
          <Chip label="Resumir atuação" onPress={() => enviar('Faça um resumo da atuação parlamentar.')} />
          <Chip label="Gerar relatório" onPress={() => enviar('Gere um relatório com os principais números.')} />
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

function Bolha({ msg }: { msg: Msg }) {
  if (msg.papel === 'user') {
    return <View style={st.userWrap}><Text style={st.userTxt}>{msg.texto}</Text></View>;
  }
  return (
    <View style={st.aiRow}>
      <View style={st.aiAvatar}><Icon name="spark" size={14} color={cor.white} /></View>
      <View style={st.aiBolha}><Rico texto={msg.texto} /></View>
    </View>
  );
}

/** Renderiza **negrito** simples. */
function Rico({ texto }: { texto: string }) {
  const partes = texto.split(/(\*\*[^*]+\*\*)/g);
  return (
    <Text style={st.aiTxt}>
      {partes.map((seg, i) =>
        seg.startsWith('**') && seg.endsWith('**')
          ? <Text key={i} style={st.negrito}>{seg.slice(2, -2)}</Text>
          : <Text key={i}>{seg}</Text>,
      )}
    </Text>
  );
}

function Digitando() {
  const v = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.loop(Animated.sequence([
      Animated.timing(v, { toValue: 1, duration: 500, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      Animated.timing(v, { toValue: 0, duration: 500, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
    ])).start();
  }, [v]);
  const op = v.interpolate({ inputRange: [0, 1], outputRange: [0.3, 1] });
  return (
    <View style={st.aiRow}>
      <View style={st.aiAvatar}><Icon name="spark" size={14} color={cor.white} /></View>
      <View style={[st.aiBolha, { flexDirection: 'row', gap: 4, alignItems: 'center' }]}>
        {[0, 1, 2].map((i) => <Animated.View key={i} style={[st.dot, { opacity: op }]} />)}
      </View>
    </View>
  );
}

function Chip({ label, onPress }: { label: string; onPress: () => void }) {
  return <Pressable onPress={onPress} style={st.chip}><Text style={st.chipTxt}>{label}</Text></Pressable>;
}

const st = StyleSheet.create({
  userWrap: { alignSelf: 'flex-end', maxWidth: '85%', paddingHorizontal: 14, paddingVertical: 10, backgroundColor: cor.navy, borderRadius: 18, borderBottomRightRadius: 4 },
  userTxt: { color: cor.white, fontFamily: fonte.r, fontSize: 14, lineHeight: 20 },
  aiRow: { flexDirection: 'row', gap: 8, alignItems: 'flex-start', maxWidth: '92%' },
  aiAvatar: { width: 28, height: 28, borderRadius: 9999, backgroundColor: cor.navy, alignItems: 'center', justifyContent: 'center' },
  aiBolha: { flex: 1, paddingHorizontal: 14, paddingVertical: 10, backgroundColor: cor.white, borderWidth: 1, borderColor: cor.border, borderRadius: 18, borderTopLeftRadius: 4 },
  aiTxt: { fontFamily: fonte.r, fontSize: 14, color: cor.ink, lineHeight: 21 },
  negrito: { fontFamily: fonte.b, color: cor.navy },
  dot: { width: 6, height: 6, borderRadius: 9999, backgroundColor: cor.muted },
  barra: { paddingHorizontal: 12, paddingTop: 8, paddingBottom: 14, backgroundColor: cor.surface, borderTopWidth: 1, borderTopColor: cor.border },
  inputRow: { flexDirection: 'row', alignItems: 'flex-end', gap: 8, backgroundColor: cor.white, borderRadius: 24, borderWidth: 1.5, borderColor: cor.borderStrong, paddingLeft: 14, paddingRight: 6, paddingVertical: 6 },
  input: { flex: 1, fontFamily: fonte.r, fontSize: 14, color: cor.navy, paddingVertical: 6, maxHeight: 120 },
  send: { width: 36, height: 36, borderRadius: 9999, alignItems: 'center', justifyContent: 'center' },
  chips: { flexDirection: 'row', justifyContent: 'center', gap: 10, marginTop: 8 },
  chip: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 9999, backgroundColor: cor.white, borderWidth: 1, borderColor: cor.border },
  chipTxt: { fontFamily: fonte.sb, fontSize: 11.5, color: cor.navy },
});
