/**
 * Núcleo cívico — as áreas de dado da Parte II da Metodologia.
 *
 * Todas as entidades aqui vêm de ingestão e carregam proveniência. Nenhuma é
 * escrita pelo usuário.
 *
 * Inclui quatro entidades que os mocks do protótipo consomem mas que o
 * DATA-MODEL.md do handoff não modela: discurso, evento, presença e o vínculo
 * nominal de voto.
 */

import type {
  Completude,
  IsoDate,
  IsoDateTime,
  Proveniencia,
  ValorOrcamentario,
} from './proveniencia';
import type { Casa } from './perfil';

// -----------------------------------------------------------------------------
// Área B — Proposições
// -----------------------------------------------------------------------------

export type ProposicaoTipo = 'PL' | 'PEC' | 'MP' | 'PLP' | 'PDL' | 'REQ' | 'INC';

export interface Proposicao extends Proveniencia {
  id: string;
  tipo: ProposicaoTipo;
  numero: number;
  ano: number;
  /** Rótulo de exibição, ex.: "PL 1234/2025". Derivado, nunca chave. */
  identificador: string;
  ementa: string;
  tema: string | null;
  situacao: string;
  orgaoPerfilId: string | null;
  casaOrigem: Casa;
  dataApresentacao: IsoDate;
  /**
   * Inteiro teor. A Metodologia, seção 9, mediu: documentos recentes retornam
   * PDF com texto extraível; documentos de 1995 não retornam PDF. A ausência é
   * um fato sobre a fonte, não sobre a matéria.
   */
  inteiroTeorUrl: string | null;
  inteiroTeorTemTexto: boolean;
  /** Já existe resumo do Prometeus. */
  temResumoIa: boolean;
}

// -----------------------------------------------------------------------------
// Área C — Votações
// -----------------------------------------------------------------------------

export type Voto = 'sim' | 'nao' | 'abstencao' | 'obstrucao' | 'ausente';

/**
 * Voto nominal de um parlamentar numa votação.
 *
 * O DATA-MODEL.md prevê `voto_por_parlamentar[]` mas nenhum mock o traz, e o
 * próprio protótipo registra a falta: há um comentário de usuário no feed
 * pedindo "entender melhor por que 38 votaram contra. O app podia mostrar
 * quem." É a entidade que responde a essa pergunta.
 */
export interface VotoNominal {
  votacaoId: string;
  perfilId: string;
  voto: Voto;
  /** Partido no momento do voto, não o atual. */
  partidoSiglaNaEpoca: string | null;
}

export interface Votacao extends Proveniencia {
  id: string;
  proposicaoId: string | null;
  titulo: string;
  data: IsoDateTime;
  casa: Casa;
  resultado: string;
  sim: number;
  nao: number;
  abstencao: number;
  /**
   * Votação secreta não tem nominal. A regra 6 do contrato de resposta obriga
   * a expor exclusões estruturais junto de qualquer índice que as sofra — um
   * ranking de fidelidade partidária que ignore votações secretas está errado
   * e precisa dizer isso.
   */
  secreta: boolean;
  nominais: VotoNominal[];
}

// -----------------------------------------------------------------------------
// Área D — Tramitações
// -----------------------------------------------------------------------------

export interface Tramitacao extends Proveniencia {
  id: string;
  proposicaoId: string;
  sequencia: number;
  data: IsoDateTime;
  orgaoSigla: string | null;
  descricao: string;
  despacho: string | null;
}

// -----------------------------------------------------------------------------
// Área A — Despesas (cota parlamentar / CEAP)
// -----------------------------------------------------------------------------

/**
 * Lançamento individual de despesa.
 *
 * Granularidade de transação, não de agregado. O mock do protótipo traz o dado
 * já somado por categoria, o que serve para desenhar o gráfico mas não permite
 * verificar integridade: a Metodologia detectou edição retroativa de despesa
 * justamente por resumo criptográfico por lançamento, invisível na contagem.
 */
export interface Despesa extends Proveniencia {
  id: string;
  perfilId: string;
  categoria: string;
  /** Competência (mês de referência), AAAA-MM. */
  competencia: string;
  dataDocumento: IsoDate;
  fornecedorNome: string;
  fornecedorDocumento: string | null;
  valorDocumentoCentavos: number;
  valorGlosaCentavos: number;
  /** Identidade aritmética: líquido = documento − glosa (seção 5.2). */
  valorLiquidoCentavos: number;
  /** Resumo do lançamento, para detectar edição feita no lugar. */
  hashLancamento: string;
}

/** Verifica a identidade aritmética de um lançamento (Nível 1, seção 5.2). */
export function despesaConsistente(d: Despesa): boolean {
  return (
    d.valorLiquidoCentavos === d.valorDocumentoCentavos - d.valorGlosaCentavos
  );
}

// -----------------------------------------------------------------------------
// Área F — Emendas parlamentares
// -----------------------------------------------------------------------------

export interface Emenda extends Proveniencia {
  id: string;
  /** Código oficial da emenda. Embute o identificador de autor (seção 6.3). */
  codigo: string;
  exercicio: number;
  /**
   * Autor individual. Nulo quando o autor é ente coletivo — bancada ou
   * comissão. Atribuir ente coletivo a uma pessoa é erro de categoria, e a
   * Metodologia mede 3,8% dos registros nessa condição.
   */
  autorPerfilId: string | null;
  autorColetivoNome: string | null;
  /** Quando a autoria foi transferida por sucessão, quem executa. */
  executorPerfilId: string | null;
  uf: string;
  municipio: string | null;
  finalidade: string;
  /**
   * Valores por estágio. A cadeia começa no empenho — a Metodologia registra
   * que 67% do empenhado foi pago no conjunto examinado. Somar estágios
   * incompatíveis é modo de falha catalogado.
   */
  valores: ValorOrcamentario[];
}

/**
 * Identidade de ordem: empenhado ≥ liquidado ≥ pago (Nível 1, seção 5.2).
 *
 * Verificada sobre 13.300 registros de dois exercícios completos, sem
 * violação. A leitura correta desse resultado, segundo a própria Metodologia:
 * esta dimensão está limpa e o detector opera; sobre as demais nada afirma.
 */
export function ordemOrcamentariaValida(valores: ValorOrcamentario[]): boolean {
  const v = (e: string) =>
    valores.find((x) => x.estagio === e)?.centavos ?? null;
  const emp = v('empenhado');
  const liq = v('liquidado');
  const pago = v('pago');
  if (emp !== null && liq !== null && liq > emp) return false;
  if (liq !== null && pago !== null && pago > liq) return false;
  if (emp !== null && pago !== null && liq === null && pago > emp) return false;
  return true;
}

// -----------------------------------------------------------------------------
// Área G — Discursos
// -----------------------------------------------------------------------------

export interface Discurso extends Proveniencia {
  id: string;
  perfilId: string;
  data: IsoDateTime;
  /** Modalidade da manifestação. A regra 5 do contrato obriga a declará-la. */
  modalidade: string;
  tema: string | null;
  duracaoSegundos: number | null;
  /**
   * Resumo oficial da casa.
   *
   * A Metodologia, seção 14, mediu: "fiel e insuficiente: compressão de 2:1 a
   * 40:1; descreve o ato, não o argumento". A regra 4 do contrato obriga a
   * rotular resumo oficial como tal — conteúdo, números e tom vêm do texto
   * integral.
   */
  resumoOficial: string | null;
  transcricaoUrl: string | null;
}

// -----------------------------------------------------------------------------
// Área E — Presença
// -----------------------------------------------------------------------------

export interface Presenca extends Proveniencia {
  perfilId: string;
  legislatura: number;
  sessoesConvocadas: number;
  sessoesPresentes: number;
  justificadas: number;
  completude: Completude;
}

// -----------------------------------------------------------------------------
// Área H — Eventos institucionais
// -----------------------------------------------------------------------------

/**
 * Evento da agenda institucional.
 *
 * A Metodologia é explícita na seção 24: "A agenda pessoal do parlamentar não
 * é dado aberto, e a cobertura de eventos limita-se ao calendário
 * institucional." A tela de Calendário do app precisa respeitar esse limite.
 */
export interface Evento extends Proveniencia {
  id: string;
  titulo: string;
  inicio: IsoDateTime;
  fim: IsoDateTime | null;
  local: string | null;
  orgaoPerfilId: string | null;
  tipoEvento: string;
  situacao: string;
  participantesPerfilIds: string[];
  pauta: string | null;
}
