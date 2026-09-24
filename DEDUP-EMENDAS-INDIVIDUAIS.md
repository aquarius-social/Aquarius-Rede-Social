# Dedup — autores individuais de emenda sem perfil resolvido

**203 emendas · 10 autores** ainda sem `autor_profile_id`. O código de autor do
orçamento não bate com `id_externo` de nenhum perfil. Duas situações:

- **DUPLICADO (7 autores)** — a pessoa serviu em Câmara **e** Senado, então tem
  2 (ou 3) perfis. Você escolhe o canônico; eu ligo o código e re-rodo.
- **SEM PERFIL (3 autores)** — ninguém com esse nome foi ingerido. Precisa
  **criar** o perfil (ou descobrir por que a pessoa não entrou).

## Como escolher (regra da metodologia)

A fonte da emenda **NÃO carrega a casa** do autor — só `autor_nome`,
`autor_codigo` e `localidade_gasto` (onde o dinheiro foi gasto, ≠ estado do
autor). Então **não dá pra auto-resolver pela fonte**. Pela metodologia §4/§6
(*identidade resolvida na data do fato*), o perfil certo é o da casa que a
pessoa ocupava **no ano da emenda** — não o perfil "ativo" hoje.

Abaixo, minha leitura do mandato de cada um está marcada `[inferido]` (§3: sem
citar arquivo-fonte). Confirme antes de eu ligar. `sen-*` = perfil do Senado;
número puro = perfil da Câmara.

---

## DUPLICADOS

### JORGINHO MELLO — 28 emendas (2020–2022) · gasto: MÚLTIPLO
código orçamento `4185`
- `jorginho-mello-160509` (Câmara, ativo)
- `jorginho-mello-sen-5350` (Senado, inativo)
- `[inferido]` Senador SC 2019–2022 → nesses anos era **Senado** (`sen-5350`).

### AROLDE DE OLIVEIRA — 23 emendas (2020) · gasto: RJ
código orçamento `4090`
- `arolde-de-oliveira-74833` (Câmara, ativo)
- `arolde-de-oliveira-sen-751` (Senado, inativo)
- `[inferido]` Senador RJ 2019–2020 (faleceu out/2020) → **Senado** (`sen-751`).

### PEDRO CHAVES — 19 emendas (2018–2019) · gasto: SP
código orçamento `3843`
- `pedro-chaves-74812` (Câmara, ativo)
- `pedro-chaves-sen-453` (Senado, inativo)
- `pedro-chaves-sen-5116` (Senado, inativo)
- `[inferido]` Senador MS 2015–2019 → **Senado**. ⚠️ Há 2 perfis de Senado E
  um 2º código (`3672`, gasto GO) com o mesmo nome — confirmar se é a **mesma
  pessoa** ou dois "Pedro Chaves".

### PEDRO CHAVES — 17 emendas (2018–2019) · gasto: GO
código orçamento `3672`
- (mesmos 3 perfis de `3843` acima) — decidir junto com o `3843`.

### EUNICIO OLIVEIRA — 17 emendas (2018–2019) · gasto: CE
código orçamento `2894`
- `eunicio-oliveira-74454` (Câmara, ativo)
- `eunicio-oliveira-sen-612` (Senado, inativo)
- `[inferido]` Senador CE 2015–2023 (presidente do Senado 2017–19) → **Senado**
  (`sen-612`).

### LINDBERGH FARIAS — 14 emendas (2018–2019) · gasto: RJ
código orçamento `2881`
- `lindbergh-farias-74858` (Câmara, ativo)
- `lindbergh-farias-sen-3695` (Senado, inativo)
- `[inferido]` Senador RJ 2011–2019 (voltou à Câmara em 2023) → nesses anos era
  **Senado** (`sen-3695`).

### RENZO BRAZ — 7 emendas (2019) · gasto: MG
código orçamento `2765`
- `renzo-braz-160654` (Câmara, ativo)
- `renzo-braz-sen-5257` (Senado, inativo)
- `[inferido]` Deputado federal MG até jan/2019; suplente de senador → 2019 é
  **ambíguo** (fim do mandato de deputado vs. suplência no Senado). Confirmar.

---

## SEM PERFIL (criar / investigar)

### JEAN PAUL PRATES — 49 emendas (2020–2023) · gasto: RN
código orçamento `3886`
- Nenhum perfil com esse nome. `[inferido]` Senador RN 2019–2023 (depois
  presidente da Petrobras). **Deveria existir** — investigar por que não foi
  ingerido (não votou no recorte? nome normalizado diferente?) e **criar**.

### ROCHA — 21 emendas (2018–2019) · gasto: Rio Branco/AC
código orçamento `3780`
- Nenhum perfil "Rocha" puro. `[inferido]` nome parlamentar de deputado do
  **Acre** (gasto todo em Rio Branco). Precisa identificar o deputado e criar/ligar.

### PEDRO DALUA — 8 emendas (2022) · gasto: AP
código orçamento `4225`
- Nenhum perfil. `[inferido]` figura do **Amapá** — nome pouco usual, pode ser
  grafia da fonte. Investigar identidade real antes de criar.

---

## Depois que você decidir

Me diga, por autor, o `código orçamento` → o `slug` do perfil canônico (ou
"criar"). Eu:
1. gravo `id_externo = <código>` no perfil escolhido (migration nova, §5);
2. re-rodo o `rebackfill_autor_profile_id` só desses códigos;
3. confirmo no banco que as 203 emendas resolveram e que **nada** foi somado
   duas vezes (invariante anti-duplicidade).
