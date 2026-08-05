/** Formatação de dinheiro e datas em pt-BR. */

/** Reais a partir de um valor numérico (a fonte já vem em reais, não centavos). */
export function reais(valor: number | null | undefined): string {
  if (valor === null || valor === undefined) return '—';
  return valor.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 2,
  });
}

/** Reais compactos para KPIs grandes: R$ 1,2 mi / R$ 340 mil. */
export function reaisCompacto(valor: number | null | undefined): string {
  if (valor === null || valor === undefined) return '—';
  const abs = Math.abs(valor);
  if (abs >= 1_000_000) return `R$ ${(valor / 1_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mi`;
  if (abs >= 1_000) return `R$ ${(valor / 1_000).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} mil`;
  return reais(valor);
}

/** Formato K/M idêntico ao design: R$ 341,2K · R$ 5,1M. */
export function kbr(valor: number | null | undefined): string {
  if (!valor) return 'R$ 0';
  if (Math.abs(valor) >= 1e6) return `R$ ${(valor / 1e6).toFixed(1).replace('.', ',')}M`;
  return `R$ ${(valor / 1e3).toFixed(1).replace('.', ',')}K`;
}

/** "sincronizado em 04/08/2026" — o frescor da fonte (§3.1). */
export function frescor(syncedAt: string | null | undefined): string {
  if (!syncedAt) return 'frescor não informado';
  const d = new Date(syncedAt);
  if (isNaN(d.getTime())) return 'frescor não informado';
  return `sincronizado em ${d.toLocaleDateString('pt-BR')}`;
}
