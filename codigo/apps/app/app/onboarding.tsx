import { useEffect, useRef, useState } from 'react';
import { View, Text, Pressable, TextInput, ScrollView, Animated, Easing, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../lib/auth';
import { useFollows } from '../lib/follows';
import { raio, fonte, type Tema } from '../lib/tema';
import { useTemaEstilos } from '../lib/theme';
import { Logo, Icon } from '../components/base';

const TEMAS = [
  'Educação', 'Saúde', 'Economia', 'Segurança', 'Meio ambiente', 'Tecnologia',
  'Trabalho', 'Direitos humanos', 'Agropecuária', 'Infraestrutura', 'Cultura', 'Impostos',
];
const PARTIDOS = ['PT', 'PL', 'PSD', 'MDB', 'UNIÃO', 'PP', 'REPUBLICANOS', 'PSB', 'PDT', 'PSOL', 'NOVO', 'PCdoB'];

type Step = 'intro' | 'temas' | 'partidos' | 'sobre' | 'montando';
const ORDEM: Step[] = ['intro', 'temas', 'partidos', 'sobre', 'montando'];

export default function Onboarding() {
  const { cor, st } = useTemaEstilos(criarSt);
  const router = useRouter();
  const { concluirOnboarding } = useAuth();
  const { seguir } = useFollows();
  const [step, setStep] = useState<Step>('intro');
  const [temas, setTemas] = useState<string[]>([]);
  const [partidos, setPartidos] = useState<string[]>([]);
  const [cep, setCep] = useState('');
  const [idade, setIdade] = useState('');
  const [genero, setGenero] = useState('');

  const idx = ORDEM.indexOf(step);
  const avancar = () => setStep(ORDEM[Math.min(ORDEM.length - 1, idx + 1)]);
  const voltar = () => setStep(ORDEM[Math.max(0, idx - 1)]);
  const toggle = (arr: string[], set: (v: string[]) => void, v: string) =>
    set(arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);

  const concluir = async () => {
    // Persiste os interesses como FOLLOWS (fonte única) e marca onboarded no
    // perfil (só os dados opt-in vão para prefs). Em sucesso, o GATE leva ao app
    // quando onboarded=true propaga. Em falha de rede, faz replace como fallback.
    try {
      const novos = [
        ...temas.map((t) => ({ tipo: 'tema' as const, ref_id: t, rotulo: t })),
        ...partidos.map((p) => ({ tipo: 'partido' as const, ref_id: p, rotulo: p })),
      ];
      await Promise.all(novos.map((f) => seguir(f).catch(() => {})));
      await concluirOnboarding({ cep, idade, genero, migradoFollows: true });
    } catch {
      router.replace('/');
    }
  };

  useEffect(() => {
    if (step === 'montando') {
      const t = setTimeout(concluir, 2200);
      return () => clearTimeout(t);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

  const podeAvancar = step === 'temas' ? temas.length >= 1 : true;
  const progresso = idx / (ORDEM.length - 1);

  if (step === 'intro') {
    return (
      <View style={st.intro}>
        <View style={{ marginBottom: 30 }}><Logo height={30} dark /></View>
        <Text style={st.introH1}>Vamos montar o seu Congresso.</Text>
        <Text style={st.introP}>
          Responda a 3 perguntas rápidas. Com elas, o Aquarius monta um feed só seu — com os temas,
          os parlamentares e as decisões que importam para a sua vida.
        </Text>
        <Pressable onPress={avancar} style={st.introCta}>
          <Text style={st.introCtaTxt}>Começar</Text>
          <Icon name="chevR" size={18} color={cor.texto} />
        </Pressable>
        <Text style={st.introNota}>Seus dados ficam privados e podem ser alterados depois.</Text>
      </View>
    );
  }

  if (step === 'montando') return <Montando />;

  return (
    <View style={{ flex: 1, backgroundColor: cor.surface }}>
      {/* barra de progresso */}
      <View style={st.topo}>
        <Pressable onPress={voltar} hitSlop={8} style={{ padding: 6, marginLeft: -6 }}>
          <Icon name="back" size={22} color={cor.texto} />
        </Pressable>
        <View style={st.progBase}><View style={[st.progFill, { width: `${progresso * 100}%` }]} /></View>
        <Text style={st.progTxt}>{idx}/{ORDEM.length - 2}</Text>
      </View>

      <ScrollView contentContainerStyle={{ padding: 24, paddingBottom: 120 }}>
        {step === 'temas' && (
          <>
            <Kicker>O QUE TE MOVE</Kicker>
            <Titulo>Quais temas você quer acompanhar?</Titulo>
            <Sub>Escolha pelo menos um. O algoritmo prioriza essas pautas no seu feed.</Sub>
            <View style={st.chipsWrap}>
              {TEMAS.map((t) => {
                const on = temas.includes(t);
                return (
                  <Pressable key={t} onPress={() => toggle(temas, setTemas, t)}
                    style={[st.chip, on && { backgroundColor: cor.navy, borderColor: cor.navy }]}>
                    {on ? <Icon name="check" size={14} color={cor.white} /> : null}
                    <Text style={[st.chipTxt, on && { color: cor.white }]}>{t}</Text>
                  </Pressable>
                );
              })}
            </View>
          </>
        )}

        {step === 'partidos' && (
          <>
            <Kicker>OPCIONAL</Kicker>
            <Titulo>Acompanha algum partido de perto?</Titulo>
            <Sub>Ajuda a destacar a atuação dessas bancadas. Pode pular.</Sub>
            <View style={st.chipsWrap}>
              {PARTIDOS.map((p) => {
                const on = partidos.includes(p);
                return (
                  <Pressable key={p} onPress={() => toggle(partidos, setPartidos, p)}
                    style={[st.chip, on && { backgroundColor: cor.navy, borderColor: cor.navy }]}>
                    {on ? <Icon name="check" size={14} color={cor.white} /> : null}
                    <Text style={[st.chipTxt, on && { color: cor.white }]}>{p}</Text>
                  </Pressable>
                );
              })}
            </View>
          </>
        )}

        {step === 'sobre' && (
          <>
            <Kicker>SOBRE VOCÊ · OPCIONAL</Kicker>
            <Titulo>Um pouco sobre você</Titulo>
            <Sub>Tudo opcional (LGPD). Ajuda o Aquarius a contextualizar — nunca é exigido e você pode pular.</Sub>

            <Text style={st.campoLabel}>CEP (sua região)</Text>
            <TextInput style={st.campo} value={cep} onChangeText={(t) => setCep(t.replace(/\D/g, '').slice(0, 8))}
              placeholder="00000000" placeholderTextColor={cor.mutedSoft} keyboardType="number-pad" inputMode="numeric" />

            <Text style={st.campoLabel}>Faixa de idade</Text>
            <View style={st.chipsWrap}>
              {['16–24', '25–34', '35–44', '45–59', '60+'].map((f) => (
                <Pressable key={f} onPress={() => setIdade(idade === f ? '' : f)}
                  style={[st.chip, idade === f && { backgroundColor: cor.navy, borderColor: cor.navy }]}>
                  <Text style={[st.chipTxt, idade === f && { color: cor.white }]}>{f}</Text>
                </Pressable>
              ))}
            </View>

            <Text style={st.campoLabel}>Gênero</Text>
            <View style={st.chipsWrap}>
              {['Feminino', 'Masculino', 'Outro', 'Prefiro não dizer'].map((g) => (
                <Pressable key={g} onPress={() => setGenero(genero === g ? '' : g)}
                  style={[st.chip, genero === g && { backgroundColor: cor.navy, borderColor: cor.navy }]}>
                  <Text style={[st.chipTxt, genero === g && { color: cor.white }]}>{g}</Text>
                </Pressable>
              ))}
            </View>
          </>
        )}
      </ScrollView>

      {/* rodapé de ação */}
      <View style={st.rodape}>
        {step === 'sobre' ? (
          <Pressable onPress={avancar} style={st.pular}><Text style={st.pularTxt}>Pular</Text></Pressable>
        ) : null}
        <Pressable onPress={avancar} disabled={!podeAvancar} style={[st.cta, !podeAvancar && { opacity: 0.5 }]}>
          <Text style={st.ctaTxt}>{step === 'sobre' ? 'Concluir' : 'Continuar'}</Text>
          <Icon name="chevR" size={17} color={cor.white} />
        </Pressable>
      </View>
    </View>
  );
}

function Montando() {
  const { cor, st } = useTemaEstilos(criarSt);
  const rot = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.loop(Animated.timing(rot, { toValue: 1, duration: 1100, easing: Easing.linear, useNativeDriver: true })).start();
  }, [rot]);
  const spin = rot.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] });
  return (
    <View style={st.montando}>
      <Animated.View style={{ transform: [{ rotate: spin }], marginBottom: 22 }}>
        <Icon name="spark" size={40} color={cor.white} />
      </Animated.View>
      <Text style={st.montandoTxt}>Montando o seu Congresso…</Text>
    </View>
  );
}

const Kicker = ({ children }: { children: string }) => {
  const { st } = useTemaEstilos(criarSt);
  return <Text style={st.kicker}>{children}</Text>;
};
const Titulo = ({ children }: { children: string }) => {
  const { st } = useTemaEstilos(criarSt);
  return <Text style={st.titulo}>{children}</Text>;
};
const Sub = ({ children }: { children: string }) => {
  const { st } = useTemaEstilos(criarSt);
  return <Text style={st.subtitulo}>{children}</Text>;
};

const criarSt = (cor: Tema) => StyleSheet.create({
  intro: { flex: 1, justifyContent: 'center', paddingHorizontal: 28, backgroundColor: cor.navy },
  introH1: { fontSize: 30, fontFamily: fonte.xb, color: cor.white, lineHeight: 36, letterSpacing: -0.5 },
  introP: { marginTop: 16, fontSize: 15, color: 'rgba(255,255,255,0.75)', lineHeight: 23 },
  introCta: { marginTop: 34, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, backgroundColor: cor.cartao, paddingVertical: 15, borderRadius: 9999 },
  introCtaTxt: { fontFamily: fonte.b, fontSize: 15, color: cor.texto },
  introNota: { marginTop: 14, textAlign: 'center', fontSize: 12, color: 'rgba(255,255,255,0.5)' },

  topo: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 16, paddingTop: 10 },
  progBase: { flex: 1, height: 5, borderRadius: 9999, backgroundColor: cor.light, overflow: 'hidden' },
  progFill: { height: '100%', borderRadius: 9999, backgroundColor: cor.sky },
  progTxt: { fontFamily: fonte.b, fontSize: 11.5, color: cor.muted, width: 34, textAlign: 'right' },

  kicker: { fontFamily: fonte.b, fontSize: 10.5, color: cor.sky, letterSpacing: 1.6 },
  titulo: { marginTop: 8, fontSize: 23, fontFamily: fonte.xb, color: cor.texto, letterSpacing: -0.4, lineHeight: 28 },
  subtitulo: { marginTop: 8, fontSize: 13.5, color: cor.muted, lineHeight: 20 },
  chipsWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 9, marginTop: 16 },
  chip: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 14, paddingVertical: 10, borderRadius: 9999, backgroundColor: cor.cartao, borderWidth: 1.5, borderColor: cor.border },
  chipTxt: { fontFamily: fonte.sb, fontSize: 13.5, color: cor.texto },

  campoLabel: { marginTop: 20, fontFamily: fonte.b, fontSize: 10.5, color: cor.muted, letterSpacing: 1.4, textTransform: 'uppercase' },
  campo: { marginTop: 8, backgroundColor: cor.cartao, borderRadius: raio.input, borderWidth: 1.5, borderColor: cor.border, paddingHorizontal: 14, paddingVertical: 13, fontSize: 15, color: cor.texto, fontFamily: fonte.m },

  rodape: { position: 'absolute', left: 0, right: 0, bottom: 0, flexDirection: 'row', gap: 10, alignItems: 'center', paddingHorizontal: 24, paddingTop: 12, paddingBottom: 28, backgroundColor: cor.surface, borderTopWidth: 1, borderTopColor: cor.border },
  pular: { paddingVertical: 14, paddingHorizontal: 18 },
  pularTxt: { fontFamily: fonte.sb, fontSize: 14, color: cor.muted },
  cta: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, backgroundColor: cor.navy, paddingVertical: 15, borderRadius: 9999 },
  ctaTxt: { fontFamily: fonte.b, fontSize: 14, color: cor.white },

  montando: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: cor.navy },
  montandoTxt: { fontFamily: fonte.sb, fontSize: 14, color: 'rgba(255,255,255,0.8)', letterSpacing: 0.4 },
});
