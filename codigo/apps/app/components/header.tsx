/**
 * AqHeader — barra de topo do app, fiel ao protótipo. Duas variantes:
 *   • home     — logo/wordmark AQUARIUS à esquerda + (sino opcional) + avatar à direita.
 *                Usada nas telas de aba (Feed, Explorar, Prometeus, Interesses, Calendário).
 *   • detalhe  — botão voltar + título centralizado + avatar à direita.
 *                Usada nas telas de pilha via `AqHeaderNav` (option `header` do Stack).
 *
 * Respeita a safe-area (notch) e o tema ativo (claro/escuro). O avatar abre
 * Configurações; o voltar usa a navegação. Substitui o header nativo do
 * @react-navigation (que saía em Inter SemiBold, sem logo/avatar).
 */
import { View, Text, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTema } from '../lib/theme';
import { useAuth } from '../lib/auth';
import { fonte } from '../lib/tema';
import { Logo, Avatar, Icon } from './base';

export function AqHeader({ variant = 'home', title, bell = false, onBell, canGoBack = true, onBack }: {
  variant?: 'home' | 'detalhe';
  title?: string;
  bell?: boolean;
  onBell?: () => void;
  canGoBack?: boolean;
  onBack?: () => void;
}) {
  const cor = useTema();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { session, prefs } = useAuth();
  const nome = prefs.nome || session?.user?.email?.split('@')[0] || 'Você';

  return (
    <View style={{ paddingTop: insets.top, backgroundColor: cor.surface, borderBottomWidth: 1, borderBottomColor: cor.border }}>
      <View style={{ height: 52, flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, gap: 10 }}>
        {variant === 'detalhe' ? (
          <>
            {canGoBack ? (
              <Pressable onPress={onBack ?? (() => router.back())} hitSlop={8} style={{ padding: 4, marginLeft: -4 }}>
                <Icon name="back" size={22} color={cor.texto} />
              </Pressable>
            ) : <View style={{ width: 22 }} />}
            <Text numberOfLines={1} style={{ flex: 1, textAlign: 'center', fontFamily: fonte.xb, fontSize: 17, color: cor.texto, letterSpacing: -0.3 }}>
              {title ?? ''}
            </Text>
            <Pressable onPress={() => router.push('/configuracoes')} hitSlop={6}><Avatar nome={nome} size={32} /></Pressable>
          </>
        ) : (
          <>
            <Logo height={23} />
            <View style={{ flex: 1 }} />
            {bell ? (
              <Pressable onPress={onBell} hitSlop={6} style={{ padding: 4 }} accessibilityLabel="Notificações">
                <Icon name="bell" size={18} color={cor.texto} />
              </Pressable>
            ) : null}
            <Pressable onPress={() => router.push('/configuracoes')} hitSlop={6}><Avatar nome={nome} size={34} /></Pressable>
          </>
        )}
      </View>
    </View>
  );
}

/** Forma mínima das props que o Stack passa para a option `header`. */
interface HeaderNavProps {
  options: { title?: string };
  route: { name: string };
  navigation: { canGoBack: () => boolean; goBack: () => void };
}

/** Wrapper para `screenOptions.header` do Stack — telas de detalhe. */
export function AqHeaderNav({ options, route, navigation }: HeaderNavProps) {
  return (
    <AqHeader
      variant="detalhe"
      title={options.title ?? route.name}
      canGoBack={navigation.canGoBack()}
      onBack={() => navigation.goBack()}
    />
  );
}
