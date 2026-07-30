# Documentação de Requisitos do Produto (PRD) - Aquarius Admin (Backoffice)

# 1\. Visão Geral

# O Aquarius Admin é a "Torre de Controle" da Rede Social Cívica

# . Ele evolui de uma ferramenta puramente operacional para um motor de inteligência de negócios, permitindo a governança de dados, auditoria de processos de IA (Prometeus), aprovação de perfis verificados e, crucialmente, a geração de relatórios estratégicos e análise de tendências políticas para parceiros B2B e governamentais

# .

# 2\. Público-Alvo (Dashboard)

# Time Base Aquarius (Operação e Estratégia).

# Curadores e Moderadores Nubo.

# Analistas de Dados e Consultores Legislativos.

# 3\. Funcionalidades Core

# 3.0 Autenticação e Segurança

# Acesso Restrito: Login via e-mail e senha padrão para administradores, operando em rede blindada

# .

# Rotas Transacionais RPC: Mapeamento de comunicações (Start, Force, Stop) via Edge Functions para o motor isolado do Agent Prometeus em Python

# .

# 3.1 Painel de Saúde de Dados (Data Ingestion Health)

# Dashboard de Crons: Status visual dos scripts de background do Prometeus que consomem APIs da Câmara e Senado

# .

# Controle de Algoritmo: Ajuste de parâmetros e pesos de prioridade para o feed "Para Você" do Mobile

# .

# Sync Manual: Comandos para forçar sincronização imediata com APIs governamentais ou pular lotes (Skip Batch)

# .

# 3.2 Moderação e Auditoria de IA (Human-in-the-Loop)

# Fila de Stories: Interface para auditar e validar os resumos diários publicados pelo gerador automático

# .

# Logs de Sumarização: Capacidade de revisar e excluir (Tombstone) resumos de leis problemáticos, solicitando novo processamento ao agente

# .

# Telemetria do Oráculo: Rastreabilidade anônima do consumo de tokens para prevenção de SPAM e monitoramento de custos

# .

# 3.3 CRM e Gestão de Perfis

# Central de Verificados (Selo Azul): Gestão do fluxo de KYC (Know Your Customer) para jornalistas, analistas e acadêmicos

# .

# Auditoria de Elegibilidade: Bloqueio de selos pagos para parlamentares e órgãos públicos para garantir a neutralidade

# .

# 3.4 Módulo de Inteligência de Dados e Relatórios B2B/G2B (Novo)

# Este módulo operacionaliza a monetização via consultoria e serviços de dados (Data-as-a-Service)

# .

# 3.4.1 Configurador de Recortes Temáticos Refinados

# Gestão de Clientes: Interface para cadastrar entidades (Frentes Parlamentares, ONGs, Redações de Mídia)

# .

# Definição de Parâmetros: Filtros avançados para a IA processar relatórios:

# Geográfico: Recortes por CEP/Região baseados na telemetria de usuários

# .

# Temático: Agrupamento de PLs e votações por tags (ex: "Agronegócio", "Educação").

# Temporal: Agendamento de relatórios diários, semanais ou mensais.

# Disparo de Relatórios: Gatilho para o Prometeus gerar sínteses estratégicas sobre o impacto de pautas específicas

# .

# 3.4.2 Painel de Telemetria de Opinião (DaaS)

# Heatmap de Sentimento: Visualização de tendências de aprovação/rejeição (Likes/Dislikes) por tema e região

# .

# Análise de Dúvidas: Agregação anônima dos tópicos mais perguntados ao Oráculo para identificar demandas informacionais da população

# .

# Exportação de Insights: Geração automática de infográficos e gráficos de tendência para uso em mídia e assessorias

# .

# 3.4.3 Gestão de Entregáveis

# Subscription Portal: Controle de níveis de acesso para parceiros corporativos.

# Log de Auditoria B2B: Registro histórico de todos os relatórios gerados e entregues para fins de faturamento e conformidade.

# 4\. Arquitetura Técnica Sugerida

# Frontend: Vite/React 18 + SPA Web utilizando Shadcn/ui para UI Kits rápidos

# .

# Visualização de Dados: Integração com bibliotecas como Recharts ou Nivo para exibição de dashboards de opinião e telemetria.

# Estado e Dados: Tanstack React Query para conexão com BFF FastAPI/Supabase

# .

# Exportação: Microsserviços para geração de PDFs e relatórios estruturados em JSON/CSV.

