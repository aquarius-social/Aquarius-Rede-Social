/**
 * Perfis — a tabela mãe.
 *
 * A Concepção do Produto, seção 4.4: "Toda entidade do Congresso é um perfil
 * que se pode seguir. [...] Partidos, comissões e frentes são o mesmo objeto,
 * com o conjunto de abas próprio de cada um, o que dá ao usuário uma única
 * forma de navegar toda a instituição."
 *
 * A Metodologia de Dados, seção 4: "profiles é o identificador próprio do
 * Aquarius para cada pessoa; identificador externo nunca serve de chave
 * primária."
 *
 * Por que isto importa na prática: no protótipo, cada tipo de entidade tem seu
 * próprio espaço de identificadores, e o identificador 'p1' designa ao mesmo
 * tempo a Comissão de Educação e uma deputada. Com espaços separados, nenhuma
 * chave estrangeira polimórfica (seguir, notificar, vincular post a perfil)
 * pode ser real — vira texto livre. Uma chave global resolve a classe inteira.
 */

import type {
  BaseAtribuicao,
  IsoDate,
  Proveniencia,
} from './proveniencia';

export type PerfilTipo =
  | 'parlamentar'
  | 'partido'
  | 'bloco'
  | 'comissao'
  | 'frente'
  | 'orgao';

export type Casa = 'camara' | 'senado' | 'congresso';

/** Campos comuns a toda entidade seguível. */
export interface PerfilBase extends Proveniencia {
  id: string;
  tipo: PerfilTipo;
  nome: string;
  sigla: string | null;
  slug: string;
  fotoUrl: string | null;
  ativo: boolean;
  seguidores: number;
}

/**
 * Ocupação de cadeira numa janela de tempo.
 *
 * Metodologia, seção 4: "versiona partido, unidade federativa e ocupação da
 * cadeira por período: um voto de 2021 resolve o partido de 2021, não o atual.
 * A ocupação registra também o suplente em exercício, porque voto, despesa e
 * discurso de uma janela pertencem a quem ocupava o assento."
 *
 * Resolver atributo no presente em vez da data do fato é um dos doze modos de
 * falha catalogados.
 */
export interface VinculoTemporal {
  casa: Casa;
  legislatura: number | null;
  uf: string;
  partidoId: string | null;
  /** Sigla como a fonte publicou no momento do fato. */
  partidoSiglaFonte: string | null;
  ocupacao: 'titular' | 'suplente_em_exercicio' | 'licenciado';
  /** Quando suplente em exercício: de quem é a cadeira. */
  titularPerfilId: string | null;
  inicio: IsoDate;
  /** Nulo significa em exercício. */
  fim: IsoDate | null;
}

/**
 * Perfil de pessoa natural com mandato.
 *
 * Os atributos de identidade (nome civil, data de nascimento, naturalidade)
 * NÃO aparecem aqui: a seção 3.5 determina que permanecem restritos à camada
 * interna de resolução, sem integrar respostas. Este tipo é o que a API serve.
 */
export interface PerfilParlamentar extends PerfilBase {
  tipo: 'parlamentar';
  /** Vínculos ordenados do mais recente para o mais antigo. */
  vinculos: VinculoTemporal[];
  /** Vínculo vigente hoje, se houver. Conveniência derivada. */
  vinculoAtual: VinculoTemporal | null;
}

export interface PerfilPartido extends PerfilBase {
  tipo: 'partido' | 'bloco';
  numeroUrna: number | null;
  fundacao: IsoDate | null;
  extincao: IsoDate | null;
  /** Siglas anteriores, com vigência. Renome preserva a identidade. */
  siglasAnteriores: { sigla: string; nome: string; ate: IsoDate }[];
  /**
   * Fusões e incorporações. A fonte "apaga as origens nas fusões, e a
   * linhagem é reconstruída por curadoria" (Metodologia, seção 4) — por isso
   * cada elo carrega a base da atribuição.
   */
  linhagem: {
    antecessorId: string;
    tipoEvento: 'fusao' | 'incorporacao' | 'renome' | 'cisao';
    dataEvento: IsoDate;
    base: BaseAtribuicao;
  }[];
}

export interface PerfilColegiado extends PerfilBase {
  tipo: 'comissao' | 'frente' | 'orgao';
  casa: Casa;
  /**
   * A Metodologia, seção 6.4, alerta: colegiados mistos do Congresso aparecem
   * no serviço de uma casa mesmo quando exercidos durante mandato na outra.
   * Toda participação é resolvida contra a linha do tempo de ocupação da
   * cadeira antes de ser atribuída a um mandato.
   */
  membros: MembroColegiado[];
}

export interface MembroColegiado {
  perfilId: string;
  cargo: string;
  inicio: IsoDate;
  fim: IsoDate | null;
  /** Contra qual mandato esta participação foi resolvida. */
  vinculoCasa: Casa;
}

export type Perfil = PerfilParlamentar | PerfilPartido | PerfilColegiado;

/** Referência leve a um perfil, para uso em cards e listas. */
export interface PerfilRef {
  id: string;
  tipo: PerfilTipo;
  nome: string;
  sigla: string | null;
  uf: string | null;
  fotoUrl: string | null;
}

/**
 * Verificação por identidade real (selo azul).
 *
 * Concepção do Produto, seção 4.8: reservada a comunicadores, analistas,
 * jornalistas e acadêmicos, e "vedada a parlamentares e partidos, uma decisão
 * que preserva a neutralidade da plataforma".
 *
 * Note que isto NÃO é atributo de `Perfil`: perfis do Congresso não são
 * verificáveis por definição. Verificação pertence ao usuário da rede social.
 * O protótipo hoje tem um campo `verificado` na entidade parlamentar, que é
 * justamente a entidade que a regra proíbe de verificar.
 */
export type CategoriaVerificacao =
  | 'jornalista'
  | 'analista'
  | 'academico'
  | 'comunicador';
