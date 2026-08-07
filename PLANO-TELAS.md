# PLANO-TELAS.md — telas do app (Expo) a partir do protótipo

Mapa das telas do Claude Design: o que já foi feito, o que falta, e a ordem
proposta. Prontidão de dado: 🟢 real agora · 🟡 parcial (perfil existe, dados
finos não ingeridos) · 🔴 precisa ingestão pesada (⛔Pro) ou IA · 🔵 casca/conta
(não depende de dado cívico).

Fonte dos designs: `uploads/Aquarius Rede Social/prototype/*.jsx` (via MCP do
Design). Já portados: `aq-foundation`, `aq-screens-2` (perfil), `aq-screens-4`
(partido).

---

## Já feitas ✅

- **11 · Perfil parlamentar** — dinheiro real (despesas do mandato + emendas com
  drill-down + fonte), 9 abas, situação (licenciado/suplente), card de transição.
- **13 · Partido** — bancada real (membros, Câmara/Senado, filtro UF) + emendas
  agregadas por função. Placeholder rotulado em Lideranças/Proposições.
- **05/16 · Explorar (hub) + Listagem** — hub de entidades com contagem real
  (Parlamentares, Partidos, Comissões, Frentes) + Listagem filtrável reutilizável.
- **14 · Comissão** — perfil **enxuto**: identidade real (nome/sigla/fonte/frescor)
  + seções pendentes rotuladas (composição/mesa/agenda/votações "em breve", pois
  dependem de reingestão ⛔Pro/⛔fonte). Listagem real das 89 comissões.
- **15 · Frente** — perfil enxuto igual: identidade real + composição/atividade
  rotuladas "em breve". Listagem real das 1443 frentes.
- **01 · Splash** — navy + logo branca animada; mostrado durante a carga.
- **02 · Login (OTP e-mail)** — visual do protótipo; login real por e-mail via
  Supabase Auth (SMS/WhatsApp "em breve"). Gate de rota por sessão + onboarding.
- **03 · Onboarding** — intro → temas → partidos → sobre (opt-in, LGPD) → montando;
  prefs salvas no perfil (user_metadata). Gate por estado (link mágico ou código).
- **18 · Configurações** — conta, Plano Free, "Complete seu perfil" (anel %), feed
  (temas/partidos), grupos LGPD/App, **Sair**. Ações não-essenciais: "em breve".
- **19 · Editar perfil** — completude + Nome/CEP/idade/gênero + dados opt-in
  (escolaridade/renda/ocupação), salvos no perfil.
- **08 · Interesses** — gerencia temas/partidos (add/remove, persistido no perfil);
  parlamentares/proposições com estado honesto (follow chega com o Feed).
- **06/07 · Prometeus (telas)** — lista (sugestões + histórico vazio) + chat
  (bolhas, digitando, input, chips). Resposta é PLACEHOLDER honesto: **o agente
  (IA) ainda não está ligado** — é o próximo passo.

## Inventário do que falta

| # | Tela | Prontidão | Nota |
|---|------|-----------|------|
| 05/16 | **Explorar / Busca** | 🟢 | Refinar a lista: filtros (UF, partido, casa, situação) + ordenação; abas para partidos/comissões/frentes. |
| 17 | **Listagem** | 🟢 | Lista genérica reutilizável (parlamentares/partidos/…). Base para Explorar. |
| 14 | **Comissão** | 🟡 | Perfil existe (`tipo=comissao`), mas membros/pauta/votações **não ingeridos** → maioria placeholder. |
| 15 | **Frente** | 🟡 | Idem comissão (perfil existe; composição/proposições não ingeridas). |
| 04 | **Feed cívico** | 🟠 | v1 possível com **destaques de dinheiro reais** (maiores despesas/emendas); feed completo precisa **Prometeus (IA)**. |
| 12 | **Proposição** | 🔴 | Precisa a área legislativa (proposições/tramitações/votações) reingerida — ⛔Pro. |
| 06/07 | **Prometeus** (lista + chat) | 🔴 | Precisa o agente de IA. |
| 01 | **Splash** | 🔵 | Abertura. Sem dado. |
| 02 | **Login (OTP)** | 🔵 | OTP por SMS/e-mail (decisão travada); WhatsApp em paralelo. |
| 03 | **Onboarding** | 🔵 | Seleção de interesses/temas. |
| 08 | **Interesses** | 🔵 | Preferências do usuário (pós-login). |
| 09 | **Calendário** | 🟡 | Agenda institucional — eventos ingeridos existem (área nova), mas truncados; parcial. |
| 10 | **Notificações** | 🔵 | Lista de notificações (depende de eventos/seguir). |
| 18 | **Configurações** | 🔵 | Conta, privacidade, LGPD. |
| 19 | **Editar perfil** | 🔵 | Perfil opt-in (renda/escolaridade = nudge, nunca obrigatório). |

## Ordem proposta (fases)

**Fase 1 — fechar o circuito de dados (real, é nosso diferencial)**
1. **Explorar/Busca refinada** (05/16) — a porta de entrada: filtros + ordenação +
   navegar entre parlamentares/partidos. Reaproveita a Listagem (17).
2. **Comissão + Frente** (14/15) — perfis, com o que temos (placeholder rotulado no
   resto), fechando os tipos de perfil polimórfico.

**Fase 2 — casca de app (vira "app de verdade")**
3. **Splash + Login (OTP) + Onboarding** (01/02/03).
4. **Configurações + Editar perfil** (18/19).

**Fase 3 — Feed & IA (o coração editorial)**
5. **Feed v1** (04) — destaques de dinheiro reais (sem IA).
6. **Prometeus** (06/07) — o agente (chat + resumos com fonte).

**Fase 4 — legislativo (depende do Pro)**
7. **Proposição** (12) + ligar as abas legislativas dos perfis (proposições,
   votações, presença, discursos) quando reingerirmos essas áreas.

**Transversais (quando fizer sentido):** Calendário (09), Notificações (10),
Interesses (08).

## Recomendação

Começar pela **Fase 1** — Explorar/Busca refinada primeiro (é o que o usuário vê
antes de tudo e hoje está cru), depois Comissão/Frente. Mantém o app 100% com dado
real e navegável ponta a ponta antes de partir para casca/IA/legislativo.
