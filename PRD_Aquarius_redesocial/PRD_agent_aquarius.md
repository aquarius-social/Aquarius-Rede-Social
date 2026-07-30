Documentação de Requisitos do Produto (PRD) - Aquarius Agent (Prometeus)

1\. Visão Geral

O Aquarius Prometeus é a infraestrutura inteligente, assíncrona e "agent-centric" que sustenta o ecossistema Aquarius

. Ele isola o processamento massivo de dados do aplicativo mobile, sendo responsável por:

Ingestão e purificação de dados das APIs governamentais

.

Operação de múltiplos "tentáculos" de IA para geração de conteúdo (Stories, Resumos, Oráculo)

.

Novo: Geração de inteligência de dados (DaaS) e relatórios estratégicos para o setor público e privado

.

2\. A Ingestão Cívica (Shadow Caching Workflows)

Para garantir estabilidade frente à instabilidade das APIs governamentais (Swagger), o Prometeus opera via fluxos periódicos invisíveis

:

WebScrapers / SDK Base: Lógicas de Retry Exponencial e Delta Sync conectadas à Câmara e ao Senado

.

Deduplicação Inteligente: Uso de upsert on conflict em Python para manter a integridade da tabela de Posts

.

Modelagem Relacional (Schema Master): Conversão de entidades oficiais em objetos sociais "seguíveis" (Profiles e Posts)

.

3\. Os Tentáculos IA (Operação Prometeus)

3.1 Tentáculo A: Background Batcher (Stories \& Feed Engine)

Processamento em massa, realizado prioritariamente em horários de baixa carga

.

Stories Diários: Resume a movimentação dos perfis "top engajados" ou com métricas explosivas nas últimas 24h

.

Eficiência de Custo: Utiliza modelos de baixo custo (Gemini Flash, Claude Haiku) para sumarizações massivas, reservando modelos complexos para interações de alto valor

.

3.2 Tentáculo B: Oráculo MCP (Chatbot Conversacional)

Interface de chat separada para dúvidas analíticas profundas

.

Arquitetura MCP: O agente utiliza ferramentas internas (Planning → Reasoning → Response) com acesso direto e restrito ao banco Postgres via MCP (sem RAG), garantindo precisão documental

.

Rastreabilidade: Todas as perguntas são mantidas em histórico por Thread ID, gerando telemetria para análise de tendências no Admin

.

3.3 Tentáculo C: Resumos On-Demand (BFF Trigger)

Permite que o usuário solicite o resumo de um Projeto de Lei (PL) que ainda não foi processado pelo batch

.

Shared Cache: Uma vez gerado o resumo, ele é assentado no banco de dados e servido instantaneamente para qualquer outro usuário que acessar o mesmo PL

.

3.4 Tentáculo D: Oráculo Title Generator (Async Cron)

Monitora conversas novas e, após 10 minutos de inatividade, gera um título sintetizado para a sessão de chat

.

3.5 Tentáculo E: Analisador de Recortes Temáticos (Novo - B2B/G2B)

Este tentáculo atende às demandas configuradas no Aquarius Admin para clientes de consultoria e mídia

.

Pintura do Cenário Político: Diferente do Tentáculo C (que resume uma lei), este motor processa conjuntos de dados. Ex: "Relatório de impacto hídrico no NE baseado em todas as votações da semana"

.

Processamento de Telemetria (DaaS): Agrega dados do Onboarding Cognitivo (CEP, ideologia, interesses) com interações do feed (Likes/Dislikes) para gerar heatmaps de sentimento e tendências de opinião em tempo real

.

Saída Estruturada: Gera relatórios em formatos profissionais (PDF, JSON, CSV) prontos para exportação via Admin

.

4\. Arquitetura Técnica Sugerida

Core: Python 3.12+ (pipelines complexas de dados e ecossistema LLM)

.

API Mestre: FastAPI para performance assíncrona

.

Jobs Assíncronos: Event-Driven via Cloud Pub/Sub ou Redis/RQ

.

Segurança: Integração via RPC (Edge Functions) para comunicação blindada com o Admin



