"""Coletor do Senado — CEAPS / verba indenizatória (Área A, §8, bicameral).

Fonte (CSV anual, ISO-8859-1, `;`-separado, com aspas):
    https://www.senado.gov.br/transparencia/LAI/verba/despesa_ceaps_{ano}.csv
Verificado ao vivo em 2026-08-01 (2024: 5.471 linhas, atualizado no mesmo dia;
2025: 6.372). A URL correta (`despesa_ceaps_{ano}.csv`, NÃO `{ano}.csv`) foi
recuperada de snapshots recentes do Internet Archive — o serviço JSON dedicado
(`adm.senado.gov.br`) estava fora do ar, mas o CSV oficial sempre esteve vivo.

Diferenças em relação à CEAP da Câmara:
  - Formato CSV (não JSON) e ISO-8859-1 → fetcher PRÓPRIO, injetável (`baixar`),
    porque o cliente HTTP compartilhado decodifica UTF-8 e presume JSON.
  - O senador é identificado por NOME (não por código) → resolução por nome
    parlamentar normalizado (§6.2), não por id_externo direto.
  - NÃO há glosa: só `VALOR_REEMBOLSADO`. Sem identidade aritmética §5.2 a checar
    (documento−glosa=líquido não se aplica); grava-se `valor_glosa=None`, e o
    valor vai em `valor_documento` e `valor_liquido` (o reembolsado é o líquido).

Colunas: ANO;MES;SENADOR;TIPO_DESPESA;CNPJ_CPF;FORNECEDOR;DOCUMENTO;DATA;
         DETALHAMENTO;VALOR_REEMBOLSADO;COD_DOCUMENTO
`DETALHAMENTO` não tem coluna na tabela `despesa` (paridade com a Câmara, que
também não a tem) — é descartado, honestamente.
"""

from __future__ import annotations

import csv
import io
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from contrato.canario import EstadoContrato, avaliar
from pipeline.camadas import (
    RegistroBronze,
    ResultadoPortao,
    campo_obrigatorio,
    portao_bronze_prata,
)

FONTE = "senado.ceaps"
URL_MODELO = "https://www.senado.gov.br/transparencia/LAI/verba/despesa_ceaps_{ano}.csv"

CAMPOS_CRITICOS_CEAPS = frozenset({
    "ANO", "MES", "SENADOR", "VALOR_REEMBOLSADO", "COD_DOCUMENTO",
})


# -----------------------------------------------------------------------------
# Fetcher próprio (CSV, ISO-8859-1) — injetável para o teste rodar sem rede
# -----------------------------------------------------------------------------

def baixar_ceaps_urllib(url: str, *, timeout: float = 90.0) -> str:
    """Baixa o CSV e decodifica ISO-8859-1. Usado no deploy; nos testes um
    duble devolve o texto direto."""
    # Accept restritivo (text/csv) leva a 406 nesse servidor — usa */*.
    req = urllib.request.Request(
        url, headers={"User-Agent": "AquariusIngest/1.0", "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("latin-1")


def _linhas_csv(texto: str) -> list[dict]:
    """Parseia o CSV com `csv.reader` sobre o TEXTO INTEIRO (não linha a linha),
    para tratar corretamente aspas e quebras de linha DENTRO de campos (o
    `DETALHAMENTO` pode conter `\\n`). Pula o metadado 'ULTIMA ATUALIZACAO' e usa
    a linha que começa em ANO como cabeçalho."""
    linhas = list(csv.reader(io.StringIO(texto), delimiter=";"))
    hidx = next(
        (i for i, r in enumerate(linhas)
         if r and r[0].strip().upper() == "ANO"), 0)
    header = [c.strip() for c in linhas[hidx]]
    out: list[dict] = []
    for r in linhas[hidx + 1:]:
        if not r or len(r) < 2:
            continue
        out.append(dict(zip(header, r)))
    return out


def coletar_bronze_ceaps(
    baixar: Callable[[str], str], ano: int,
) -> list[RegistroBronze]:
    """Baixa e parseia o CSV do exercício. Um bronze por linha (dict cru)."""
    url = URL_MODELO.format(ano=ano)
    texto = baixar(url)
    return [RegistroBronze.de(FONTE, url, row) for row in _linhas_csv(texto)]


# -----------------------------------------------------------------------------
# Transformação
# -----------------------------------------------------------------------------

def _int(v: Any) -> int | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _valor(v: Any) -> float | None:
    """Formato BR ('1.234,56' → 1234.56; '583,58' → 583.58). Vazio → None."""
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _data_br(v: Any) -> str | None:
    """DD/MM/YYYY → ISO YYYY-MM-DD. Vazio/ inválido → None."""
    if not v:
        return None
    partes = str(v).strip().split("/")
    if len(partes) != 3:
        return None
    d, m, a = partes
    if not (d and m and a):
        return None
    return f"{a}-{m.zfill(2)}-{d.zfill(2)}"


def transformar_despesa_senado(row: dict) -> dict:
    valor = _valor(row.get("VALOR_REEMBOLSADO"))
    return {
        # Resolução por NOME (não código) — a fonte não traz id do senador.
        "senador_nome": (row.get("SENADOR") or "").strip() or None,
        "ano": _int(row.get("ANO")),
        "mes": _int(row.get("MES")),
        "tipo_despesa": (row.get("TIPO_DESPESA") or "").strip() or None,
        "tipo_documento": None,
        "cod_documento": _int(row.get("COD_DOCUMENTO")),
        "num_documento": (row.get("DOCUMENTO") or "").strip() or None,
        # Senado não tem parcela; 0 (não null) para a unique key
        # (perfil, cod_documento, parcela) dedupar de verdade.
        "parcela": 0,
        "data_documento": _data_br(row.get("DATA")),
        "valor_documento": valor,
        "valor_glosa": None,          # sem glosa no Senado
        "valor_liquido": valor,       # reembolsado = líquido
        "fornecedor_nome": (row.get("FORNECEDOR") or "").strip() or None,
        "fornecedor_cnpj_cpf": (row.get("CNPJ_CPF") or "").strip() or None,
        "url_documento": None,
    }


VERIFICADORES_CEAPS = [
    campo_obrigatorio("senador_nome"),
    campo_obrigatorio("ano"),
    campo_obrigatorio("mes"),
    campo_obrigatorio("cod_documento"),   # sem ele não há como dedupar (§ idempotência)
]


def processar_ceaps_para_prata(bronze: list[RegistroBronze]) -> ResultadoPortao:
    return portao_bronze_prata(
        bronze, transformar=transformar_despesa_senado,
        verificadores=VERIFICADORES_CEAPS)


# -----------------------------------------------------------------------------
# Rodada — por exercício
# -----------------------------------------------------------------------------

@dataclass
class ResultadoRodadaCeaps:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    prata: ResultadoPortao | None = None


def rodada_ceaps(
    baixar: Callable[[str], str], ano: int, *,
    canario_validado: bool, linha_base: frozenset[str] | None,
) -> ResultadoRodadaCeaps:
    from pipeline.coletor import ErroFalha, ErroInstabilidade
    erro_falha = erro_instabilidade = None
    bronze: list[RegistroBronze] = []
    try:
        bronze = coletar_bronze_ceaps(baixar, ano)
    except ErroFalha as e:
        erro_falha = str(e)
    except (ErroInstabilidade, OSError) as e:
        erro_instabilidade = str(e)

    amostra = bronze[0].payload if bronze else None
    contrato = avaliar(
        canario_validado=canario_validado,
        resposta=[amostra] if amostra is not None else None,
        erro_falha=erro_falha, erro_instabilidade=erro_instabilidade,
        linha_base=linha_base, criticos=CAMPOS_CRITICOS_CEAPS,
    )
    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaCeaps(contrato.estado, contrato.detalhe, bronze)
    prata = processar_ceaps_para_prata(bronze)
    return ResultadoRodadaCeaps(contrato.estado, contrato.detalhe, bronze, prata)
