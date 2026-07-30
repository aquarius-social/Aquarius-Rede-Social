/**
 * Camada social — posts, stories, comentários.
 *
 * Duas decisões estruturais estão registradas aqui, ambas vindas da auditoria
 * do protótipo contra a documentação.
 */

import type {
  Completude,
  IsoDateTime,
  Proveniencia,
} from './proveniencia';
import type { PerfilRef } from './perfil';

/**
 * Tipo de post.
 *
 * O protótipo do app usa oito valores em minúsculas; o do admin usa quatro
 * capitalizados. São dois enums para o mesmo campo. Adotamos os oito do app,
 * porque é sobre eles que a interface do feed decide o que renderizar — e a
 * regra do projeto é que o protótipo manda no observável. Os rótulos do admin
 * viram apresentação, não dado.
 */
export type PostTipo =
  | 'acontecendo'
  | 'proposicao'
  | 'votacao'
  | 'emenda'
  | 'discurso'
  | 'agenda'
  | 'tramitacao'
  | 'relatorio';

/**
 * Papel de um perfil num post (recurso "Collab").
 *
 * O papel é dado de negócio, não decoração: num post de votação, "Votou a
 * favor" e "Votou contra" no mesmo card mudam o sentido do que se lê. Um
 * modelo com autor único não representa isso.
 *
 * Sem esta tabela de junção, dois recursos do produto ficam inimplementáveis:
 * o feed "Seguindo" (não há como filtrar posts por perfis seguidos) e a aba
 * "Feed" de cada perfil.
 */
export type PapelNoPost =
  | 'autoria'
  | 'coautoria'
  | 'relatoria'
  | 'votou_a_favor'
  | 'votou_contra'
  | 'absteve_se'
  | 'discursou'
  | 'autoria_emenda'
  | 'organiza'
  | 'participa'
  | 'citado';

export interface PerfilNoPost {
  perfil: PerfilRef;
  papel: PapelNoPost;
  /** Ordem de exibição. O índice 0 é o principal e define o título do card. */
  ordem: number;
}

/**
 * Confiança da geração automática.
 *
 * Deliberadamente `number | null`, nunca 0 como sentinela. No protótipo, um
 * story ainda em geração carrega `aiConf: 0` — e pelo predicado literal da
 * regra (`< 0.65` exige revisão humana), "ainda não calculado" seria lido como
 * "baixa confiança". São coisas diferentes e precisam de representações
 * diferentes.
 */
export type ConfiancaIa = number | null;

/** Limiar de revisão humana obrigatória. */
export const LIMIAR_REVISAO_HUMANA = 0.65;

/**
 * Decide se um item exige revisão humana antes de publicar.
 *
 * Confiança ausente exige revisão: não saber não é o mesmo que confiar.
 */
export function exigeRevisaoHumana(conf: ConfiancaIa): boolean {
  return conf === null || conf < LIMIAR_REVISAO_HUMANA;
}

export type PostStatus =
  | 'rascunho'
  | 'revisao'
  | 'agendado'
  | 'publicado'
  | 'retratado';

export interface PostMetrics {
  likes: number;
  /**
   * Descurtidas.
   *
   * Ausente do DATA-MODEL.md do handoff, presente em todos os posts do
   * protótipo e exigido pelos PRDs ("Like, Dislike e Comentários"). Mantido
   * por decisão de produto.
   */
  dislikes: number;
  comentarios: number;
  compartilhamentos: number;
  alcance: number;
}

export interface Post extends Proveniencia {
  id: string;
  tipo: PostTipo;
  /** Título em terceira pessoa, factual. A IA contextualiza, não opina. */
  titulo: string;
  corpo: string;
  /** Referência ao ato oficial que originou o post. */
  origemTipo: string;
  origemId: string;
  /** Os perfis vinculados, com papel. Índice 0 é o principal. */
  perfis: PerfilNoPost[];
  status: PostStatus;
  confiancaIa: ConfiancaIa;
  completude: Completude;
  geradoEm: IsoDateTime;
  publicadoEm: IsoDateTime | null;
  metrics: PostMetrics;
  /** Já existe resumo do Prometeus para a matéria vinculada. */
  temResumoIa: boolean;
}

export type StoryTipo = 'panorama' | 'perfil' | 'tema' | 'orgao' | 'partido';

export interface StoryCard {
  kicker: string;
  texto: string;
  tom: 'navy' | 'sky';
}

export interface Story extends Proveniencia {
  id: string;
  tipo: StoryTipo;
  titulo: string;
  cards: StoryCard[];
  status: 'gerando' | 'revisao' | 'publicado' | 'expirado';
  confiancaIa: ConfiancaIa;
  publicadoEm: IsoDateTime | null;
  /** Stories duram 24 h. */
  expiraEm: IsoDateTime;
  aberturas: number;
  conclusaoPct: number;
}

export interface Comentario {
  id: string;
  postId: string;
  /** Nulo em comentário raiz; preenchido em resposta (thread de um nível). */
  paiId: string | null;
  autorId: string;
  autorNome: string;
  autorUf: string | null;
  /**
   * Distingue comentário de pessoa de intervenção do Prometeus.
   *
   * No protótipo, o Prometeus responde dentro de uma thread como se fosse um
   * usuário, e nada no dado marca a diferença. Numa plataforma cuja promessa é
   * separar o que a IA disse do que o Congresso escreveu, essa distinção
   * precisa existir no modelo, não só no visual.
   */
  autorEhIa: boolean;
  texto: string;
  likes: number;
  criadoEm: IsoDateTime;
  respostas?: Comentario[];
}

export type AlvoSeguivel = 'perfil' | 'tema' | 'proposicao';

export interface Follow {
  usuarioId: string;
  alvoTipo: AlvoSeguivel;
  /** Chave global — por isso a tabela mãe de perfis existe. */
  alvoId: string;
  criadoEm: IsoDateTime;
}
