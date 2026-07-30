/**
 * Usuário da rede social, preferências e consentimento.
 *
 * Uma decisão estrutural está registrada aqui: o consentimento nasce junto do
 * usuário, não é adicionado quando o DaaS for construído.
 *
 * Motivo: base legal não é retroativa. Evento de engajamento gravado sem
 * finalidade declarada e sem consentimento vinculado é evento que não pode ser
 * usado depois — e, dependendo da leitura, não deveria ter sido coletado. Por
 * isso os tipos de consentimento existem desde a fundação, mesmo com a tela de
 * audiências ainda distante no plano.
 */

import type { IsoDate, IsoDateTime } from './proveniencia';
import type { CategoriaVerificacao } from './perfil';

export type Plano = 'free' | 'premium' | 'b2b';

/**
 * Finalidade declarada de tratamento.
 *
 * O consentimento não é um booleano global: a LGPD exige finalidade
 * específica. Consentir com recomendação de conteúdo não é consentir com
 * inclusão em recorte de audiência vendido a terceiro.
 */
export type FinalidadeTratamento =
  | 'personalizacao_feed'
  | 'notificacoes'
  | 'audiencias_agregadas'
  | 'pesquisa_academica';

export interface Consentimento {
  finalidade: FinalidadeTratamento;
  concedido: boolean;
  concedidoEm: IsoDateTime | null;
  /**
   * Revogação. O opt-out precisa ser de um toque e aplicado em até 24 horas
   * em todos os produtos.
   */
  revogadoEm: IsoDateTime | null;
  /** Versão do texto de consentimento aceito. Necessária para auditoria. */
  versaoTermo: string;
}

/** Preferências do onboarding cold-start. */
export interface PreferenciasOnboarding {
  temas: string[];
  partidosPerfilIds: string[];
  cep: string | null;
  uf: string | null;
  faixaEtaria: string | null;
  genero: string | null;
}

/**
 * Dados opcionais do perfil.
 *
 * Todos anuláveis, todos coletados apenas pelo nudge de "completar perfil".
 * Princípio inegociável do projeto: opt-in, sutil, sem fricção, nunca
 * obrigatório.
 *
 * Nota de escopo em aberto: estes campos existem no protótipo e sustentam as
 * dimensões socioeconômicas do motor de audiências, mas a Concepção do Produto
 * descreve o DaaS apenas como "engajamento por tema e por região". Há uma
 * diferença real de ambição e de risco entre as duas versões, e ela ainda não
 * foi decidida.
 */
export interface PerfilOpcional {
  escolaridade: string | null;
  faixaRenda: string | null;
  ocupacao: string | null;
}

export interface Usuario {
  id: string;
  nome: string;
  /** Sempre mascarado nas respostas de API. */
  telefoneMascarado: string | null;
  plano: Plano;
  prefs: PreferenciasOnboarding;
  perfilOpcional: PerfilOpcional;
  consentimentos: Consentimento[];
  criadoEm: IsoDateTime;
}

/** Verifica consentimento vigente para uma finalidade. */
export function consenteCom(
  u: Usuario,
  finalidade: FinalidadeTratamento
): boolean {
  const c = u.consentimentos.find((x) => x.finalidade === finalidade);
  return !!c && c.concedido && c.revogadoEm === null;
}

/** Completude do perfil, para o anel de progresso do app. */
export function completudePerfil(u: Usuario): {
  pct: number;
  faltando: string[];
} {
  const campos: [string, unknown][] = [
    ['temas', u.prefs.temas.length ? true : null],
    ['regiao', u.prefs.cep ?? u.prefs.uf],
    ['faixaEtaria', u.prefs.faixaEtaria],
    ['genero', u.prefs.genero],
    ['escolaridade', u.perfilOpcional.escolaridade],
    ['faixaRenda', u.perfilOpcional.faixaRenda],
    ['ocupacao', u.perfilOpcional.ocupacao],
  ];
  const faltando = campos.filter(([, v]) => !v).map(([k]) => k);
  return {
    pct: Math.round(((campos.length - faltando.length) / campos.length) * 100),
    faltando,
  };
}

// -----------------------------------------------------------------------------
// Verificação (selo azul)
// -----------------------------------------------------------------------------

export type StatusVerificacao =
  | 'nao_solicitada'
  | 'em_analise'
  | 'aprovada'
  | 'recusada'
  | 'revogada';

/**
 * Pedido de verificação por identidade real.
 *
 * A regra de elegibilidade é de neutralidade, não de produto: a verificação é
 * vedada a parlamentares e partidos porque quem é objeto do acompanhamento não
 * recebe selo de destaque dentro dele.
 */
export interface PedidoVerificacao {
  id: string;
  usuarioId: string;
  categoria: CategoriaVerificacao;
  status: StatusVerificacao;
  solicitadoEm: IsoDateTime;
  decididoEm: IsoDateTime | null;
  revisorId: string | null;
  motivoRecusa: string | null;
}

// -----------------------------------------------------------------------------
// Engajamento
// -----------------------------------------------------------------------------

export type AcaoEngajamento =
  | 'view'
  | 'like'
  | 'dislike'
  | 'comment'
  | 'share'
  | 'save'
  | 'follow'
  | 'open_profile'
  | 'ask_ai'
  | 'search';

/**
 * Evento de engajamento.
 *
 * Carrega a finalidade sob a qual foi coletado. É o que permite, mais tarde,
 * filtrar a base de uma análise por consentimento sem precisar reconstruir
 * história — e o que torna o opt-out efetivo de verdade.
 */
export interface EventoEngajamento {
  id: string;
  usuarioId: string;
  ts: IsoDateTime;
  acao: AcaoEngajamento;
  objetoTipo: 'perfil' | 'tema' | 'proposicao' | 'post' | 'story';
  objetoId: string;
  sessaoId: string;
  dispositivo: 'ios' | 'android' | 'web';
  finalidades: FinalidadeTratamento[];
}

export interface Sessao {
  id: string;
  usuarioId: string;
  iniciadaEm: IsoDateTime;
  encerradaEm: IsoDateTime | null;
  duracaoSegundos: number | null;
  telasVistas: number;
  dispositivo: 'ios' | 'android' | 'web';
  data: IsoDate;
}
