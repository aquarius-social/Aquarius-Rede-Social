import type { Contagens } from './dados';

// Fonte única dos pipelines (usada na Visão geral e na tela Pipelines).
// `reg` retorna a contagem REAL da base (ou null quando a área está fora).
export type EstadoPipe = 'ok' | 'parcial' | 'fora';
export interface Pipe {
  id: string; nome: string; fonte: string; freq: string; estado: EstadoPipe;
  reg: (c: Contagens, desp: number) => number | null; obs?: string;
}

export const PIPES: Pipe[] = [
  { id: 'despesas', nome: 'Despesas (Cota)', fonte: 'Câmara · Senado · CSV', freq: 'Semanal', estado: 'parcial', reg: (_c, d) => d, obs: 'CEAP da Câmara completa; CEAPS do Senado sem 2026 (truncado por espaço no Free).' },
  { id: 'emendas', nome: 'Emendas', fonte: 'Portal da Transparência', freq: 'Semanal', estado: 'ok', reg: (c) => c.emendas },
  { id: 'agenda', nome: 'Agenda / eventos', fonte: 'API Câmara · Senado', freq: 'Diário', estado: 'ok', reg: (c) => c.eventos },
  { id: 'orgaos', nome: 'Comissões & Frentes', fonte: 'API Câmara', freq: 'Diário', estado: 'ok', reg: (c) => c.comissoes + c.frentes },
  { id: 'perfis', nome: 'Parlamentares & partidos', fonte: 'API Câmara · Senado', freq: 'Diário', estado: 'ok', reg: (c) => c.parlamentares + c.partidos },
  { id: 'proposicoes', nome: 'Proposições', fonte: 'API Câmara · Senado', freq: '—', estado: 'fora', reg: () => null, obs: 'Coletor pronto, truncado da base atual (⛔ precisa Supabase Pro).' },
  { id: 'votacoes', nome: 'Votações nominais', fonte: 'API Câmara · Senado', freq: '—', estado: 'fora', reg: () => null, obs: 'Coletor pronto, truncado (⛔Pro). É o "como cada um votou".' },
  { id: 'presenca', nome: 'Presença', fonte: '(sem coletor ainda)', freq: '—', estado: 'fora', reg: () => null, obs: 'Ainda não há coletor de presença (Câmara + Senado).' },
  { id: 'discursos', nome: 'Discursos', fonte: 'API Câmara · Senado', freq: '—', estado: 'fora', reg: () => null, obs: 'Coletor pronto, truncado (⛔Pro).' },
  { id: 'posts', nome: 'Geração de posts · feed', fonte: 'IA · Prometeus', freq: '—', estado: 'fora', reg: () => null, obs: 'Depende do agente Prometeus, que ainda não foi ligado.' },
  { id: 'stories', nome: 'Stories diárias · IA', fonte: 'IA · Prometeus', freq: '—', estado: 'fora', reg: () => null, obs: 'Depende do agente Prometeus.' },
  { id: 'sumariza', nome: 'Sumarização IA · PLs', fonte: 'IA · Prometeus', freq: '—', estado: 'fora', reg: () => null, obs: 'Depende do agente Prometeus.' },
];

export function saudePipelines() {
  return {
    ok: PIPES.filter((p) => p.estado === 'ok').length,
    parcial: PIPES.filter((p) => p.estado === 'parcial').length,
    fora: PIPES.filter((p) => p.estado === 'fora').length,
    total: PIPES.length,
  };
}
