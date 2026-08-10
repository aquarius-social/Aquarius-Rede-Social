'use client';
import { useState } from 'react';
import { useAdmTheme } from '../lib/theme';
import { useAuth } from '../lib/auth';
import { Shell } from './Shell';
import { Icon } from './Icon';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function Gate({ children }: { children: React.ReactNode }) {
  const { theme } = useAdmTheme();
  const { session, carregando, isAdmin } = useAuth();

  // Bypass de desenvolvimento: pula o gate quando NEXT_PUBLIC_ADMIN_DEV_BYPASS=1
  // (definido só no .env.local local; ausente em produção = gate ativo). Permite
  // desenvolver/ver o console sem montar auth. NUNCA ligar em produção.
  if (process.env.NEXT_PUBLIC_ADMIN_DEV_BYPASS === '1') return <Shell>{children}</Shell>;

  if (carregando) {
    return (
      <div style={{ minHeight: '100vh', background: theme.bg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: theme.fgMuted, fontSize: 13 }}>
          <Icon name="sync" size={18} color={theme.fgMuted} /> Verificando acesso…
        </div>
      </div>
    );
  }

  if (!session) return <Login />;
  if (!isAdmin) return <SemAcesso />;
  return <Shell>{children}</Shell>;
}

function Mark() {
  return (
    <svg width={40} height={40} viewBox="0 0 32 32" fill="none">
      <rect width="32" height="32" rx="9" fill="url(#gm)" />
      <path d="M6 20 Q11 15 16 20 T26 20" stroke="#fff" strokeWidth="2" fill="none" strokeLinecap="round" />
      <path d="M6 15 Q11 10 16 15 T26 15" stroke="#5FA0E0" strokeWidth="2" fill="none" strokeLinecap="round" opacity="0.9" />
      <defs><linearGradient id="gm" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#0D2B5E" /><stop offset="1" stopColor="#2E7DD1" /></linearGradient></defs>
    </svg>
  );
}

function Casca({ children }: { children: React.ReactNode }) {
  const { theme } = useAdmTheme();
  return (
    <div style={{ minHeight: '100vh', background: theme.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <div style={{ width: '100%', maxWidth: 380, background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: 16, padding: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
          <Mark />
          <div>
            <div style={{ fontWeight: 800, fontSize: 18, color: theme.fg, letterSpacing: '0.02em' }}>AQUARIUS</div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: theme.fgSubtle }}>Admin</div>
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}

function Login() {
  const { theme } = useAdmTheme();
  const { enviarLink } = useAuth();
  const [email, setEmail] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [enviado, setEnviado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const ok = EMAIL_RE.test(email.trim());

  const enviar = async () => {
    if (!ok || enviando) return;
    setErro(null); setEnviando(true);
    try { await enviarLink(email); setEnviado(true); }
    catch { setErro('Não deu para enviar agora. Tente novamente.'); }
    finally { setEnviando(false); }
  };

  return (
    <Casca>
      {enviado ? (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <Icon name="check" size={18} color={theme.pos} />
            <span style={{ fontSize: 15, fontWeight: 700, color: theme.fg }}>Link enviado</span>
          </div>
          <p style={{ margin: 0, fontSize: 13, color: theme.fgMuted, lineHeight: 1.5 }}>
            Enviamos um link de acesso para <b style={{ color: theme.fg }}>{email}</b>. Abra o e-mail e clique para entrar no console.
          </p>
        </div>
      ) : (
        <div>
          <h1 style={{ margin: '0 0 6px', fontSize: 18, fontWeight: 800, color: theme.fg }}>Entrar no console</h1>
          <p style={{ margin: '0 0 16px', fontSize: 12.5, color: theme.fgMuted, lineHeight: 1.5 }}>Acesso restrito à equipe. Enviamos um link mágico para o seu e-mail.</p>
          <label style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: theme.fgMuted }}>E-mail</label>
          <input value={email} onChange={(e) => { setEmail(e.target.value); setErro(null); }} onKeyDown={(e) => e.key === 'Enter' && enviar()}
            placeholder="voce@base.aq" autoFocus
            style={{ width: '100%', marginTop: 6, padding: '11px 12px', borderRadius: 9, border: `1.5px solid ${theme.border}`, background: theme.bg, color: theme.fg, fontSize: 14, outline: 'none' }} />
          {erro ? <div style={{ marginTop: 8, fontSize: 12.5, color: theme.neg }}>{erro}</div> : null}
          <button onClick={enviar} disabled={!ok || enviando}
            style={{ width: '100%', marginTop: 14, padding: '12px', borderRadius: 9, border: 'none', cursor: ok ? 'pointer' : 'default', background: theme.sky, color: '#fff', fontSize: 14, fontWeight: 700, opacity: !ok || enviando ? 0.5 : 1 }}>
            {enviando ? 'Enviando…' : 'Enviar link de acesso'}
          </button>
        </div>
      )}
    </Casca>
  );
}

function SemAcesso() {
  const { theme } = useAdmTheme();
  const { session, sair } = useAuth();
  return (
    <Casca>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <Icon name="lock" size={18} color={theme.warn} />
        <span style={{ fontSize: 15, fontWeight: 700, color: theme.fg }}>Sem acesso ao console</span>
      </div>
      <p style={{ margin: '0 0 16px', fontSize: 13, color: theme.fgMuted, lineHeight: 1.5 }}>
        Você entrou como <b style={{ color: theme.fg }}>{session?.user?.email}</b>, mas essa conta não está na equipe do admin
        (<code>admin_roles</code>). Peça a um superadmin para incluir seu acesso.
      </p>
      <button onClick={sair} style={{ padding: '10px 14px', borderRadius: 9, border: `1px solid ${theme.borderStrong}`, background: 'transparent', color: theme.fg, cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>Sair</button>
    </Casca>
  );
}
