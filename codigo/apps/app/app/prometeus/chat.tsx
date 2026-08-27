import { useEffect, useRef, useState } from 'react';
import {
  View, Text, TextInput, Pressable, ScrollView, Animated, Easing,
  KeyboardAvoidingView, Platform, StyleSheet, Linking,
} from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { fonte, type Tema } from '../../lib/tema';
import { useTemaEstilos } from '../../lib/theme';
import { Icon } from '../../components/base';

type Papel = 'user' | 'assistant';
interface Fonte { source: string | null; source_url: string | null; synced_at: string | null }
interface Msg { papel: Papel; texto: string; fontes?: Fonte[]; ressalvas?: string[] }

// Endpoint do serviço Prometeus (Etapa 2.2). Enquanto não publicado, fica indefinido
// e o chat mostra um aviso honesto — nada quebra.
const PROMETEUS_URL = process.env.EXPO_PUBLIC_PROMETEUS_URL;

const INTRO: Msg = {
  papel: 'assistant',
  texto: 'Sou o **Prometeus**. Pergunte sobre **despesas de cota**, **emendas** ou a **agenda** do Congresso — respondo com dados oficiais, **sempre com a fonte**.',
};

const NAO_CONECTADO =
  'Ainda não estou conectado ao serviço (falta publicar o endpoint). Assim que o ' +
  'Prometeus subir, respondo com dados reais do Congresso — **sempre com a fonte**.';

const ERRO = 'Não consegui falar com o serviço agora. Tente de novo em instantes.';

export default function PrometeusChat() {
  const { cor, st } = useTemaEstilos(criarSt);
  const { prompt } = useLocalSearchParams<{ prompt?: string }>();
  const [msgs, setMsgs] = useState<Msg[]>([INTRO]);
  const [input, setInput] = useState('');
  const [digitando, setDigitando] = useState(false);
  const scroll = useRef<ScrollView>(null);
  const jaEnviou = useRef(false);

  const enviar = async (texto: string) => {
    const t = texto.trim();
    if (!t || digitando) return;
    setMsgs((m) => [...m, { papel: 'user', texto: t }]);
    setInput('');
    setDigitando(true);
    try {
      if (!PROMETEUS_URL) {
        setMsgs((m) => [...m, { papel: 'assistant', texto: NAO_CONECTADO }]);
        return;
      }
      const resp = await fetch(`${PROMETEUS_URL}/perguntar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pergunta: t }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setMsgs((m) => [...m, {
        papel: 'assistant',
        texto: typeof data?.resposta === 'string' ? data.resposta : 'Não recebi resposta.',
        fontes: Array.isArray(data?.fontes) ? data.fontes : [],
        ressalvas: Array.isArray(data?.ressalvas) ? data.ressalvas : [],
      }]);
    } catch {
      setMsgs((m) => [...m, { papel: 'assistant', texto: ERRO }]);
    } finally {
      setDigitando(false);
    }
  };

  // Se veio de uma sugestão, dispara a pergunta uma vez.
  useEffect(() => {
    if (prompt && !jaEnviou.current) { jaEnviou.current = true; void enviar(prompt); }
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
            onSubmitEditing={() => { void enviar(input); }}
          />
          <Pressable onPress={() => { void enviar(input); }} disabled={!input.trim()}
            style={[st.send, { backgroundColor: input.trim() ? cor.navy : cor.light }]}>
            <Icon name="send" size={16} color={input.trim() ? cor.white : cor.mutedSoft} />
          </Pressable>
        </View>
        <View style={st.chips}>
          <Chip label="Gastos de um parlamentar" onPress={() => { void enviar('Como vejo os gastos de cota de um parlamentar?'); }} />
          <Chip label="Agenda do Congresso" onPress={() => { void enviar('O que está na agenda do Congresso hoje?'); }} />
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

function Bolha({ msg }: { msg: Msg }) {
  const { cor, st } = useTemaEstilos(criarSt);
  if (msg.papel === 'user') {
    return <View style={st.userWrap}><Text style={st.userTxt}>{msg.texto}</Text></View>;
  }
  const ressalvas = msg.ressalvas ?? [];
  const fontes = msg.fontes ?? [];
  return (
    <View style={st.aiRow}>
      <View style={st.aiAvatar}><Icon name="spark" size={14} color={cor.white} /></View>
      <View style={st.aiBolha}>
        <Rico texto={msg.texto} />
        {ressalvas.length > 0 ? (
          <View style={st.ressalvas}>
            {ressalvas.map((r, i) => <Text key={i} style={st.ressalvaTxt}>⚠ {r}</Text>)}
          </View>
        ) : null}
        {fontes.length > 0 ? (
          <View style={st.fontes}>
            <Text style={st.fontesLabel}>FONTES</Text>
            {fontes.map((f, i) => <FonteItem key={i} fonte={f} />)}
          </View>
        ) : null}
      </View>
    </View>
  );
}

function FonteItem({ fonte: f }: { fonte: Fonte }) {
  const { cor, st } = useTemaEstilos(criarSt);
  const frescor = f.synced_at ? f.synced_at.slice(0, 10) : null;
  const abrir = () => { if (f.source_url) void Linking.openURL(f.source_url); };
  return (
    <Pressable onPress={abrir} disabled={!f.source_url} style={st.fonteItem}>
      <Icon name="doc" size={11} color={cor.sky} />
      <Text style={st.fonteTxt} numberOfLines={1}>
        {f.source ?? 'fonte oficial'}{frescor ? ` · ${frescor}` : ''}
      </Text>
    </Pressable>
  );
}

/** Renderiza **negrito** simples. */
function Rico({ texto }: { texto: string }) {
  const { st } = useTemaEstilos(criarSt);
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
  const { cor, st } = useTemaEstilos(criarSt);
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
  const { st } = useTemaEstilos(criarSt);
  return <Pressable onPress={onPress} style={st.chip}><Text style={st.chipTxt}>{label}</Text></Pressable>;
}

const criarSt = (cor: Tema) => StyleSheet.create({
  userWrap: { alignSelf: 'flex-end', maxWidth: '85%', paddingHorizontal: 14, paddingVertical: 10, backgroundColor: cor.navy, borderRadius: 18, borderBottomRightRadius: 4 },
  userTxt: { color: cor.white, fontFamily: fonte.r, fontSize: 14, lineHeight: 20 },
  aiRow: { flexDirection: 'row', gap: 8, alignItems: 'flex-start', maxWidth: '92%' },
  aiAvatar: { width: 28, height: 28, borderRadius: 9999, backgroundColor: cor.navy, alignItems: 'center', justifyContent: 'center' },
  aiBolha: { flex: 1, paddingHorizontal: 14, paddingVertical: 10, backgroundColor: cor.cartao, borderWidth: 1, borderColor: cor.border, borderRadius: 18, borderTopLeftRadius: 4 },
  aiTxt: { fontFamily: fonte.r, fontSize: 14, color: cor.ink, lineHeight: 21 },
  negrito: { fontFamily: fonte.b, color: cor.texto },
  dot: { width: 6, height: 6, borderRadius: 9999, backgroundColor: cor.muted },
  ressalvas: { marginTop: 8, gap: 3 },
  ressalvaTxt: { fontFamily: fonte.r, fontSize: 11, color: cor.muted, lineHeight: 15 },
  fontes: { marginTop: 10, paddingTop: 8, borderTopWidth: 1, borderTopColor: cor.border, gap: 4 },
  fontesLabel: { fontFamily: fonte.b, fontSize: 9, letterSpacing: 1, color: cor.mutedSoft },
  fonteItem: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  fonteTxt: { fontFamily: fonte.m, fontSize: 11, color: cor.sky, flex: 1 },
  barra: { paddingHorizontal: 12, paddingTop: 8, paddingBottom: 14, backgroundColor: cor.surface, borderTopWidth: 1, borderTopColor: cor.border },
  inputRow: { flexDirection: 'row', alignItems: 'flex-end', gap: 8, backgroundColor: cor.cartao, borderRadius: 24, borderWidth: 1.5, borderColor: cor.borderStrong, paddingLeft: 14, paddingRight: 6, paddingVertical: 6 },
  input: { flex: 1, fontFamily: fonte.r, fontSize: 14, color: cor.texto, paddingVertical: 6, maxHeight: 120 },
  send: { width: 36, height: 36, borderRadius: 9999, alignItems: 'center', justifyContent: 'center' },
  chips: { flexDirection: 'row', justifyContent: 'center', gap: 10, marginTop: 8 },
  chip: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 9999, backgroundColor: cor.cartao, borderWidth: 1, borderColor: cor.border },
  chipTxt: { fontFamily: fonte.sb, fontSize: 11.5, color: cor.texto },
});
