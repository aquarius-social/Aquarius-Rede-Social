// DADOS DE DEMONSTRAÇÃO (equipe) — TODO: trocar por query real quando a auth/role de admin existir.

export const PERMISSOES = [
  { l: 'Publicar posts no feed', s: false },
  { l: 'Editar texto gerado', s: false },
  { l: 'Corrigir / retratar publicado', s: true },
  { l: 'Remover / manter conteúdo', s: false },
  { l: 'Suspender / banir usuário', s: false },
  { l: 'Exportar dados DaaS', s: true },
  { l: 'Gerir contratos DaaS', s: true },
  { l: 'Alterar feature flags', s: false },
  { l: 'Gerir equipe e papéis', s: true },
];
export const PAPEIS = [
  { id: 'chefe', nome: 'Editor-chefe', membros: 2, perm: [0, 1, 2, 3, 4, 5, 6, 7, 8] },
  { id: 'editor', nome: 'Editor', membros: 6, perm: [0, 1, 2, 3] },
  { id: 'mod', nome: 'Moderador', membros: 5, perm: [3, 4] },
  { id: 'daas', nome: 'Analista DaaS', membros: 3, perm: [5] },
  { id: 'view', nome: 'Visualizador', membros: 4, perm: [] as number[] },
];
export const MEMBROS = [
  { av: 'BT', nome: 'Bruno Tavares', email: 'bruno@aquarius.gov.br', papel: 'Editor-chefe', tone: 'accent' as const, twofa: true, quando: 'agora', conv: false },
  { av: 'AR', nome: 'Ana Ribeiro', email: 'ana@aquarius.gov.br', papel: 'Editor', tone: 'accent' as const, twofa: true, quando: 'há 12 min', conv: false },
  { av: 'CS', nome: 'Carla Souza', email: 'carla@aquarius.gov.br', papel: 'Editor', tone: 'accent' as const, twofa: true, quando: 'há 1h', conv: false },
  { av: 'DL', nome: 'Diego Lima', email: 'diego@aquarius.gov.br', papel: 'Moderador', tone: 'muted' as const, twofa: false, quando: 'há 3h', conv: false },
  { av: 'PN', nome: 'Paula Nunes', email: 'paula@aquarius.gov.br', papel: 'Analista DaaS', tone: 'pos' as const, twofa: true, quando: 'ontem', conv: false },
  { av: 'RD', nome: 'Rafael Dias', email: 'rafael@parceiro.org', papel: 'Visualizador', tone: 'muted' as const, twofa: false, quando: 'há 2 dias', conv: true },
];
