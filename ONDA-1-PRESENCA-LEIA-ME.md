# Onda 1 · Área E — Presença (frequência no Plenário)

O que mudou e por quê. Área E era a **última área de atividade sem coletor**;
agora tem coletor, schema e camada ouro (Câmara). Senado fica para um 2º passe.

## O que é

Presença = comparecimento dos deputados às **sessões deliberativas do Plenário**.
Vira o stat "Presença %" no topo do perfil.

## Fonte (verificada ao vivo 2026-09-22)

- `/eventos?codTipoEvento=110&codTipoEvento=204` (tipos "Sessão Deliberativa"),
  filtrando `orgao='PLEN'` → a lista de sessões (~93/ano).
- `/eventos/{id}/deputados` → os **presentes** (varia 465..489 de 513 — presença
  real). **Ausente = fora da lista.** "Ausência justificada" NÃO vem desta fonte
  → `justificadas` fica `null` (dado ausente é melhor que inventado, §1).

## Camada de dados (migration `0019_presenca.sql`)

- `sessao` — sessões deliberativas do Plenário (bicameral por `casa`; Senado entra
  depois sem migration nova).
- `presenca` — uma linha por parlamentar **presente** numa sessão.
- `presenca_publica` (ouro) — agrega por parlamentar: **presenças / convocadas /
  percentual**. `convocadas` = sessões realizadas **dentro do mandato** do
  parlamentar (via `vinculo_temporal`, §4) — suplente que assumiu no meio não é
  penalizado. View de FATO (inclui ex-parlamentares, como `despesa_publica`).

## Código

- `camara/presenca.py` — coletor (bronze → prata → portão → contrato/canário):
  `rodada_sessoes`, `rodada_presencas`. Identidade resolvida na coleta por
  id_externo (a PESSOA, na data da sessão).
- `persistencia/repositorio.py` — `salvar_sessoes`, `salvar_presencas` (resolve o
  perfil por lookup; deputado não resolvido é pulado, sem perfil fantasma).
- `run_presenca.py` — backfill fatiável por ano (`AQUARIUS_PRESENCA_ANO`),
  resumível (pula sessão que já tem presença), isolado por sessão, idempotente.
- `.github/workflows/backfill-presenca.yml` — matriz por ano, max-parallel 3.
- `camara/tests/test_presenca.py` — 8 testes (aceita/recusa): só-PLEN, janela
  vazia, quarentena sem id, persistência idempotente + resolução/skip.

## Como rodar

1. **Aplicar a migration `0019_presenca.sql`** no Supabase (SQL Editor) — as
   tabelas não existem até isso; sem elas o backfill FALHA.
2. Disparar `backfill-presenca.yml` (Actions) — ou local: `py run_presenca.py`.
   Leve (~2 chamadas por sessão, ~93 sessões/ano). Idempotente/resumível.

## Pendente

- **Senado** (comparecimento no Plenário do Senado) — fonte a pesquisar (outro
  host); a tabela já é `casa`-agnóstica.
- **Justificadas** — de um recurso de justificativas de ausência (passe futuro).
