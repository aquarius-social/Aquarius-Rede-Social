/**
 * DADOS DE DEMONSTRAÇÃO (placeholders) — centralizados de propósito.
 *
 * Cada tela do admin lê os valores que ainda não temos daqui. Quando a fonte
 * real existir (agente Prometeus, analytics de produto, camada social, tabelas
 * de admin), basta trocar o corpo destas funções por uma query real — as TELAS
 * não mudam. Ver os `// TODO` de cada bloco. Marcadas na UI com o selo "amostra".
 */
import type { IconName } from '../components/Icon';

export interface KpiDemo { label: string; value: string; sub: string; delta?: number; trend?: number[]; icon: IconName }

// TODO(analytics + agente): DAU/uso vêm do analytics de produto; consultas do agente Prometeus.
export const KPIS_VISAO: KpiDemo[] = [
  { label: 'Usuários ativos · DAU', value: '18,4K', sub: '62,2K 7d · 148,3K 30d', delta: 8.7, trend: [120, 128, 134, 141, 149, 156, 162, 166], icon: 'users' },
  { label: 'Consultas Prometeus · 24h', value: '4,8K', sub: '49,3K no mês', delta: 11.3, trend: [3.1, 3.4, 3.7, 3.9, 4.2, 4.5, 4.8], icon: 'spark' },
  { label: 'Posts publicados · hoje', value: '284', sub: 'atos oficiais convertidos em posts', delta: 6.2, trend: [210, 228, 240, 255, 268, 276, 284], icon: 'list' },
  { label: 'Engajamento do feed', value: '7.8%', sub: '38,1K comentários · 24h', delta: 0.6, trend: [6.9, 7.0, 7.2, 7.4, 7.5, 7.7, 7.8], icon: 'spark' },
];

// TODO(analytics): atividade horária real (sessões + perguntas ao agente).
export const ATIVIDADE_APP = {
  total: '21,2K',
  serie: [560, 540, 520, 510, 515, 560, 640, 780, 980, 1100, 1180, 1240, 1300, 1240, 1180, 1200, 1280, 1360, 1400, 1380, 1200, 980, 760, 600],
  labels: ['00:00', '', '', '03:00', '', '', '06:00', '', '', '09:00', '', '', '12:00', '', '', '15:00', '', '', '18:00', '', '', '21:00', '', '23:00'],
};

// TODO(monitoring): uptime/erros reais do sistema.
export const SAUDE_STATS = { uptime: '99.94', erros: '0.18' };

// TODO(agente + analytics): stories geradas pelo Prometeus + aberturas/conclusão reais.
export const STORIES_KPIS: KpiDemo[] = [
  { label: 'Edições · hoje', value: '6', sub: '4 publicadas · 2 em produção', icon: 'star' },
  { label: 'Aberturas · 24h', value: '92,4K', sub: 'trilha no topo do feed', delta: 12.1, trend: [70, 74, 78, 82, 86, 90, 92], icon: 'eye' },
  { label: 'Taxa de conclusão', value: '71%', sub: 'usuários que veem até o fim', delta: 2.4, icon: 'trend' },
  { label: 'Tempo médio', value: '3m 48s', sub: 'por trilha completa', delta: 1.1, icon: 'cal' },
];
export const STORIES_PRODUCAO: { icon: IconName; titulo: string; tipo: string; sub: string; estado: 'revisar' | 'gerando' }[] = [
  { icon: 'star', titulo: 'PSB · bancada na semana', tipo: 'Partido', sub: '1 card · gerado pelo Tentáculo D', estado: 'revisar' },
  { icon: 'spark', titulo: 'O dia no Congresso · 24 Mai', tipo: 'Panorama', sub: '3 cards · gerado pelo Tentáculo D', estado: 'gerando' },
];
export const STORIES_PUBLICADAS: { titulo: string; tipo: string; aberturas: string; conclusao: number; conf: number; quando: string }[] = [
  { titulo: 'O dia no Congresso · 23 Mai', tipo: 'Panorama', aberturas: '38,4K', conclusao: 74, conf: 91, quando: 'há 1h' },
  { titulo: 'Tabata Amaral · atividade de hoje', tipo: 'Perfil', aberturas: '12,2K', conclusao: 68, conf: 86, quando: 'há 58min' },
  { titulo: '#FUNDEB em alta', tipo: 'Tema', aberturas: '9,6K', conclusao: 71, conf: 83, quando: 'há 55min' },
  { titulo: 'CCJC · decisões de hoje', tipo: 'Órgão', aberturas: '5,2K', conclusao: 66, conf: 80, quando: 'há 52min' },
];

// TODO(agente): telemetria real do Prometeus (custo, tokens, latência, temas).
export const PROMETEUS_KPIS: KpiDemo[] = [
  { label: 'Perguntas · 30d', value: '142.8K', sub: '4,8K hoje · pico às 14h', delta: 11.3, trend: [100, 108, 116, 124, 130, 136, 143], icon: 'spark' },
  { label: 'Custo · 30d', value: 'R$ 2.312', sub: 'OpenAI: R$ 1.984 · Anthropic: R$ 328', delta: 4.8, trend: [60, 72, 65, 80, 70, 88, 76], icon: 'trend' },
  { label: 'Tokens · entrada', value: '48,2M', sub: 'média 3,4K por pergunta', delta: 12.1, icon: 'upload' },
  { label: 'Tokens · saída', value: '9,7M', sub: 'média 680 por resposta', delta: 8.4, icon: 'download' },
];
export const PROMETEUS_CUSTO = {
  media: 'R$ 76,18',
  serie: [50, 72, 74, 58, 68, 78, 72, 80, 78, 70, 62, 58, 55, 52, 70, 50, 48, 48, 74, 82, 88, 94, 70, 68, 78, 82],
  labels: ['24d', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '4d', '', '', '', '', ''],
};
export const PROMETEUS_LATENCIA: { label: string; v: string; pct: number; tone: 'pos' | 'warn' | 'neg' }[] = [
  { label: 'p50', v: '1,2s', pct: 24, tone: 'pos' },
  { label: 'p75', v: '2,1s', pct: 42, tone: 'pos' },
  { label: 'p95', v: '4,8s', pct: 78, tone: 'warn' },
  { label: 'p99', v: '9,4s', pct: 96, tone: 'neg' },
];
export const PROMETEUS_DISTRIBUICAO: { tema: string; n: string; pct: number }[] = [
  { tema: 'Votações de parlamentar específico', n: '1.842', pct: 23.8 },
  { tema: 'Resumo / análise de PL', n: '1.421', pct: 18.3 },
  { tema: 'Emendas por município ou estado', n: '988', pct: 12.7 },
  { tema: 'Comparação entre partidos', n: '742', pct: 9.6 },
  { tema: 'Despesas (cota parlamentar)', n: '681', pct: 8.8 },
  { tema: 'Relatórios B2B customizados', n: '459', pct: 5.9 },
];

// TODO(analytics): engajamento real (DAU/WAU/MAU, coortes, perfis/buscas).
export const ENGAJAMENTO_KPIS: KpiDemo[] = [
  { label: 'DAU', value: '18,4K', sub: 'ativos hoje', delta: 8.7, trend: [12, 13, 14, 15, 16, 17, 18], icon: 'users' },
  { label: 'WAU', value: '62,2K', sub: 'ativos 7 dias', delta: 12.4, trend: [48, 51, 54, 56, 58, 60, 62], icon: 'users' },
  { label: 'MAU', value: '148,3K', sub: 'ativos 30 dias', delta: 18.6, trend: [110, 118, 126, 133, 140, 145, 148], icon: 'users' },
  { label: 'Sessão média', value: '6m 42s', sub: 'iOS: 7m 12s · Android: 6m 04s', delta: 3.2, icon: 'trend' },
];
export const RETENCAO_COORTE: { semana: string; cohort: string; d1: number; d7: number; d30: number | null }[] = [
  { semana: 'Abr 06', cohort: '6.840', d1: 71, d7: 42, d30: 24 },
  { semana: 'Abr 13', cohort: '7.212', d1: 69, d7: 40, d30: 23 },
  { semana: 'Abr 20', cohort: '7.888', d1: 72, d7: 43, d30: 25 },
  { semana: 'Abr 27', cohort: '8.120', d1: 68, d7: 41, d30: 23 },
  { semana: 'Mai 04', cohort: '9.210', d1: 70, d7: 42, d30: 22 },
  { semana: 'Mai 11', cohort: '9.842', d1: 67, d7: 39, d30: 22 },
  { semana: 'Mai 18', cohort: '10.412', d1: 68, d7: 41, d30: null },
];
export const PERFIS_CONSULTADOS: { av: string; nome: string; sub: string; valor: string; delta: string }[] = [
  { av: 'TA', nome: 'Tabata Amaral', sub: 'PSB-SP', valor: '84,2K', delta: '+12.3%' },
  { av: 'HM', nome: 'Hugo Motta', sub: 'REPUBLICANOS-PB', valor: '71,4K', delta: '+8.4%' },
  { av: 'NF', nome: 'Nikolas Ferreira', sub: 'PL-MG', valor: '63,1K', delta: '+15.2%' },
  { av: 'EH', nome: 'Erika Hilton', sub: 'PSOL-SP', valor: '58,7K', delta: '+6.1%' },
];
export const BUSCAS_FREQUENTES: { termo: string; valor: string; delta: string }[] = [
  { termo: 'reforma tributária', valor: '14,2K', delta: '+8.4%' },
  { termo: 'pé-de-meia', valor: '11,4K', delta: '+22.1%' },
  { termo: 'tabata amaral', valor: '8,1K', delta: '+5.6%' },
  { termo: 'emendas 2026', valor: '6,9K', delta: '+11.0%' },
];

// TODO(DaaS/escala): audiências agregadas reais (k-anon, consentimento em escala).
export const AUDIENCIAS_KPIS: KpiDemo[] = [
  { label: 'Perfis 100% completos', value: '38%', sub: '63,0K membros · induzido no app', delta: 5.2, trend: [30, 32, 34, 35, 36, 37, 38], icon: 'users' },
  { label: 'Consentimento DaaS', value: '71%', sub: 'base elegível para análises', delta: 2.3, icon: 'check' },
  { label: 'Relatórios · 30d', value: '412', sub: 'prontos + sob demanda', delta: 22.4, icon: 'doc' },
  { label: 'Receita DaaS · mês', value: 'R$ 60.8K', sub: 'audiências agregadas', delta: 14.2, icon: 'trend' },
];
export const AUDIENCIAS_BARRAS: { regiao: string; engajado: number; base: number; index: number }[] = [
  { regiao: 'Norte', engajado: 7.1, base: 8, index: 89 },
  { regiao: 'Nordeste', engajado: 27.2, base: 27, index: 101 },
  { regiao: 'Centro-Oeste', engajado: 7.8, base: 9, index: 87 },
  { regiao: 'Sudeste', engajado: 44.5, base: 42, index: 106 },
  { regiao: 'Sul', engajado: 13.4, base: 14, index: 95 },
];
export const AUDIENCIAS_PRONTAS: { icon: IconName; titulo: string; badge?: string }[] = [
  { icon: 'globe', titulo: 'Engajamento por região × tema', badge: 'Destaque' },
  { icon: 'flag', titulo: 'Afinidade partidária por faixa etária', badge: 'Popular' },
  { icon: 'trend', titulo: 'Tendência de interesse · reforma tributária' },
  { icon: 'users', titulo: 'Perfil socioeconômico dos seguidores' },
  { icon: 'spark', titulo: 'Temas em alta por município' },
];

// TODO(agente): temas realmente perguntados ao Prometeus nos últimos 30 dias.
export const TOP_TEMAS: { label: string; valor: string; pct: number }[] = [
  { label: 'Votações de parlamentar específico', valor: '1,8K', pct: 23.8 },
  { label: 'Resumo / análise de PL', valor: '1,4K', pct: 18.3 },
  { label: 'Emendas por município ou estado', valor: '988', pct: 12.7 },
  { label: 'Comparação entre partidos', valor: '742', pct: 9.6 },
  { label: 'Despesas (cota parlamentar)', valor: '681', pct: 8.8 },
  { label: 'Relatórios B2B customizados', valor: '459', pct: 5.9 },
];
