// DADOS DE DEMONSTRAÇÃO (revisao) — TODO: trocar por query real quando o agente Prometeus existir.
export const FILA = [
  {
    id: 'v1', tipo: 'Votação', conf: 74, baixa: false,
    headline: 'A Câmara aprovou em 1º turno a PEC 78/2024, que torna o FUNDEB permanente.',
    ia: 'A Câmara dos Deputados aprovou em primeiro turno a PEC 78/2024, que torna o FUNDEB permanente na Constituição. Foram 412 votos a favor, 38 contra e 7 abstenções.',
    fonte: 'Proposição PEC 78/2024 — Votação em 1º turno.\nSIM: 412 · NÃO: 38 · ABSTENÇÃO: 7 · Resultado: APROVADA.',
    fonteRef: 'Câmara · votações nominais', geradoHa: '6min',
  },
  {
    id: 'd1', tipo: 'Discurso', conf: 58, baixa: true,
    headline: 'Em plenário, Erika Hilton defendeu a regulamentação do Pé-de-Meia.',
    ia: 'Em pronunciamento no plenário, a parlamentar defendeu a regulamentação do programa Pé-de-Meia, citando atrasos no repasse.',
    fonte: 'Discurso · Grande Expediente. Trecho sujeito a conferência nas notas taquigráficas (atribuição a confirmar).',
    fonteRef: 'Câmara · notas taquigráficas', geradoHa: '12min',
  },
  {
    id: 'e1', tipo: 'Despesa', conf: 63, baixa: true,
    headline: 'A bancada do PSB registrou R$ 41M em novas emendas, com foco no Nordeste.',
    ia: 'A bancada do PSB registrou cerca de R$ 41 milhões em novas emendas empenhadas, com concentração em municípios do Nordeste.',
    fonte: 'Emendas · Portal da Transparência. Somatório por partido a validar (estágio empenhado ≠ pago).',
    fonteRef: 'Portal da Transparência', geradoHa: '20min',
  },
];

export const CORRECOES = [
  { icon: 'check' as const, tone: 'pos' as const, titulo: 'PL 2159/2021 · licenciamento ambiental', tipo: 'Votação', status: 'Corrigido', statusTone: 'pos' as const, origem: 'Número de votos divergente da fonte oficial após atualização da Câmara.', acao: '"aprovado por 274 votos" → "aprovado por 277 votos". Nota de correção anexada ao post.', autor: 'Ana · Editora', quando: 'há 2h' },
  { icon: 'trash' as const, tone: 'neg' as const, titulo: 'Discurso atribuído incorretamente', tipo: 'Discurso', status: 'Retratado', statusTone: 'neg' as const, origem: 'Atribuição trocada entre dois parlamentares na geração automática.', acao: 'Post removido do feed e substituído por nota de retratação. Usuários que interagiram foram notificados.', autor: 'Bruno · Editor-chefe', quando: 'ontem' },
];
