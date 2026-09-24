# Dedup dos autores individuais de emenda — RESOLVIDO (2026-09-24)

Os **203 individuais** que faltavam foram todos resolvidos e vinculados. Migration
`0026_dedup_individuais_autores.sql`. Autoria individual de emenda: **0 sem perfil**.
Cobertura total de emenda: **99,45% → 99,87%** (sobram só coletivos: comissão/relator).

## Como foi resolvido (§4/§6 — casa na DATA DO FATO, fonte oficial)

A fonte da emenda **não carrega a casa** do autor. Cada vínculo foi ancorado no
**mandato oficial** (API Câmara `/deputados/{id}` + Senado `/senador/{cod}/mandatos`
e `/senador/lista/legislatura/{leg}`) e **verificado adversarialmente** por 10
agentes independentes (8/8 duplicados "concorda / confiança alta", 0 divergências;
2 "sem perfil" identificados como perfis **já existentes** — nenhum criado).

| Código | Nome na fonte | → Perfil | Casa (data do fato) | Emendas | Base oficial |
|---|---|---|---|---|---|
| 4185 | JORGINHO MELLO | `jorginho-mello-sen-5350` | Senado | 28 | senador SC leg56; Câmara = deputado até jan/2019 |
| 4090 | AROLDE DE OLIVEIRA | `arolde-de-oliveira-sen-751` | Senado | 23 | senador RJ leg56 (†out/2020); nascimento idêntico confirma |
| 2894 | EUNICIO OLIVEIRA | `eunicio-oliveira-sen-612` | Senado | 17 | senador CE leg55; Câmara é mandato 2023+ |
| 2881 | LINDBERGH FARIAS | `lindbergh-farias-sen-3695` | Senado | 14 | senador RJ leg55; Câmara é mandato 2023+ |
| 3886 | JEAN PAUL PRATES | `jean-paul-prates-sen-5627` | Senado | 49 | senador RN leg56; grafia "Jean-Paul" (hífen) escondia |
| 3843 | PEDRO CHAVES | `pedro-chaves-sen-5116` | Senado | 19 | senador **MS** leg55 (Pedro Chaves dos Santos Filho); gasto MS |
| 3672 | PEDRO CHAVES | `pedro-chaves-74812` | Câmara | 17 | deputado **GO** leg55 (Pedro Pinheiro Chaves — **outra pessoa**); gasto GO |
| 2765 | RENZO BRAZ | `renzo-braz-160654` | Câmara | 7 | deputado MG leg55; LOA2019 redigida em 2018; gasto MG |
| 3780 | ROCHA | `wherles-rocha-178840` | Câmara | 21 | = Wherles F. da Rocha, deputado AC leg55; gasto AC |
| 4225 | PEDRO DALUA | `dalua-do-rota-217330` | Câmara | 8 | = DaLua do Rota (mesma pessoa), deputado AP leg56; gasto AP |

**Homônimo Pedro Chaves:** eram **duas pessoas** — o senador de MS (5116) e o
deputado de GO (74812). Códigos de orçamento distintos, desambiguados por UF do
gasto e nome civil. Cada um foi para um perfil **diferente** → sem soma dupla.

**Sinais (§5.3):** `metodo='convergencia'`, `grau='direto'`, ≥2 sinais
(`nome_parlamentar` + `mandato_oficial_data_do_fato`; +`uf_do_gasto` nos homônimos).
`versao_regra='dedup_individuais.v1'`, `pendente_conferencia=false` (a fonte
oficial de mandato é o 2º sinal, não um palpite).

## O que sobra (coletivo, honesto)

66 emendas ainda sem autor **pessoal** — todas COLETIVAS: 65 Emenda de Comissão
(as siglas truncadas/ambíguas que ficaram fora do 0025) + 1 Emenda de Relator.
Pertencem a perfil coletivo, nunca somadas a um parlamentar (invariante
anti-duplicidade). Curadoria à parte, não furo de dado.
