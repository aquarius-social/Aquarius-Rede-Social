import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { View, Text } from 'react-native';
import {
  useFonts,
  Inter_400Regular,
  Inter_500Medium,
  Inter_600SemiBold,
  Inter_700Bold,
  Inter_800ExtraBold,
} from '@expo-google-fonts/inter';
import { cor, fonte } from '../lib/tema';

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

  // Trava o render até a Inter carregar (evita flash com a fonte do sistema).
  // Se der erro no carregamento, segue mesmo assim para não travar o app.
  if (!fontsLoaded && !fontError) {
    return <View style={{ flex: 1, backgroundColor: cor.surface }} />;
  }

  return (
    <>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: cor.surface },
          headerTintColor: cor.navy,
          headerTitleStyle: { fontFamily: 'Inter_800ExtraBold', color: cor.navy },
          contentStyle: { backgroundColor: cor.surface },
        }}
      >
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen name="listagem/[tipo]" options={{ title: 'Explorar' }} />
        <Stack.Screen name="parlamentar/[id]" options={{ title: 'Perfil' }} />
        <Stack.Screen name="partido/[sigla]" options={{ title: 'Partido' }} />
        <Stack.Screen name="comissao/[id]" options={{ title: 'Comissão' }} />
        <Stack.Screen name="frente/[id]" options={{ title: 'Frente' }} />
      </Stack>
    </>
  );
}
