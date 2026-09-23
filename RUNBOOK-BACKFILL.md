# RUNBOOK — Backfill "fatia de valor" (identidade + dinheiro, 2018–2022)

**Para quem:** o dev que vai rodar a ingestão (mesma máquina/momento do deploy do Prometeus).
**Escopo desta rodada:** estender **identidade** e **dinheiro** (despesa de cota + emendas) de
**2018 a 2022**. NÃO inclui os domínios de atividade (proposição/votação/discurso) — isso fica
para uma 2ª rodada. Motivo: despesa e emenda são o que o Prometeus **lê hoje**, então isso
aprofunda o agente imediatamente, com o menor custo/risco.

**Por que 2018–2022 e não antes:** o mapeador `legislatura_do_ano` (`run_backfill.py:43-50`) só
distingue as legislaturas 55/56/57. Dentro de **2015–2026** a extensão é só config. **Ir antes
de 2015 exige mudar código** — não faça nesta rodada.

---

## ⚠️ A ordem é inegociável: identidade ANTES dos fatos

A Metodologia (§4, modo de falha nº 6) exige **identidade resolvida na data do fato**. Se
ingerirmos uma despesa de 2019 **sem** o vínculo de partido/UF de 2019 já carregado, ela é
carimbada com o **partido de hoje** — o erro que a metodologia inteira existe para impedir.

Por isso rodamos em **3 passadas**, nesta ordem: **(A) identidade → (B) cota → (C) emendas.**

---

## 0. Antes de começar (pré-requisitos)

1. **Máquina robusta, isolada.** Feche Metro (Expo) e qualquer `tsc`/preview — eles competem por
   RAM. O backfill em si é leve de memória, mas é **longo** (single-thread; a passada A é rápida,
   B e C levam horas). Deixe rodando.
2. **Terminal na pasta do serviço:**
   ```powershell
   cd "codigo\services\ingestao"
   py -m pip install supabase
   ```
3. **Segredos — no arquivo `.env`** (padrão fixo, lido automaticamente). Edite
   `codigo\services\ingestao\.env`:
   ```
   SUPABASE_URL=https://nqebfmyzchpkufsytvyf.supabase.co
   SUPABASE_SERVICE_KEY=<a service_role key — Supabase > Settings > API>
   ```
   O `py run_backfill.py` lê esse `.env` sozinho (`env_local.carregar_env`) — **nunca** cole a
   chave direto no terminal nem no chat. Uma variável já definida no ambiente (ex.: no CI) tem
   prioridade e não é sobrescrita.
   > 🔒 A `service_role` key está na lista de **rotacionar** (circulou no chat antes). Idealmente
   > rotacione-a antes e use a nova aqui.
4. **Chave da Transparência** (só para a passada C — emendas). É gratuita; cadastre um e-mail em
   `portaldatransparencia.gov.br/api-de-dados/cadastrar-email` e guarde a chave. Se o projeto já
   tinha uma (as emendas de 2023–2026 já existem), reuse a mesma.

**Regras que valem para as 3 passadas:**
- **Idempotente:** tudo é `upsert`. Pode rerodar à vontade — acumula/deduplica, nunca soma.
- **Retomável por ANO:** `Ctrl+C` pausa; rerodar continua do ano seguinte. (Não há checkpoint
  no meio de um ano — interromper no meio re-puxa aquele ano inteiro, o que é seguro, só não é
  barato.)
- **Sempre meça 1 ano primeiro** (o próprio código manda). Só depois solte o intervalo.

---

## Passada A — Identidade + vínculos (2018–2022)

Carrega deputados/senadores + **histórico de mandatos → `vinculo_temporal`** das legislaturas
55/56. É o alicerce que resolve o partido/UF na data do fato. **Rápida.**

**Fatos DESLIGADOS; identidade LIGADA:**
```powershell
# --- Passada A: identidade only ---
$env:AQUARIUS_HISTORICO   = "1"   # histórico de mandatos (Câmara) -> vínculos
$env:AQUARIUS_ENRIQUECER  = "1"   # pessoa natural (necessário p/ junção bicameral)
$env:AQUARIUS_SENADO      = "1"   # senadores + mandatos (identidade do Senado)
$env:AQUARIUS_DESPESAS    = "0"
$env:AQUARIUS_CEAPS       = "0"
$env:AQUARIUS_PROPOSICOES = "0"
$env:AQUARIUS_VOTACOES    = "0"
$env:AQUARIUS_DISCURSOS   = "0"
$env:AQUARIUS_EVENTOS     = "0"
$env:AQUARIUS_BRONZE      = "0"   # app lê a camada ouro, não o bronze — poupa espaço/tempo
Remove-Item Env:\AQUARIUS_TRANSPARENCIA_KEY -ErrorAction SilentlyContinue  # emendas off aqui

# mede 1 ano:
$env:AQUARIUS_BACKFILL_INICIO = "2018"; $env:AQUARIUS_BACKFILL_FIM = "2018"
py run_backfill.py
# se o output imprimir perfis=<não-zero>, solte o intervalo:
$env:AQUARIUS_BACKFILL_INICIO = "2018"; $env:AQUARIUS_BACKFILL_FIM = "2022"
py run_backfill.py
```
Ao terminar, **me avise** — eu confirmo via Supabase MCP (leitura) que os vínculos 2018–2022
entraram certo antes de seguir. Essa é a checagem que garante que a passada B vai resolver o
partido histórico, não o de hoje.

---

## Passada B — Cota parlamentar / despesa (2018–2022)

Despesa CEAP (Câmara) + CEAPS (Senado). É o dado de maior valor imediato para o Prometeus.
**Horas** (uma chamada por parlamentar por ano). Sem chave de API.

```powershell
# --- Passada B: dinheiro (cota) ---
$env:AQUARIUS_DESPESAS    = "1"   # CEAP (Câmara)
$env:AQUARIUS_CEAPS       = "1"   # CEAPS (Senado)
$env:AQUARIUS_SENADO      = "1"
$env:AQUARIUS_HISTORICO   = "1"   # idempotente; garante vínculo presente
$env:AQUARIUS_ENRIQUECER  = "1"
$env:AQUARIUS_PROPOSICOES = "0"
$env:AQUARIUS_VOTACOES    = "0"
$env:AQUARIUS_DISCURSOS   = "0"
$env:AQUARIUS_EVENTOS     = "0"
$env:AQUARIUS_BRONZE      = "0"
Remove-Item Env:\AQUARIUS_TRANSPARENCIA_KEY -ErrorAction SilentlyContinue  # emendas ficam p/ C

# mede 1 ano, depois solte:
$env:AQUARIUS_BACKFILL_INICIO = "2022"; $env:AQUARIUS_BACKFILL_FIM = "2022"
py run_backfill.py
$env:AQUARIUS_BACKFILL_INICIO = "2018"; $env:AQUARIUS_BACKFILL_FIM = "2022"
py run_backfill.py
```

---

## Passada C — Emendas (2018–2022)

Fonte federal única (Portal da Transparência), cobre autores das duas casas. **Isolada** porque
essa API tem **rate-limit real e restritivo** — rodar sozinha evita estrangular as outras.

```powershell
# --- Passada C: emendas (precisa da chave) ---
$env:AQUARIUS_TRANSPARENCIA_KEY = "<sua chave da Transparência>"
$env:AQUARIUS_DESPESAS    = "0"
$env:AQUARIUS_CEAPS       = "0"
$env:AQUARIUS_SENADO      = "0"
$env:AQUARIUS_HISTORICO   = "0"
$env:AQUARIUS_ENRIQUECER  = "0"
$env:AQUARIUS_PROPOSICOES = "0"
$env:AQUARIUS_VOTACOES    = "0"
$env:AQUARIUS_DISCURSOS   = "0"
$env:AQUARIUS_EVENTOS     = "0"
$env:AQUARIUS_BRONZE      = "0"

$env:AQUARIUS_BACKFILL_INICIO = "2022"; $env:AQUARIUS_BACKFILL_FIM = "2022"
py run_backfill.py
$env:AQUARIUS_BACKFILL_INICIO = "2018"; $env:AQUARIUS_BACKFILL_FIM = "2022"
py run_backfill.py
```
Se aparecer erro HTTP 429 no meio, é o rate-limit: o código já faz backoff e retenta; se
persistir, pause (`Ctrl+C`) e rode de novo mais tarde — é idempotente.

---

## Depois: verificação e ressalva de parcialidade

Ao final de B e C, dá pra conferir a cobertura pelas views ouro (rode no **SQL Editor** do
Supabase, ou me peça que eu rodo via MCP):
```sql
-- cota por casa e ano (esperado: 2018–2022 preenchidos nas duas fontes)
select source, ano, count(*) from despesa_publica
where ano between 2018 and 2022 group by 1,2 order by 2,1;

-- emendas por ano
select ano, count(*) from emenda_publica
where ano between 2018 and 2022 group by 1 order by 1;
```
**Ressalva honesta (Metodologia §2/§20):** enquanto a base não fechar, o Prometeus deve dizer
"cobertura parcial até <ano>" em vez de silenciar. Como o agente já carrega proveniência e
ressalvas, isso é automático — mas vale lembrar ao comunicar os números.

---

## O que NÃO fazer nesta rodada

- **Não ir antes de 2018** (quebra o `legislatura_do_ano`; precisa de código).
- **Não ligar** `AQUARIUS_PROPOSICOES/VOTACOES/DISCURSOS/EVENTOS/BRONZE` — é a 2ª rodada
  (atividade), mais pesada, e proposições ainda precisam rodar o **canário** (nunca validado ao
  vivo).
- **Não rodar junto com Metro/tsc.**
- **Não pular a Passada A.** Fato sem vínculo da época = partido errado.
