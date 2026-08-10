import { useEffect } from 'react';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { Text } from 'react-native';
import {
  useFonts,
  Inter_400Regular,
  Inter_500Medium,
  Inter_600SemiBold,
  Inter_700Bold,
  Inter_800ExtraBold,
} from '@expo-google-fonts/inter';
import { fonte } from '../lib/tema';
import { TemaProvider, useTema, useTemaCtrl } from '../lib/theme';
import { AuthProvider, useAuth } from '../lib/auth';
import { FollowsProvider } from '../lib/follows';
import { Splash } from '../components/splash';
import { AqHeaderNav } from '../components/header';

// Default global de fonte: prefixa Inter Regular no estilo de TODO <Text>, de
// modo que o texto de corpo (sem peso) use Inter, mas estilos com fontFamily
// explícito (fonte.sb/b/xb…) continuem vencendo por virem depois no array.
// Padrão consagrado de override do render do Text (o protótipo aplica Inter em
// cada elemento; aqui centralizamos num ponto só).
const TextRender = Text as unknown as {
  render?: (props: { style?: unknown }, ref: unknown) => any;
  __aqPatched?: boolean;
};
if (TextRender.render && !TextRender.__aqPatched) {
  const original = TextRender.render;
  // Prefixa a família no ESTILO DE ENTRADA (antes do RNW resolver p/ className).
  // Array de estilo RN é achatado corretamente; peso explícito vem depois e vence.
  TextRender.render = function patched(props: { style?: unknown }, ref: unknown) {
    const merged = { ...props, style: [{ fontFamily: fonte.r }, props?.style] };
    return original.call(this, merged, ref);
  };
  TextRender.__aqPatched = true;
}

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
    Inter_800ExtraBold,
  });

  return (
    <TemaProvider>
      {/* Trava o render até a Inter carregar (evita flash com a fonte do sistema). */}
      {(!fontsLoaded && !fontError) ? (
        <Splash />
      ) : (
        <AuthProvider>
          <FollowsProvider>
            <BarraStatus />
            <Gate />
          </FollowsProvider>
        </AuthProvider>
      )}
    </TemaProvider>
  );
}

/** StatusBar que acompanha o tema (ícones claros no modo escuro). */
function BarraStatus() {
  const { modo } = useTemaCtrl();
  return <StatusBar style={modo === 'dark' ? 'light' : 'dark'} />;
}

/**
 * Gate de rota: sem sessão, só a tela de login é acessível; com sessão, o app
 * inteiro. Enquanto a sessão inicial resolve, mostra o Splash.
 */
function Gate() {
  const cor = useTema();
  const { session, carregando, onboarded } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (carregando) return;
    const emLogin = segments[0] === 'login';
    const emOnboarding = segments[0] === 'onboarding';
    if (!session && !emLogin) {
      router.replace('/login');                         // não logado → login
    } else if (session && !onboarded && !emOnboarding) {
      router.replace('/onboarding');                    // logado sem onboarding → onboarding
    } else if (session && onboarded && (emLogin || emOnboarding)) {
      router.replace('/');                              // já resolvido → app
    }
  }, [session, onboarded, carregando, segments, router]);

  if (carregando) return <Splash />;

  return (
    <Stack
      screenOptions={{
        header: (props) => <AqHeaderNav options={props.options} route={props.route} navigation={props.navigation} />,
        contentStyle: { backgroundColor: cor.surface },
      }}
    >
      <Stack.Screen name="index" options={{ headerShown: false }} />
      <Stack.Screen name="login" options={{ headerShown: false }} />
      <Stack.Screen name="onboarding" options={{ headerShown: false }} />
      <Stack.Screen name="feed" options={{ headerShown: false }} />
      <Stack.Screen name="calendario" options={{ headerShown: false }} />
      <Stack.Screen name="interesses" options={{ headerShown: false }} />
      <Stack.Screen name="prometeus/index" options={{ headerShown: false }} />
      <Stack.Screen name="prometeus/chat" options={{ title: 'Prometeus' }} />
      <Stack.Screen name="configuracoes" options={{ title: 'Configurações' }} />
      <Stack.Screen name="editar-perfil" options={{ title: 'Editar perfil' }} />
      <Stack.Screen name="listagem/[tipo]" options={{ title: 'Explorar' }} />
      <Stack.Screen name="parlamentar/[id]" options={{ title: 'Perfil' }} />
      <Stack.Screen name="partido/[sigla]" options={{ title: 'Partido' }} />
      <Stack.Screen name="comissao/[id]" options={{ title: 'Comissão' }} />
      <Stack.Screen name="frente/[id]" options={{ title: 'Frente' }} />
    </Stack>
  );
}
