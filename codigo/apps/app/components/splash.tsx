import { useEffect, useRef } from 'react';
import { View, Text, Animated, Easing, StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { cor, fonte } from '../lib/tema';
import { Logo } from './base';

/**
 * Splash — porte fiel de AqSplashScreen (aq-screens-1.jsx): fundo navy, logo
 * branca (símbolo + wordmark) e barra de carregamento. Mostrado enquanto a
 * sessão/fontes resolvem. Animações em Animated (RN não tem @keyframes CSS).
 */
export function Splash() {
  const barra = useRef(new Animated.Value(0)).current;
  const pulso = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.loop(
      Animated.timing(barra, { toValue: 1, duration: 1400, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
    ).start();
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulso, { toValue: 1, duration: 2000, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        Animated.timing(pulso, { toValue: 0, duration: 2000, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      ]),
    ).start();
  }, [barra, pulso]);

  const translate = barra.interpolate({ inputRange: [0, 1], outputRange: [-140, 140] });
  const flutua = pulso.interpolate({ inputRange: [0, 1], outputRange: [0, -6] });

  return (
    <View style={st.wrap}>
      <LinearGradient
        colors={['#1A4FA0', '#0D2B5E', '#08204A']}
        locations={[0, 0.56, 1]}
        start={{ x: 0.5, y: 0.1 }}
        end={{ x: 0.5, y: 1 }}
        style={StyleSheet.absoluteFill}
      />
      <Animated.View style={{ transform: [{ translateY: flutua }] }}>
        <Logo height={40} dark />
      </Animated.View>

      <View style={st.barraBase}>
        <Animated.View style={[st.barraLuz, { transform: [{ translateX: translate }] }]} />
      </View>
      <Text style={st.caption}>CARREGANDO DADOS DO CONGRESSO</Text>
    </View>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: cor.navy },
  barraBase: {
    position: 'absolute', bottom: 84, width: 130, height: 3, borderRadius: 9999,
    backgroundColor: 'rgba(255,255,255,0.16)', overflow: 'hidden',
  },
  barraLuz: { position: 'absolute', top: 0, bottom: 0, width: 57, borderRadius: 9999, backgroundColor: cor.skySoft },
  caption: {
    position: 'absolute', bottom: 54, fontSize: 11.5, fontFamily: fonte.sb,
    letterSpacing: 1.4, color: 'rgba(255,255,255,0.55)',
  },
});
