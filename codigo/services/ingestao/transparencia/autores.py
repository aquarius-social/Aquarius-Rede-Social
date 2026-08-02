"""Curadoria — autor de emenda → perfil (§6.3, resolução de entidade).

A execução orçamentária (emendas) identifica o autor por um CÓDIGO embutido no
`codigoEmenda` (§6.3), não por id de Câmara/Senado. Esta curadoria carrega o
mapa `codigo_autor → parlamentar` (auto-gerado por convergência de sinais: nome,
UF, tokens) e o materializa como `id_externo` (sistema='autor_orcamentario'),
que é o que `salvar_emendas` consulta para preencher `emenda.autor_profile_id`.

Fonte: `dados/mapa_autores_emendas_2025.csv` (629 linhas; 628 autores). Colunas:
    codigo_autor;nome_na_fonte;deputado_id;nome_camara;sinais;n_sinais;classe;
    ufs_do_gasto;conferido_por_humano

DOIS BRAÇOS de resolução (§17, a paridade que faltava à curadoria):
  - Câmara: `deputado_id` presente → resolve por id_externo(camara).
  - Senado: sem `deputado_id`, mas o nome casa um SENADOR (ex.: AUGUSTA BRITO,
    JORGE SEIF, RODRIGO CUNHA, ZUCCO estão entre os "não resolvido" porque o mapa
    só tentou casar contra a Câmara) → resolve por nome parlamentar normalizado.
  - Bancadas estaduais e comissões (coletivo) ficam SEM perfil por ora (não há
    tipo de perfil 'bancada'; honesto, não inventado).

Grau (§5.3): o mapa NÃO é conferido por humano (auto-match), então o grau vem do
número de sinais — 2+ → 'direto'; 1 sinal só → 'com_ressalva' + pendente de
conferência. Nunca afirma o que um sinal isolado não sustenta.
"""

from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass
from typing import Any, Callable

from contrato.canario import EstadoContrato, avaliar
from pipeline.camadas import (
    RegistroBronze,
    ResultadoPortao,
    campo_obrigatorio,
    portao_bronze_prata,
)

FONTE = "curadoria.autores_emendas"

CAMINHO_MAPA_PADRAO = os.path.join(
    os.path.dirname(__file__), "..", "dados", "mapa_autores_emendas_2025.csv")

CAMPOS_CRITICOS_AUTOR = frozenset({"codigo_autor", "nome_na_fonte"})


def abrir_mapa_padrao() -> str:
    """Lê o mapa curado do repositório (UTF-8). No deploy é o default; nos testes
    um duble devolve o texto direto."""
    with open(CAMINHO_MAPA_PADRAO, encoding="utf-8-sig") as f:
        return f.read()


def _linhas_csv(texto: str) -> list[dict]:
    return [dict(r) for r in csv.DictReader(io.StringIO(texto), delimiter=";")]


def coletar_bronze_autores(abrir: Callable[[], str]) -> list[RegistroBronze]:
    """Um bronze por linha do mapa (dict cru)."""
    texto = abrir()
    return [RegistroBronze.de(FONTE, CAMINHO_MAPA_PADRAO, row)
            for row in _linhas_csv(texto)]


def _sinais(v: Any) -> list[str]:
    return [s.strip() for s in str(v or "").split(",") if s.strip()]


def transformar_autor(row: dict) -> dict:
    dep = (row.get("deputado_id") or "").strip()
    return {
        "codigo_autor": (row.get("codigo_autor") or "").strip() or None,
        "nome_na_fonte": (row.get("nome_na_fonte") or "").strip() or None,
        "deputado_id": dep or None,
        "sinais": _sinais(row.get("sinais")),
        "classe": (row.get("classe") or "").strip() or None,
    }


VERIFICADORES_AUTOR = [
    campo_obrigatorio("codigo_autor"),
    campo_obrigatorio("nome_na_fonte"),
]


def processar_autores_para_prata(bronze: list[RegistroBronze]) -> ResultadoPortao:
    return portao_bronze_prata(
        bronze, transformar=transformar_autor, verificadores=VERIFICADORES_AUTOR)


@dataclass
class ResultadoRodadaAutores:
    estado: EstadoContrato
    detalhe: str
    bronze: list[RegistroBronze]
    prata: ResultadoPortao | None = None


def rodada_autores(
    abrir: Callable[[], str], *, canario_validado: bool,
    linha_base: frozenset[str] | None,
) -> ResultadoRodadaAutores:
    erro = None
    bronze: list[RegistroBronze] = []
    try:
        bronze = coletar_bronze_autores(abrir)
    except OSError as e:
        erro = str(e)

    amostra = bronze[0].payload if bronze else None
    contrato = avaliar(
        canario_validado=canario_validado,
        resposta=[amostra] if amostra is not None else None,
        erro_instabilidade=erro,
        linha_base=linha_base, criticos=CAMPOS_CRITICOS_AUTOR,
    )
    if contrato.estado in (EstadoContrato.FALHA, EstadoContrato.QUEBRA):
        return ResultadoRodadaAutores(contrato.estado, contrato.detalhe, bronze)
    prata = processar_autores_para_prata(bronze)
    return ResultadoRodadaAutores(contrato.estado, contrato.detalhe, bronze, prata)
