# Onda 0 — Fundação

Primeira entrega de código do Aquarius. Cobre a Onda 0 da Metodologia de Dados
(seção 18): resolução de identidade, mais os pacotes compartilhados de tipos e
tokens.

```
supabase/migrations/0001_identidade.sql     schema de identidade
services/ingestao/resolucao/                resolvedor + normalização + 21 testes
packages/types/                             tipos TS compartilhados
packages/ui/                                tokens de design + preset Tailwind
```

Verificar tudo:

```
cd services/ingestao && python -m unittest discover -s resolucao/tests -t .
cd packages/types && npx tsc --noEmit
cd packages/ui    && npx tsc --noEmit
```

Os testes Python não têm dependência externa. Rodam sob `unittest` e sob
`pytest`.

---

## Por que a identidade vem antes de tudo

A Metodologia é direta na seção 6: se a identidade não estiver resolvida, o
cruzamento atribui o dado ao parlamentar errado, e a qualidade das demais
camadas deixa de importar.

O protótipo já mostra o sintoma, sem que o problema fosse nomeado: no mock do
feed, o identificador `p1` designa ao mesmo tempo a Comissão de Educação e uma
deputada, porque cada tipo de entidade tem seu próprio espaço de
identificadores. Como consequência, clicar numa comissão dentro de um post abre
o perfil de uma parlamentar. Uma chave global elimina a classe inteira desse
defeito, e é o que torna reais as chaves estrangeiras polimórficas de seguir,
notificar e vincular post a perfil.

---

## O schema

`profiles` é a tabela mãe de toda entidade seguível. `id_externo` mapeia cada
perfil para os identificadores da Câmara, do Senado e do código de autor
orçamentário, guardando método e grau de confiança por ligação — é o que
permite ao contrato de resposta declarar a base da atribuição quando o vínculo
não for direto. `vinculo_temporal` versiona partido, UF e ocupação da cadeira
por período, incluindo suplente em exercício. `partido` tem histórico de siglas
e linhagem de fusões, reconstruída por curadoria.

Há também `registro_fonte`, com classe de volatilidade e janela móvel por área,
e `quarentena`, para o que não passa nos portões de qualidade.

Quatro invariantes estão no banco como restrição, não como convenção: recusa
exige divergência declarada; grau `direto` exige ao menos dois sinais; uma
pessoa não ocupa duas cadeiras na mesma casa ao mesmo tempo; e fonte com
canário não validado não pode ser ativada — porque monitor que grita à toa é
monitor ignorado.

## O resolvedor

Dois tempos, na ordem que a seção 5.3 fixa. Primeiro as condições necessárias
eliminam candidatos: mandato vigente na data do fato, casa compatível. Só entre
os sobreviventes é que as evidências são somadas. Inverter isso é um dos doze
modos de falha catalogados — candidato fora de mandato somando pontos fabrica
ambiguidade onde não há.

Sinais são agrupados em famílias, e cada família contribui no máximo uma vez.
Nome civil e nome parlamentar derivam do mesmo cadastro e falham juntos.
Município de nascimento implica a UF. Contá-los separadamente fabricaria
confiança.

O grau é declarado, não estimado: dois ou mais sinais independentes sustentam
afirmação direta; um sinal isolado, afirmação com ressalva; sinais
contraditórios produzem recusa com a divergência exposta, nunca escolha pelo
mais provável.

**Um teste pegou um defeito real durante a implementação.** A primeira versão
só tratava divergência de nome civil como contradição quando o sufixo
geracional diferia; nomes civis simplesmente distintos passavam em silêncio, e
a data de nascimento sozinha bastava para aceitar. Isso produziria exatamente o
falso aceite que a seção 6.1 registra ter sido evitado — a data isolada colide
em nove por cento do universo, com até quatro parlamentares nascidos no mesmo
dia. Corrigido, e coberto por teste.

## packages/types

Além de transcrever o modelo, os tipos **resolvem divergências** encontradas na
auditoria do protótipo contra a documentação. As decisões estão comentadas no
código, junto do trecho que as motiva:

Perfil é polimórfico, com `PerfilRef` para uso em cards. Post carrega
`perfis[]` com papel explícito, porque o papel é dado de negócio — num post de
votação, "Votou a favor" e "Votou contra" no mesmo card mudam o sentido do que
se lê, e um modelo de autor único não representa isso. Sem essa junção, o feed
"Seguindo" e a aba "Feed" de cada perfil são inimplementáveis.

`confiancaIa` é `number | null`, nunca `0` como sentinela: no protótipo um story
em geração carrega `aiConf: 0`, e pelo predicado literal da regra isso seria
lido como baixa confiança. Não saber não é o mesmo que desconfiar — a função
`exigeRevisaoHumana` trata os dois casos, e ambos vão para revisão.

O enum de tipo de post adota os oito valores em minúsculas do app, não os
quatro capitalizados do admin, porque é sobre eles que a interface do feed
decide o que renderizar. `dislikes` está no modelo, por decisão de produto.
Datas são ISO-8601; as strings relativas do protótipo são formatação, não dado.

Consentimento nasce junto do usuário, com finalidade específica, e viaja dentro
de cada evento de engajamento. Base legal não é retroativa: evento gravado sem
finalidade vinculada é evento que não pode ser usado depois.

Verificação (selo azul) não é atributo de `Perfil` — perfis do Congresso não são
verificáveis por definição. O protótipo hoje tem `verificado` na entidade
parlamentar, que é justamente a que a regra proíbe de verificar.

## packages/ui

Tokens transcritos literalmente do protótipo, que é a autoridade sobre o
observável. O dourado está marcado no código com uso único — selo de
verificação — porque reutilizá-lo como acento destrói o sinal. E o `sky` do
admin no tema escuro (`#3A86C9`) difere do `sky` do app (`#2E7DD1`) de
propósito, para contraste sobre canvas escuro; há um teste de sanidade que
falha se alguém "unificar" os dois.

---

## O que ficou pendente, e por quê

**Contratos das APIs não verificados contra a fonte viva.** O ambiente onde este
código foi escrito não tem acesso de rede às interfaces da Câmara, do Senado e
do Portal da Transparência. A Metodologia exige verificação por consulta real,
com amostra e data registradas, e é explícita ao dizer que afirmação sobre
estrutura de fonte não se infere de documentação. Os pontos afetados estão
marcados no SQL com `[verificar]`.

**Layout do código de autor de emenda.** A seção 6.3 documenta que o código da
emenda embute um identificador de autor, com bijeção perfeita de 628 códigos
para 628 nomes em 2025. O recorte exato dos dígitos não consta da prosa.
`extrair_codigo_autor` está deliberadamente como `NotImplementedError`, com o
motivo no docstring, em vez de um palpite que passaria despercebido dentro de um
pipeline. A verificação da bijeção, essa sim, está pronta e testada.

**Monorepo ainda sem ferramenta de workspace.** Os dois pacotes têm
`package.json` e compilam isoladamente. A escolha entre pnpm workspaces,
Turborepo ou npm workspaces continua aberta.

## Próximo passo

Conferir o layout do código de emenda e os nomes de campo das fontes contra as
APIs reais, numa máquina com acesso. Com isso fechado, a Onda 0 está de pé e a
Onda 1 começa pela Câmara — proposições e votações, um tentáculo completo antes
do próximo.
