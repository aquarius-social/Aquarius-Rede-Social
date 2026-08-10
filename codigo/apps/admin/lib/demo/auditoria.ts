// DADOS DE DEMONSTRAÇÃO (auditoria) — TODO: trocar por query real quando a tabela audit_log + auth de admin existir.

export type Cat = 'seguranca' | 'dados' | 'sistema';
export const EVENTOS: { quando: string; ator: string; av: string; sistema?: boolean; acao: string; alvo: string; ip: string; cat: Cat }[] = [
  { quando: 'há 3 min', ator: 'mariana@base.aq', av: 'M', acao: 'user.impersonate', alvo: 'Lucas Oliveira', ip: '200.171.45.12', cat: 'seguranca' },
  { quando: 'há 11 min', ator: 'system', av: '', sistema: true, acao: 'pipeline.sync', alvo: 'Frentes Parlam.', ip: '—', cat: 'sistema' },
  { quando: 'há 24 min', ator: 'pedro@base.aq', av: 'P', acao: 'report.export', alvo: 'CNI · panorama', ip: '201.34.12.88', cat: 'dados' },
  { quando: 'há 1h', ator: 'mariana@base.aq', av: 'M', acao: 'tombstone.apply', alvo: 'Resumo PL 3287', ip: '200.171.45.12', cat: 'dados' },
  { quando: 'há 2h', ator: 'rodrigo@base.aq', av: 'R', acao: 'user.refund', alvo: '+55 11 9 8765…', ip: '179.18.4.27', cat: 'seguranca' },
  { quando: 'há 4h', ator: 'system', av: '', sistema: true, acao: 'pipeline.fail', alvo: 'Frentes Parlam.', ip: '—', cat: 'sistema' },
];
