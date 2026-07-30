/**
 * Proveniência, frescor e confiança.
 *
 * A Metodologia de Dados exige que a camada servida carregue "rótulos de
 * proveniência, completude e frescor embutidos, os mesmos que o contrato de
 * resposta (seção 20) obriga a exibir".
 *
 * Isto não é metadado opcional: as regras 1, 2, 3 e 7 do contrato de resposta
 * do Prometeus só são cumpríveis se estes campos viajarem junto do dado até a
 * tela.
 */

/** Data e hora em ISO-8601. Convenção fixada no contrato de API. */
export type IsoDateTime = string;
/** Data em ISO-8601 (AAAA-MM-DD). */
export type IsoDate = string;

/** Fonte oficial de um fato. */
export type FonteOficial =
  | 'camara'
  | 'senado'
  | 'congresso'
  | 'portal_transparencia';

/**
 * Carimbo de proveniência.
 *
 * Todo fato cívico carrega este bloco. Sem ele, o post não pode ser publicado
 * (princípio inegociável: "tudo de fonte oficial; sem fonte, não publica") e o
 * Prometeus não pode responder (regra 1: declarar a fonte e a data do dado).
 */
export interface Proveniencia {
  fonte: FonteOficial;
  fonteUrl: string | null;
  /** Instante da coleta. É o que sustenta o rótulo de frescor na tela. */
  sincronizadoEm: IsoDateTime;
}

/**
 * Grau declarado de uma ligação de identidade.
 *
 * Decorre do número de sinais independentes que convergiram (Metodologia,
 * seção 5.3). Espelha o enum `grau_confianca` da migration 0001.
 */
export type GrauConfianca = 'direto' | 'com_ressalva' | 'recusado';

/**
 * Base de uma atribuição que não veio direto da fonte.
 *
 * A regra 2 do contrato de resposta obriga o oráculo a "declarar a base da
 * atribuição quando o vínculo não for direto: por quais sinais convergentes a
 * ligação foi estabelecida". Este objeto é o que torna isso possível.
 */
export interface BaseAtribuicao {
  grau: GrauConfianca;
  /** Ex.: ['nome_civil', 'data_nascimento']. */
  sinais: string[];
  /** Preenchido quando grau é 'recusado'. */
  divergencia?: string;
}

/**
 * Completude de um recorte de dado.
 *
 * A regra 3 do contrato exige "distinguir ausência de registro de inexistência
 * do fato, informando a data do último registro conhecido". Um número agregado
 * sem este bloco não pode ser exibido: seria impossível saber se o zero
 * significa "não aconteceu" ou "ainda não foi publicado".
 */
export interface Completude {
  /** Início e fim do recorte considerado. */
  janelaInicio: IsoDate;
  janelaFim: IsoDate;
  /** Data do último registro conhecido na área. */
  ultimoRegistroEm: IsoDate | null;
  /**
   * Exclusões estruturais que afetam o número, como votação secreta.
   * A regra 6 obriga a expor isto junto de qualquer índice que as sofra.
   */
  exclusoesEstruturais?: string[];
}

/** Estágio de execução de valor orçamentário. */
export type EstagioOrcamentario =
  | 'empenhado'
  | 'liquidado'
  | 'pago'
  | 'restos_a_pagar';

/**
 * Valor monetário com estágio declarado.
 *
 * A regra 5 do contrato: "declarar o estágio de todo valor orçamentário".
 * Somar estágios incompatíveis é um dos doze modos de falha catalogados —
 * produz "valor sem estágio declarado", que é número errado com aparência de
 * número certo.
 */
export interface ValorOrcamentario {
  /** Em centavos, para preservar precisão decimal. */
  centavos: number;
  estagio: EstagioOrcamentario;
}
