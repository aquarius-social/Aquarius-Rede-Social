// ESLint do app (Expo). Base oficial `eslint-config-expo`.
// As regras novas do "React Compiler" (eslint-plugin-react-hooks v5) são
// agressivas demais para React Native e geram falso-positivo em padrões válidos:
//  - react-hooks/refs: acusa `Animated.Value.interpolate()` no render (correto em RN);
//  - set-state-in-effect / immutability: acusam init de provider e afins.
// Mantemos as clássicas valiosas: rules-of-hooks (erro) e exhaustive-deps (aviso).
module.exports = {
  root: true,
  extends: ['expo'],
  ignorePatterns: ['node_modules/', '.expo/', 'dist/', 'web-build/'],
  rules: {
    'react-hooks/refs': 'off',
    'react-hooks/set-state-in-effect': 'off',
    'react-hooks/immutability': 'off',
    'react-hooks/exhaustive-deps': 'warn',
    '@typescript-eslint/array-type': 'off',
  },
};
