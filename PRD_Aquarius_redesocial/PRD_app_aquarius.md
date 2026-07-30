# Documentação de Requisitos do Produto (PRD) - Aquarius App (Frontend)

## 1. Visão Geral
O **Aquarius App** é a interface primária do usuário (Mobile) da Rede Social Cívica. Ele tem a missão de engajar o cidadão entregando conteúdo político complexo de forma mastigada, social e dinâmica.

## 2. Público-Alvo (App)
*   **Cidadãos Comuns**: Usuários que desejam entender política como consomem notícias.
*   **Jornalistas/Acadêmicos**: Usuários que precisam favoritar e monitorar pautas ativamente.
*   **Poder Público (Perfis Legislativos)**: Parlamentares, Partidos e Comissões possuirão páginas de perfil polimórficas (conforme seção 4.B), mas **não** são elegíveis ao Selo Azul de usuários verificados.
*   **Perfis Verificados (Selo Azul)**: Exclusivo para Comunicadores, Analistas Políticos, Jornalistas e Acadêmicos. Requer aprovação via **KYC (Know Your Customer)** e pagamento de taxa recorrente de R$ 9,99/mês. Este selo confere destaque visual e prioridade em comentários.

## 3. Estrutura de Interface (Tabs e Navegação)

### 3.1. Autenticação e Onboarding Cognitivo
*   **Autenticação Mobile**: Login primário via Supabase Auth com WhatsApp (OTP sem senha numérica longa). O usuário recebe um código para entrar e a sessão permanece logada no dispositivo móvel.
*   **Engine de Cold-Start**: O usuário novo obrigatoriamente responde a um quiz visual:
    *   Temas de interesse (Ex: Educação, Segurança Pública, Economia).
    *   Região (CEP e autocomplete nas demais informações).
    *   Alinhamento (Partidos que gosta).
    *   Isso constrói as "Preferências Ativas", alimentando o motor de recomendação do Feed (que fará uso de uma Edge Function, não detalhada neste momento).

### 3.2. A Interface Principal (Toolbar e Topbar)
1. **Top Header**: Ancorado estaticamente na navegação do *Feed*. Ocupado pela Logo do Aquarius (Esquerda) e pela Miniatura de Foto do Usuário Logado (Direita). Ao clicar na foto, entra-se na tela de `Configurações da Conta/Onboarding`.
   - *Gerenciamento/LGPD*: Esta tela inclui, obrigatoriamente, as funções de "Deletar Conta", "Limpar Cache de Consultas Passadas" e "Exportar Dados".
2. **Toolbar Inferior (5 Abas Base)**:
   - **Feed (Home)**: Ágora principal.
   - **Explorar (Lupa)**: Buscador e painéis massivos.
   - **Prometeus (Chatbot)**: Aba 100% dedicada ao Oráculo de Inteligência Artificial.
   - **Interesses (Coração)**: Centro de atalhos e favoritos.
   - **Calendário**: Visão de data-driven.

### 3.3. Responsividade e Adaptabilidade (Mobile-First / Web)
O Aquarius é concebido como uma experiência **Mobile-First**, mas totalmente funcional em navegadores (Web).
- **Breakpoint de Transição**: Em telas largas (> 768px/1024px), a interface realiza um reflow estrutural.
- **Toolbar $\leftrightarrow$ Sidebar**: Os 5 itens da `Toolbar Inferior` do mobile deixam de existir no rodapé e são transpostos para uma **Sidebar Lateral Esquerda** fixa.
- **Top Header**: A miniatura de foto e logo podem se fundir ou se rearranjar na Sidebar ou em um Topbar estendido para melhor aproveitamento de tela horizontal.
- **Feed Centralizado**: O layout de cards de feed deve manter uma largura máxima (Max-Width) legível para evitar estiramento visual em monitores UltraWide.

---

## 4. Funcionalidades Core (Detalhes das Telas)

### A. O Feed (A "Ágora")
- **Layout de Abas**: Switchers superiores para trocar entre: `Para Você` (Algoritmo Complexo em Edge Function, calibrado no Admin), `Seguindo`, e abas `Customizadas` criadas pelo usuário.
- **Carrossel de Stories**: No topo absoluto do Feed. Mostra resumos diários (arquitetados em pílulas informais). Histórias duram 24h.
- **Scroll Infinito de Posts**: Feed misto, renderizando cards de diversos perfis. Emprega recursos Optimistic-UI para botões nativos (`Like`, `Dislike` e `Comentário`).
- **Feature Collab**: Posts exibem múltiplos autores (Ex: Deputado X, Presidente Y, Partido Z) lado a lado na assinatura do card.

### B. O Explorar e as Páginas de Perfil Expandidas
- **Índice Macro**: Listagem global separada por categorias de entidades (Parlamentares, Partidos, Órgãos, Proposições e Eventos).
- **Tela de Perfil Universal**: Todo clique numa entidade redireciona a uma "Visão de Perfil". *No futuro, a aba de perfil exibirá 1 botão para "Verificar Perfil", levando a um checkout pago (ax. R$ 9,99) para ganhar o Selo Azul e destaque em comentários*. A página de Perfil varia suas Tabs internas via Polimorfismo:
- **Pivô de Navegação por Perfil (Polimorfismo)**: Ao acessar uma entidade (Profile), a estrutura de abas se adapta:
  - *Parlamentares*: Feed Próprio (Posts vinculados), Proposições (Timeline e Autoria), Despesas (Gráficos/PieChart Nativo), Emendas Parlamentares, Discursos e Órgãos/Frentes que compõe.
  - *Partidos e Blocos*: Feed do Partido, Parlamentares (Membros filiados), Atuação/Lideranças e Emendas do Bloco.
  - *Órgãos e Comissões*: Feed da Comissão, Mesa Diretora/Membros, Eventos Futuros da Agenda, Votações Internas e Emendas Vinculadas.
  - *Frentes Parlamentares*: Feed Temático, Coordenação de Frente, Membros ativos e Emendas Relacionadas.
  - *Proposições/PLs (Tela de Detalhe)*: Resumo (Oficial ou IA), Autores (Header Collab), Tramitação (Timeline de fluxo legal) e Votações agregadas/indexadas.

### C. O Oráculo (Interface Chat Prometeus)
- Aba nativa mobile de chat: a interface do Oráculo deve seguir uma lógica de navegação familiar ao usuário de aplicativos de conversa, com organização simples, contínua e orientada por histórico.
- Header da funcionalidade: no topo da tela, o usuário visualiza o cabeçalho da área de chat com a logo do Prometeus à esquerda e um botão de destaque para Nova Conversa (+), que inicia imediatamente um novo tópico de interação com o Oráculo.
- Listagem de conversas na tela principal: abaixo do header, a interface exibe o histórico de conversas já realizadas pelo usuário, em uma estrutura inspirada na lógica da aba de mensagens do Instagram.
    - **Títulos Inteligentes**: Cada conversa deve ter um título sintetizado pelo Oráculo com base no contexto inicial. O título deve ser gerado/atualizado via **cron de sistema após 10 minutos de inatividade** em um novo tópico ou mudança drástica de assunto.
- Conversas contínuas por tema: cada conversa funciona como um tópico persistente, permitindo que o usuário volte posteriormente ao mesmo assunto para aprofundar o entendimento.
- Política de retenção do histórico: os históricos de conversa permanecem salvos por até 120 dias. Caso um tópico fique 120 dias sem qualquer interação, ele deverá ser apagado automaticamente da conta do usuário.
- Experiência de resposta: ao entrar em uma conversa, o usuário acessa uma janela de chat com respostas em streaming token-a-token, reforçando a percepção de interação em tempo real.
- Resumo sob demanda no Feed: quando o usuário clicar em uma PL extensa no Feed e ela ainda não possuir resumo disponível, poderá acionar um botão de IA para solicitar a geração do resumo naquele momento.

### D. Interesses e Calendário
- **Interesses Dinâmicos (Favoritos)**: Lista rápida segmentada verticalmente (`Seus Deputados`, `Seus Temas`, `Suas Pautas`), fornecendo contagem de itens não lidos (unseen notifications).
- **Calendário Visual**: Renderização estilo Agenda mesclando reuniões de comissões favoridatas e eventos públicos.

---

## 5. Arquitetura Técnica FrontEnd
- **Framework**: Expo / React Native UI (Versão 54+).
- **Estilização**: Tailwind CSS embutido via NativeWind v4 (permitindo Design System CSS variables dinâmico para modos claro/escuro fluidos e unificação visual com Admin).
- **Otimização**: Componentes de lista substituídos nativamente por renderização de alta-performance (ex: `@shopify/flash-list`) para tolerar Feeds gigantes.
- **State Manager / BFF**: Tratamento via Tanstack Query (React Query) integrado ao pacote `supabase-js`, rodando com **abundância de cache no device** para evitar onerosos recast/polling constantes via background na tela do feed.
