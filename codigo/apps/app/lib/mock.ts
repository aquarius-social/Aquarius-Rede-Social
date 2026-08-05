/**
 * Dados de PROTÓTIPO para as abas ainda não ingeridas (Proposições, Votações,
 * Presença, Discursos, Agenda, Órgãos). Portados de `aq-foundation.jsx`.
 *
 * ⚠️ São placeholders do design — NÃO são dados reais deste parlamentar. Só
 * Despesas e Emendas leem o banco. Estas abas replicam o layout do Claude
 * Design com o conteúdo-exemplo, até a ingestão dessas áreas voltar (hoje o
 * Free do Supabase está priorizando dinheiro). Ver ESTADO_ATUAL.md.
 */
import { cor } from './tema';

export const PARTIDO_COR: Record<string, string> = {
  PT: '#CC0000', PL: '#1B3A6E', PP: '#0066B3', PSB: '#FFCC00',
  UNIÃO: '#0044CC', PSOL: '#E20613', REPUBLICANOS: '#0E76BC', MDB: '#FF6B00',
  PCdoB: '#C4161C', AVANTE: '#00A0DF', PSD: '#26489F', NOVO: '#FF6B00',
};

/** KPIs de cabeçalho que ainda não temos ingeridos (placeholder do design). */
export const KPI_PLACEHOLDER = { presenca: 92.4, alinhamentoPart: 89, proposicoesAuto: 47 };

export const PROPOSICOES = [
  { id: 'pl1', tipo: 'PL', numero: '1234/2025', ementa: 'Institui a Política Nacional de Educação Integral em Tempo Integral nas redes públicas de ensino básico, com critérios de financiamento e metas de cobertura até 2030.', tema: 'Educação', situacao: 'Em tramitação', dataApres: '14 Mar 2025', resumoIA: true },
  { id: 'pl2', tipo: 'PEC', numero: '78/2024', ementa: 'Altera o art. 212-A da Constituição Federal para tornar permanente o FUNDEB.', tema: 'Educação', situacao: 'Aprovado em 1º turno', dataApres: '02 Abr 2024', resumoIA: true },
  { id: 'pl3', tipo: 'PL', numero: '3287/2025', ementa: 'Dispõe sobre o uso de Inteligência Artificial em ambientes escolares, vedando vigilância biométrica e exigindo supervisão pedagógica.', tema: 'Tecnologia · Educação', situacao: 'Aguardando relator', dataApres: '21 Mai 2025', resumoIA: false },
  { id: 'pl4', tipo: 'REQ', numero: '392/2025', ementa: 'Requerimento de convocação do Ministro da Educação para prestar esclarecimentos sobre a execução do Pé-de-Meia.', tema: 'Educação', situacao: 'Aprovado', dataApres: '08 Fev 2025', resumoIA: false },
  { id: 'pl5', tipo: 'PL', numero: '4521/2024', ementa: 'Regulamenta a prestação de serviços por aplicativos de transporte e entrega, garantindo direitos aos trabalhadores da economia digital.', tema: 'Trabalho', situacao: 'Arquivado', dataApres: '11 Set 2024', resumoIA: false },
  { id: 'pl6', tipo: 'PL', numero: '2089/2026', ementa: 'Cria o Programa Nacional de Letramento em Saúde Mental para adolescentes nas escolas de ensino médio.', tema: 'Saúde · Educação', situacao: 'Em tramitação', dataApres: '19 Mar 2026', resumoIA: true },
];

export const VOTACOES = [
  { id: 'v1', titulo: 'PEC 78/2024 — FUNDEB Permanente · 1º turno', data: '12 Mar 2025', voto: 'Sim', resultado: 'Aprovada' },
  { id: 'v2', titulo: 'PL 1904/2024 — Marco Civil das IAs', data: '08 Out 2024', voto: 'Sim', resultado: 'Aprovada' },
  { id: 'v3', titulo: 'MP 1227/2024 — Compensação Cred. ICMS', data: '25 Jun 2024', voto: 'Não', resultado: 'Aprovada' },
  { id: 'v4', titulo: 'PEC 45/2023 — Reforma Tributária · 2º turno', data: '15 Dez 2023', voto: 'Sim', resultado: 'Aprovada' },
  { id: 'v6', titulo: 'PL 4188/2021 — Marco do Saneamento', data: '17 Mar 2024', voto: 'Não', resultado: 'Aprovada' },
  { id: 'v8', titulo: 'REQ 1023 — Convocação Min. Fazenda', data: '19 Jun 2024', voto: 'Abstenção', resultado: 'Rejeitada' },
];

export const ALINHAMENTO = [
  { label: 'PSB (partido)', pct: 89, color: cor.navy },
  { label: 'Governo Lula', pct: 68, color: cor.sky },
  { label: 'Base oposicionista', pct: 31, color: cor.muted },
  { label: 'Bancada SP', pct: 74, color: cor.blue },
];

export const PRESENCA = [94, 91, 96, 89, 92, 95, 88, 94, 90, 93, 91, 92];
export const PRESENCA_LABELS = ['Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez', 'Jan', 'Fev', 'Mar', 'Abr'];
export const PRESENCA_POR_SESSAO = [
  { label: 'Plenário', pct: 94 },
  { label: 'Comissão de Educação', pct: 97 },
  { label: 'Comissão de CCJ', pct: 84 },
  { label: 'Sessões deliberativas extraord.', pct: 88 },
];

export const DISCURSOS = [
  { id: 'd1', data: '22 Abr 2026', tipo: 'Pequeno Expediente', tema: 'Educação', resumo: 'Cobra do Executivo regulamentação do Pé-de-Meia para 2026 e alerta sobre evasão escolar pós-pandemia.', dur: '8 min' },
  { id: 'd2', data: '17 Abr 2026', tipo: 'Grande Expediente', tema: 'Ciência', resumo: 'Defende reajuste do orçamento da CAPES e critica corte em bolsas de pós-graduação.', dur: '14 min' },
  { id: 'd3', data: '09 Abr 2026', tipo: 'Comissão de Educação', tema: 'IA nas escolas', resumo: 'Apresenta o PL 3287/2025 e discute riscos de vigilância biométrica em sala de aula.', dur: '22 min' },
  { id: 'd4', data: '03 Abr 2026', tipo: 'Pequeno Expediente', tema: 'Juventude', resumo: 'Saúda inclusão da PEC da Juventude no calendário do mês.', dur: '5 min' },
  { id: 'd5', data: '27 Mar 2026', tipo: 'Plenário', tema: 'Reforma do Ensino Médio', resumo: 'Posiciona-se sobre destaques ao PL 5230/2023 e propõe carga horária mínima de matemática.', dur: '11 min' },
];
export const DISCURSO_TEMAS = ['Educação · 24', 'Ciência · 8', 'Juventude · 6', 'Saúde · 4', 'Tributário · 3', 'Outros · 2'];

export const AGENDA = [
  { data: 'Hoje · 14:00', titulo: 'Audiência Pública — Pé-de-Meia 2026', local: 'Anexo II · Plen. 2', tipo: 'Comissão' },
  { data: 'Amanhã · 09:30', titulo: 'Reunião CE — Discussão PL 3287/2025', local: 'Anexo II · Plen. 10', tipo: 'Comissão' },
  { data: 'Qui 28 · 11:00', titulo: 'Lançamento Relatório FPM Educação 2025', local: 'Salão Nobre · Câmara', tipo: 'Evento' },
  { data: 'Sex 29 · 19:00', titulo: 'Sabatina Universidade Federal do ABC', local: 'Santo André — SP', tipo: 'Externa' },
];

export const ORGAOS = [
  { id: 'o1', nome: 'Comissão de Educação (CE)', cargo: 'Membro Titular', cor: '#1A4FA0' },
  { id: 'o2', nome: 'Comissão de Ciência, Tecnologia e Inovação (CCTI)', cargo: '2ª Vice-presidente', cor: '#2E7DD1' },
  { id: 'o3', nome: 'Frente Parlamentar Mista da Educação', cargo: 'Coordenadora Executiva', cor: '#0D2B5E' },
  { id: 'o4', nome: 'Comissão de Defesa dos Direitos da Mulher', cargo: 'Suplente', cor: '#4A6090' },
  { id: 'o5', nome: 'Frente Parlamentar da Juventude', cargo: 'Membro', cor: '#1A4FA0' },
];
