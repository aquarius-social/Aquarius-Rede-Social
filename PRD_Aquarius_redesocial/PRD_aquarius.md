# Documentação de Requisitos do Produto (PRD) - Aquarius V1

## 1. Visão Geral (Pivô Estratégico)
O **Aquarius V1** evolui de um passivo "Portal de Monitoramento" para uma **Rede Social Cívica de Política e Gestão Pública**. 

Em vez de exigir que o usuário tenha um interesse proativo e busque dados no formato clássico de "dashboard/busca", a aplicação passa a processar, mastigar e instigar o consumo de dados governamentais através da linguagem universal de **Feeds e Stories**. 

A plataforma consolida e humaniza Atividades, Votações, Leis e Gestão em um ambiente social nativo onde os "Perfis" são provedores de conteúdo integrados e a IA (via ecossistema Prometeus) atua não apenas como sumarizador de background, mas como interface direta da informação e "usuário validador".

## 2. Público-Alvo e Business Model

*   **B2C Sustentável**: Cidadãos e Estudantes formam a base orgânica. Jornalistas e ONGs de monitoramento civil.
*   **B2B Upsell & Poder Público**: Ferramentas direcionadas para mandatos parlamentares e segundo setor, oferecendo recortes temáticos refinados pelas IAs analisadoras de dados legislativos.

## 3. Conceitos Centrais e Arquitetura de Domínio

### 3.1 Perfis (O Objeto Cidadão)
O objeto primário do app foi universalizado. Em vez do conceito engessado de "Deputado/Senador", operamos através de **Profiles**. Tudo que for entidade mapeada vira um "Profile", passível de ser seguido.
Tipos Suportados de Profiles: Parlamentares (Câmara, Senado - MVP), Partidos, Blocos Partidários, Frentes, Comissões, Órgãos.
*Roadmap*: Perfis de "Analistas IA" que produzem análises próprias (tendências) que o usuário poderá seguir como personas interativas.

### 3.2 Posts (O Feed e os Collabs)
Projetos de Lei, Tramitações, Votações, Emendas Parlamentares e Eventos na agenda se tornam e são modelados arquiteturalmente como `Posts`. 

**Recurso Collab (Vínculos Array)**:
Todo Post suporta o vínculo com múltiplos Profiles. Quando um PL é lançado, o card do Post listará o Partido, o Órgão e o Autor associados lado a lado, assemelhando-se às "Collabs" do Instagram. Permite transição direta até a origem e o respectivo perfil.

**Interação Social**:
Todos os cards no feed abrem gatilho de interação, compondo ranking logarítmico na rede com botões em interface unificada: Like, Dislike e Comentários do Cidadão.

### 3.3 Prometeus (A Orquestração IA)
O núcleo cerebral inteligente baseado em Microsserviços Python/GCP e Node. Possui 3 tentáculos cruciais:
*   **Background (O Cron Worker Preditivo)**: Em horários fixos e de forma autônoma, os workers conectam-se às APIs Swagger públicas, digerem todo o fluxo relacional do dia em nosso Backend estruturado num PG SQL unificado e evocam requests "Batching" baseados em LLM. O processo assenta tudo isso formatado como "Novidades do Feed" e "Stories", blindando a estabilidade da UI/App (evitando requisições live).
*   **Orquestrador Frontend (O Chatbot Oráculo MCP)**: Oráculo *Plan $\rightarrow$ Reasoning $\rightarrow$ Response* suportando tool-usings da própria aplicação Aquarius para sanar dúvidas analíticas longas enviadas pelo usuário (Ex: "Deputado X tem perfil fiscalista?").
*   **Resumos Inteligentes Sob Demanda (User-Triggered)**: Funcionalidades onde o próprio usuário pode solicitar à IA um resumo customizado na hora (ex: Um PL gigante que caiu na timeline e ainda não foi mastigado). Tais resumos gerados dinamicamente são registrados no banco de dados e entram como dados consultivos base do PRD (Shared Cache), de forma que se um segundo usuário abrir o mesmo PL, o resumo será servido instantaneamente.

---

## 4. Funcionalidades de Interface (UI/UX Roadmap)

### 4.1. Onboarding Cognitivo Guiado
Para driblar o engajamento pífio (Cold Start), o novo Login incorpora perguntas de sondagem profundas para calibração inicial do algoritmo de recomendação: Pautas Favoritas, Ideologia/Partidos, Regiões de Interesse, Background de Domínio.

### 4.2. Header e Toolbar Inferior (5 Abas Base)
*   **Header Main - apenas na tela Feed**: Fica ancorado no Topo e abrigará o Logo do app + a foto arredondada contendo atalho para a seção do **Perfil do Usuário Logado** (onde se gerencia Onboarding/Setup).

**A Toolbar Horizontal Inferior:**
1.  **Feed (Home)** 
2.  **Explorar (Lupa)** 
3.  **Prometeus (Chatbot Oráculo)** 
4.  **Interesses / Favoritos (Coração)** 
5.  **Calendário**

### 4.3. Telas Core 

#### **A. Tela 1: O Feed (Home)**
*   **Layout Abas do Feed**: Combinação de feeds em `Para Você / Últimas`, `Seguindo`, e feeds fixáveis ativados no botão `+` (O usuário pinna atalhos para os "Posts do PT" ou "Posts da Comissão da Fazenda").
*   **A "Trilha" de Stories**: Área primária superior arredondada baseada nos favoritos - resumos em linguagem informal compactando o histórico do dia daquele político ou pauta em cards temporários diários de IA.
*   **Rolagem Timeline Infinita**: Apresentação visual da tabela de posts com botões *Like*, *Dislike*, *Comentários* (modal). 

#### **B. Tela 2: Explorar (A Wiki Social)**
*   Pivota por: `Partidos e Blocos` / `Parlamentares e Frentes` / `Órgãos e Comissões` / `Proposições e Votações` / `Agenda e Eventos`.
*   A Tela principal dessa estrutura consome a listagem massiva (via paginação ao nosso backend).

**Estrutura Dinâmica da Página "Detalhes"**
Ao acessar um perfil, exibimos a Página "Detalhes", composta de um Header de Conta, Biografia, Botão "Seguir" e uma estrutura de Abas parametrizada pelo tipo de Perfil:
- **Parlamentares**: *Feed próprio, Proposições, Despesas (Gráficos), Emendas Parlamentares, Discursos, Eventos da Agenda e Órgãos/Frentes ativas*.
- **Partidos e Blocos**: *Feed do Partido, Parlamentares (Membros filiados), Atuação/Lideranças, Emendas Parlamentares do Bloco.*
- **Órgãos e Comissões**: *Feed da Comissão, Mesa Diretora/Membros, Eventos Futuros, Votações Internas realizadas e Emendas Vinculadas*.
- **Frentes Parlamentares**: *Feed Temático, Coordenação, Membros da Frente e Emendas Relacionadas*.
- **Proposições/PLs**: *Resumo Oficial (ou IA Sob-Demanda), Autores (Collab Header), Tramitação (Timeline de fluxo legal) e Votações agregadas e indexadas*.

#### **C. Tela 3: Oráculo Prometeus (Aba Própria)**
*   A interface do chatbot é separada, comportando uma Sidebar local/Lista de navegação por "Sessões Prévias de Chat" (histórico mantido em BD por Thread ID), dando reusabilidade a pesquisas complexas anteriores e botão de *New Chat*.

#### **D. Tela 4: Interesses (Quick Access)**
*   Lista vertical dos favoritos que geram notificação proativa (Sino Ativado). O "Short-cut" de perfis.
*   **Organização Dinâmica**: Os interesses e "following lists" serão organizados categoricamente de forma visual. (ex: Aba/Section para "Seus Políticos", "Seus Partidos", "Seus Temas e Órgãos").

#### **E. Tela 5: Calendário**
*   Dashboard visual onde o usuário visualiza eventos na agenda dos preferidos, eventos em tramitação, cruza pautas macro das casas legislativas, filtrável de forma interativa.

---

## 5. Arquitetura Técnica Recomendada

### Frontend Mobile
- **Core**: React Native SDK 54 / Expo.
- **UI Toolkit**: TailwindCSS via NativeWind 4 / Otimizações agressivas de componentes (ex: FlashList) para suportar renderização passiva de Feeds pesados sem perder o delta FPS na scroll.

### Backend Integrador (FastAPI API -> Supabase DB)
- **Framework O-Auth**: Rotais de autenticação delegados integralmente via pacote Supabase Auth e RLS restritos.
- **Motor Banco**: PostgreSQL Supabase: A Modelagem foi polida para focar as APIs consumidas da câmara numa consolidação Shadow Server. Nada passa live (com exceção exploratória) pro frontend. Tabela mãe: *`profiles` e `posts`*.

---

## 6. Evolução Macro - Fases de Integração
- **Fase 1 (MVP)**: Câmara dos Deputados e Senado Federal, Modelagem de dados baseada nas APIs Dados Abertos e Legis Senado.
- **Fase 2**: Acoplagem Prometeus Bot ativo, sistema "Verificado" e gatilhos de resumos dinâmicos em Timeline.
- **Roadmap Futuro**: Incorporação e monitoramento Cívico de Tribunais, Judiciário local, Tratores Executivos de Orçamento (Estados/Câmaras Municipais).
