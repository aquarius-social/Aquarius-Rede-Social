import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { cor } from '../lib/tema';

export default function RootLayout() {
  return (
    <>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: cor.surface },
          headerTintColor: cor.navy,
          headerTitleStyle: { fontWeight: '800', color: cor.navy },
          contentStyle: { backgroundColor: cor.surface },
        }}
      >
        <Stack.Screen name="index" options={{ title: 'Parlamentares' }} />
        <Stack.Screen name="parlamentar/[id]" options={{ title: 'Perfil' }} />
        <Stack.Screen name="partido/[sigla]" options={{ title: 'Partido' }} />
      </Stack>
    </>
  );
}
