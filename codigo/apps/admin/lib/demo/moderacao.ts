// DADOS DE DEMONSTRAÇÃO (moderacao) — TODO: trocar por query real quando a camada social + auth de usuários existir.
export type Motivo = 'desinformação' | 'assédio' | 'spam' | 'discurso de ódio';
export type Sev = 'alta' | 'crítica' | 'baixa';
export const DENUNCIAS: { tipo: string; motivo: Motivo; sev: Sev; flags: number; texto: string; autor: string; ctx: string; ia: number }[] = [
  { tipo: 'Comentário', motivo: 'desinformação', sev: 'alta', flags: 14, texto: 'Isso é tudo mentira, esse deputado nunca votou assim, fake news!', autor: 'Anderson M. · MG', ctx: 'em Post · PEC 78/2024 (FUNDEB)', ia: 81 },
  { tipo: 'Comentário', motivo: 'assédio', sev: 'crítica', flags: 23, texto: 'Vai ver no que dá quando a gente souber onde você mora…', autor: 'perfil_anon_4471', ctx: 'em Post · Erika Hilton · discurso', ia: 94 },
  { tipo: 'Comentário', motivo: 'spam', sev: 'baixa', flags: 8, texto: 'COMPRE SEGUIDORES BARATO link na bio promoção imperdível', autor: 'midia_promo_oficial', ctx: 'em Post · PSB · emendas', ia: 97 },
  { tipo: 'Post', motivo: 'discurso de ódio', sev: 'alta', flags: 11, texto: 'Conteúdo com ataque direcionado a grupo — retido para conferência editorial.', autor: 'conta_removida', ctx: 'em Post · gerado por usuário', ia: 88 },
];
export const MOTIVOS = [['Spam', 46], ['Desinformação', 25], ['Discurso de ódio', 16], ['Assédio', 13]] as const;
export const ACAO = [
  { av: 'P', nome: 'perfil_anon_4471', motivo: 'Assédio reincidente', status: 'suspenso', tone: 'warn' as const, n: 38 },
  { av: 'B', nome: 'bot_corrente_77', motivo: 'Spam automatizado', status: 'banido', tone: 'neg' as const, n: 46 },
  { av: 'M', nome: 'midia_promo_oficial', motivo: 'Spam comercial', status: 'suspenso', tone: 'warn' as const, n: 19 },
  { av: 'JD', nome: 'José da Silva', motivo: 'Discurso de ódio · 2ª ocorrência', status: 'advertido', tone: 'muted' as const, n: 14 },
];
