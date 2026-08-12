# Estado atual do Aquarius

Documento vivo, **enxuto de propósito** — é o 2º arquivo a ler (depois do `CLAUDE.md`).
Para a fotografia completa, leia `RELATORIO_DESENVOLVIMENTO.md`; para o backlog granular,
`MELHORIAS.md`; para os marcos detalhados (números de ingestão, achados), `HISTORICO.md`.

Atualização: 2026-08-12.

## Onde estamos (resumo)

- **App (Expo) — camada de leitura pronta.** 15 telas navegáveis, dado real onde existe:
  Perfil parlamentar, Partido, Comissão, Frente, Explorar + Listagem, Feed v1 (dinheiro
  real), Calendário, Interesses, Prometeus (lista+chat, placeholder honesto), Configurações,
  Editar perfil, Login (OTP e-mail + gate), Onboarding. **Modo escuro ✅ · Header custom
  (AqHeader) ✅ · Sistema de "seguir" ✅** (núcleo + Feed "Seguindo").
- **Dados & ingestão.** Fundação de identidade + pipeline 3 camadas de pé; 8/9 áreas com
  coletor; **servidas no banco:** despesas (Câmara+Senado), emendas, eventos. Proposições/
  votações/tramitações/discursos: coletor pronto, **truncados por espaço**. Presença: sem
  coletor. Banco no **teto do Free (~476/500 MB)**.
- **Admin (Next.js).** 14 telas fiéis ao protótipo (via adaptador de dados) + **RBAC**
  (`admin_roles` + RLS + gate de login). **Deploy na Vercel ✅** (produção) + `localhost:3001`.
- **Login & deploys (11/08).** App web e Admin **no ar na Vercel**. Login por **OTP de 6
  dígitos** funcionando (Supabase + **Resend como SMTP custom**); o "colar o código inteiro"
  foi corrigido. Ressalva de produção: com `onboarding@resend.dev` o código só chega no
  **e-mail da própria conta Resend** — liberar para qualquer usuário depende de **domínio
  verificado** (ver pendências).
- **Agente Prometeus (IA) — Onda 2 em construção.** Plano fechado em sub-etapas 2.0→2.5
  (ver `PLANO.md`): ReAct + servidor MCP + Sonnet 5 (fall-back nativo Claude→Claude), no GCP.
  **Etapa 2.1 pronta:** serviço `codigo/services/prometeus/` — servidor MCP com **7 consultas
  seguras** à camada ouro (despesas, emendas, eventos, identidade), cada uma com proveniência
  e honrando o contrato de resposta da Metodologia §20; **14 testes sem rede, verdes**. Falta
  plugar a IA (Etapa 2.2). As telas do app seguem com placeholder honesto.

## ⚠️ Ações pendentes do usuário (fora do código)

1. **Rotacionar a service/secret key do Supabase** — ela circulou no chat durante os
   testes de ingestão. Supabase → Settings → API Keys → revoke + gerar nova. (Não quebra o
   app, que usa a `anon`.) **Prioridade: segurança.**
2. **Rodar a migration `0018_follows`** no SQL editor do Supabase — sem ela, o "seguir"
   não persiste.
3. **E-mail de produção — comprar domínio + verificar no Resend.** *(Parqueado até adquirir
   o domínio.)* O SMTP do Resend já está configurado no Supabase e o template já envia o
   `{{ .Token }}` (código de 6 dígitos). Mas `onboarding@resend.dev` só entrega para o e-mail
   da própria conta Resend — sem um **domínio verificado**, Bruno e demais usuários **não
   recebem o código**. Fluxo: Resend → Domains → registros DNS no provedor → trocar o Sender
   no Supabase para `login@seudominio`.
4. **Secrets do repo** (`SUPABASE_URL`/`SUPABASE_SERVICE_KEY`) — para o agendador
   `ingestao.yml` rodar sozinho 2×/dia.
5. **Supabase Free → Pro** — quando for ligar as áreas pesadas (legislativo, bronze,
   convênios, pré-2018). Bloqueio de várias frentes.
6. **WhatsApp Business** — iniciar a habilitação Meta em paralelo (dependência externa
   mais longa; ver `PLANO.md`).

## Próximo passo

- **App:** testar o "seguir" ponta a ponta (após a migration); depois **Notificações
  (tela)** e a **tela de Proposição** — ou já o **agente Prometeus** (a peça mais delicada).
- **Admin:** ligar as telas ao real conforme as tabelas nascem; a **Revisão editorial** é o
  freio de segurança, pré-requisito para ligar a IA.
- **Dados:** subir para o Pro e **reingerir** as áreas truncadas (destrava Proposição + abas
  legislativas). Depois: convênios/transferências (o "objeto" das emendas).

Backlog completo por área (A–I) em `MELHORIAS.md`. Roadmap em ondas em `PLANO.md`.

## Notas de ambiente

- O interpretador Python aqui é **`py`**, não `python` (alias fantasma da Microsoft Store).
- Testes de ingestão: **~302 passando** sem rede — `cd codigo/services/ingestao && py -m
  unittest discover -s . -t .`. Devem sair com `OK`.
- **Máquina com RAM limitada:** Metro (Expo web) e `tsc` estouram memória com app + admin +
  preview juntos. Parar o preview antes do `tsc`; `metro.config.js` já limita `maxWorkers`.
  Ver a memória do projeto `ambiente-ram-limitada`.

## O que NÃO fazer (resumo — detalhe no `CLAUDE.md`)

- Não editar migration antiga (correção vem em migration nova).
- Não copiar código de `basedosdados/pipelines` (sem licença) nem `parlametria/leggo-backend`
  (AGPL). OK ler como referência de campo/modelagem.
- Não pular a resolução de identidade ("resolver depois"). Dado errado é pior que ausente.
- Não criar arquivos fora da pasta do projeto.
