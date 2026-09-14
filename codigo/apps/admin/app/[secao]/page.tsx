'use client';
import { useAdmTheme } from '../../lib/theme';
import { PageHeader, Card } from '../../components/ui';
import { Icon } from '../../components/Icon';

const TITULOS: Record<string, string> = {
  pipelines: 'Pipelines', feed: 'Feed & Posts', stories: 'Stories da IA', revisao: 'Revisão editorial',
  moderacao: 'Moderação', prometeus: 'Prometeus IA', usuarios: 'Usuários', engajamento: 'Engajamento',
  audiencias: 'Audiências (DaaS)', flags: 'Feature flags', auditoria: 'Auditoria LGPD',
  equipe: 'Equipe & Permissões', settings: 'Configurações',
};

export default function Secao({ params }: { params: { secao: string } }) {
  const { theme } = useAdmTheme();
  const titulo = TITULOS[params.secao] ?? params.secao;
  return (
    <>
      <PageHeader title={titulo} subtitle="Tela do admin — em construção" />
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '18px 4px' }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: theme.accentSoft, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Icon name="grid" size={20} color={theme.accent} />
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: theme.fg }}>“{titulo}” ainda não foi construída</div>
            <div style={{ marginTop: 3, fontSize: 12.5, color: theme.fgMuted, lineHeight: 1.5 }}>
              A fundação do admin (shell, tema claro/escuro, Visão geral) está pronta. As telas entram
              uma a uma, fiéis ao protótipo. A ordem está no board do Snaps.
            </div>
          </div>
        </div>
      </Card>
    </>
  );
}
