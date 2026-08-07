import { useEffect, useRef, useState } from 'react';
import {
  View, Text, TextInput, Pressable, ActivityIndicator, StyleSheet,
  KeyboardAvoidingView, Platform, ScrollView,
} from 'react-native';
import { useRouter } from 'expo-router';
import Svg, { Path } from 'react-native-svg';
import { useAuth } from '../lib/auth';
import { cor, raio, fonte } from '../lib/tema';
import { Logo } from '../components/base';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Login() {
  const router = useRouter();
  const { enviarCodigo, verificarCodigo } = useAuth();
  const [step, setStep] = useState<0 | 1>(0);
  const [email, setEmail] = useState('');
  const [codigo, setCodigo] = useState(['', '', '', '', '', '']);
  const [enviando, setEnviando] = useState(false);
  const [verificando, setVerificando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const refs = useRef<Array<TextInput | null>>([]);

  const emailOk = EMAIL_RE.test(email.trim());

  const enviar = async () => {
    if (!emailOk || enviando) return;
    setErro(null); setEnviando(true);
    try {
      await enviarCodigo(email);
      setStep(1);
      setTimeout(() => refs.current[0]?.focus(), 250);
    } catch (e: any) {
      setErro(traduzErro(e?.message));
    } finally { setEnviando(false); }
  };

  const onDigit = (i: number, v: string) => {
    const d = v.replace(/\D/g, '');
    const next = [...codigo];
    if (d.length > 1) {
      // colou o código inteiro
      for (let k = 0; k < 6; k++) next[k] = d[k] ?? '';
      setCodigo(next);
      refs.current[Math.min(d.length, 5)]?.focus();
      return;
    }
    next[i] = d;
    setCodigo(next);
    if (d && i < 5) refs.current[i + 1]?.focus();
  };

  const verificar = async (cod: string) => {
    setErro(null); setVerificando(true);
    try {
      await verificarCodigo(email, cod);
      router.replace('/onboarding');
    } catch (e: any) {
      setErro(traduzErro(e?.message));
      setCodigo(['', '', '', '', '', '']);
      refs.current[0]?.focus();
    } finally { setVerificando(false); }
  };

  useEffect(() => {
    if (step === 1 && codigo.every((c) => c) && !verificando) verificar(codigo.join(''));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [codigo]);

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={{ flexGrow: 1 }} keyboardShouldPersistTaps="handled" style={st.bg}>
        {/* Onda Sky decorativa */}
        <Svg width={220} height={80} viewBox="0 0 220 80" style={st.onda}>
          <Path d="M-5 50 Q40 20 90 50 T185 50 T235 50" stroke={cor.sky} strokeWidth={2.5} fill="none" strokeLinecap="round" />
          <Path d="M-5 65 Q40 35 90 65 T185 65 T235 65" stroke={cor.sky} strokeOpacity={0.35} strokeWidth={2} fill="none" strokeLinecap="round" />
        </Svg>

        <View style={st.conteudo}>
          <Logo height={28} />
          <Text style={st.h1}>Tudo sobre o Congresso Nacional na palma da sua mão.</Text>
          <Text style={st.p}>
            Dados completos do Congresso combinados com o <Text style={st.forte}>Prometeus IA</Text> para
            consultas analíticas instantâneas.
          </Text>

          <View style={{ marginTop: 'auto' }}>
            {step === 0 ? (
              <>
                <Text style={st.label}>Seu e-mail</Text>
                <TextInput
                  style={st.input}
                  value={email}
                  onChangeText={(t) => { setEmail(t); setErro(null); }}
                  placeholder="voce@email.com"
                  placeholderTextColor={cor.mutedSoft}
                  keyboardType="email-address"
                  autoCapitalize="none"
                  autoCorrect={false}
                  inputMode="email"
                  onSubmitEditing={enviar}
                  returnKeyType="send"
                />
                {erro ? <Text style={st.erro}>{erro}</Text> : null}
                <Pressable
                  onPress={enviar}
                  disabled={!emailOk || enviando}
                  style={[st.cta, (!emailOk || enviando) && { opacity: 0.5 }]}
                >
                  {enviando ? <ActivityIndicator color={cor.white} />
                    : <Text style={st.ctaTxt}>Receber código no e-mail</Text>}
                </Pressable>
                <Text style={st.nota}>Login por SMS e WhatsApp — em breve.</Text>
                <Text style={st.termos}>
                  Ao continuar você aceita os <Text style={st.link}>Termos</Text> e a{' '}
                  <Text style={st.link}>Política de Privacidade</Text> (LGPD).
                </Text>
              </>
            ) : (
              <>
                <Text style={st.label}>Código enviado para {email}</Text>
                <View style={st.otpRow}>
                  {codigo.map((c, i) => (
                    <TextInput
                      key={i}
                      ref={(r) => { refs.current[i] = r; }}
                      value={c}
                      onChangeText={(v) => onDigit(i, v)}
                      onKeyPress={({ nativeEvent }) => {
                        if (nativeEvent.key === 'Backspace' && !codigo[i] && i > 0) refs.current[i - 1]?.focus();
                      }}
                      keyboardType="number-pad"
                      inputMode="numeric"
                      maxLength={1}
                      style={[st.otpBox, c ? { borderColor: cor.sky } : null]}
                      editable={!verificando}
                    />
                  ))}
                </View>
                {verificando ? <ActivityIndicator color={cor.blue} style={{ marginTop: 14 }} /> : null}
                {erro ? <Text style={[st.erro, { textAlign: 'center' }]}>{erro}</Text> : null}
                <Pressable onPress={enviar} disabled={enviando} style={st.linkBtn}>
                  <Text style={st.linkBtnTxt}>{enviando ? 'Reenviando…' : 'Reenviar código'}</Text>
                </Pressable>
                <Pressable onPress={() => { setStep(0); setCodigo(['', '', '', '', '', '']); setErro(null); }} style={st.linkBtn}>
                  <Text style={st.linkBtnTxt}>Alterar e-mail</Text>
                </Pressable>
              </>
            )}
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function traduzErro(msg?: string): string {
  const m = (msg ?? '').toLowerCase();
  if (m.includes('token') || m.includes('invalid') || m.includes('expired')) return 'Código inválido ou expirado. Tente de novo.';
  if (m.includes('rate') || m.includes('limit') || m.includes('seconds')) return 'Muitas tentativas. Aguarde um minuto e tente de novo.';
  if (m.includes('email')) return 'E-mail inválido.';
  return 'Não deu para completar agora. Tente novamente.';
}

const st = StyleSheet.create({
  bg: { flex: 1, backgroundColor: cor.light },
  onda: { position: 'absolute', top: 62, right: -30, opacity: 0.55 },
  conteudo: { flex: 1, paddingHorizontal: 28, paddingTop: 84, paddingBottom: 32 },
  h1: { marginTop: 42, marginBottom: 8, fontSize: 26, fontFamily: fonte.xb, color: cor.navy, letterSpacing: -0.5, lineHeight: 31 },
  p: { fontSize: 14, lineHeight: 22, color: cor.muted, maxWidth: 320 },
  forte: { color: cor.navy, fontFamily: fonte.b },
  label: { fontFamily: fonte.b, fontSize: 10.5, color: cor.muted, letterSpacing: 1.6, textTransform: 'uppercase' },
  input: {
    marginTop: 8, backgroundColor: cor.white, borderRadius: raio.input, borderWidth: 1.5, borderColor: cor.border,
    paddingHorizontal: 14, paddingVertical: 14, fontSize: 16, color: cor.navy, fontFamily: fonte.m,
  },
  cta: { marginTop: 14, paddingVertical: 15, borderRadius: 9999, backgroundColor: cor.navy, alignItems: 'center', justifyContent: 'center' },
  ctaTxt: { color: cor.white, fontFamily: fonte.b, fontSize: 14, letterSpacing: 0.3 },
  nota: { marginTop: 12, fontSize: 11.5, color: cor.mutedSoft, textAlign: 'center' },
  termos: { marginTop: 10, fontSize: 11.5, lineHeight: 18, color: cor.muted, textAlign: 'center' },
  link: { color: cor.sky, fontFamily: fonte.sb },
  erro: { marginTop: 10, fontSize: 12.5, color: cor.neg, fontFamily: fonte.m },
  otpRow: { flexDirection: 'row', gap: 8, marginTop: 10 },
  otpBox: {
    flex: 1, height: 54, borderRadius: raio.input, textAlign: 'center', borderWidth: 1.5, borderColor: cor.border,
    backgroundColor: cor.white, fontFamily: fonte.xb, fontSize: 22, color: cor.navy,
  },
  linkBtn: { marginTop: 14, paddingVertical: 4, alignItems: 'center' },
  linkBtnTxt: { fontFamily: fonte.sb, fontSize: 12.5, color: cor.sky },
});
