import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { AdmThemeProvider } from '../lib/theme';
import { AuthProvider } from '../lib/auth';
import { Gate } from '../components/Gate';

const inter = Inter({ subsets: ['latin'], weight: ['400', '500', '600', '700', '800'], variable: '--font-inter' });
const mono = JetBrains_Mono({ subsets: ['latin'], weight: ['400', '500', '600'], variable: '--font-mono' });

export const metadata: Metadata = {
  title: 'Aquarius · Admin',
  description: 'Console operacional da rede social cívica Aquarius',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${inter.variable} ${mono.variable}`}>
      <body>
        <AdmThemeProvider>
          <AuthProvider>
            <Gate>{children}</Gate>
          </AuthProvider>
        </AdmThemeProvider>
      </body>
    </html>
  );
}
