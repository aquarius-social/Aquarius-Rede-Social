// DADOS DE DEMONSTRAÇÃO (usuarios) — TODO: trocar por query real quando o analytics de produto existir.

export const HORA = [0.1, 0.08, 0.06, 0.05, 0.05, 0.07, 0.12, 0.22, 0.35, 0.42, 0.46, 0.5, 0.58, 0.5, 0.46, 0.48, 0.55, 0.7, 0.9, 1.0, 0.85, 0.6, 0.4, 0.2];
export const DIA = [1, 0.98, 0.96, 0.97, 0.92, 0.7, 0.62];

export const DURACAO = [['<1m', 9], ['1–3m', 17], ['3–6m', 26], ['6–10m', 24], ['10–20m', 16], ['>20m', 8]] as const;
export const FUNIL = [['Abriu o app', '62,1K', 100], ['Viu as Stories', '48,9K', 78.7], ['Rolou o feed', '44,2K', 71.1], ['Abriu um perfil/PL', '21,9K', 35.2], ['Comentou ou curtiu', '14,3K', 23]] as const;
export const ADOCAO = [['Feed', 'list', 98], ['Stories da IA', 'star', 81], ['Perfis', 'users', 64], ['Prometeus IA', 'spark', 43]] as const;
