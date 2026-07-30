"""Normalização de nomes para comparação de identidade.

Implementa a seção 3.2 e a seção 6.2 da Metodologia de Dados.

A regra central, e o motivo dela (seção 6.2):

    "O caso-limite é real e está em exercício: dois senadores cujos nomes civis
     diferem apenas pela palavra final (pai e filho), padrão que se repete em
     vários pares homônimos da Câmara. Por isso a normalização preserva os
     sufixos geracionais, que são com frequência a única marca textual entre
     duas pessoas."

Normalizar demais funde duas pessoas num perfil — é um dos doze modos de falha
catalogados (Tabela 9: "Normalização excessiva de nomes").
"""

from __future__ import annotations

import re
import unicodedata

VERSAO_REGRA = "normalizacao-1.0.0"

# Partículas de ligação: removidas para comparação porque variam livremente
# entre fontes ("Maria de Souza" / "Maria Souza"). Não carregam identidade.
PARTICULAS_LIGACAO = frozenset(
    {"de", "da", "do", "das", "dos", "e", "di", "du", "del", "della", "van", "von", "la", "le"}
)

# Sufixos geracionais: PRESERVADOS. Com frequência são a única marca textual
# entre pai e filho (seção 6.2).
SUFIXOS_GERACIONAIS = frozenset(
    {
        "filho",
        "filha",
        "neto",
        "neta",
        "sobrinho",
        "sobrinha",
        "junior",
        "jr",
        "senior",
        "sr",
        "segundo",
        "terceiro",
        "ii",
        "iii",
        "iv",
    }
)

# Títulos e patentes que aparecem em uma fonte e faltam em outra. A seção 6.3
# documenta isso como resíduo que o resolvedor NÃO deve tentar aproximar
# sozinho: "patente militar presente numa fonte e ausente na outra, título
# religioso abreviado". Marcamos, mas não removemos silenciosamente — quem
# decide o que fazer é o resolvedor, que registra a ressalva.
TITULOS_E_PATENTES = frozenset(
    {
        "dr", "dra", "prof", "professor", "professora",
        "pastor", "pastora", "padre", "frei", "bispo", "irma", "irmao",
        "delegado", "delegada", "capitao", "capita", "major", "coronel",
        "tenente", "sargento", "soldado", "cabo", "general", "almirante",
        "deputado", "deputada", "senador", "senadora", "vereador", "vereadora",
    }
)


def _remover_acentos(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def tokens(nome: str) -> list[str]:
    """Quebra o nome em tokens minúsculos e sem acento, sem descartar nada."""
    if not nome:
        return []
    limpo = _remover_acentos(nome).lower()
    limpo = limpo.replace(".", " ")
    limpo = re.sub(r"[^a-z0-9\s'-]", " ", limpo)
    return [t for t in limpo.split() if t]


def normalizar(nome: str) -> str:
    """Forma canônica para comparação.

    Remove caixa, acentos e partículas de ligação.
    PRESERVA sufixos geracionais — ver seção 6.2.

    >>> normalizar("José de Souza Filho")
    'jose souza filho'
    >>> normalizar("Jose Souza")
    'jose souza'
    >>> normalizar("José de Souza Filho") == normalizar("José de Souza")
    False
    """
    ts = tokens(nome)
    mantidos = [
        t
        for t in ts
        if t not in PARTICULAS_LIGACAO or t in SUFIXOS_GERACIONAIS
    ]
    return " ".join(mantidos)


def sufixo_geracional(nome: str) -> str | None:
    """Devolve o sufixo geracional do nome, se houver."""
    ts = tokens(nome)
    for t in reversed(ts):
        if t in SUFIXOS_GERACIONAIS:
            return t
        if t not in PARTICULAS_LIGACAO:
            return None
    return None


def tem_titulo_ou_patente(nome: str) -> bool:
    """Indica presença de título/patente — sinal de que a comparação textual
    direta pode falhar por variação de fonte (seção 6.3)."""
    return any(t in TITULOS_E_PATENTES for t in tokens(nome))


def sem_titulos(nome: str) -> str:
    """Forma canônica com títulos e patentes removidos.

    Uso restrito: serve para DETECTAR que dois nomes podem ser a mesma pessoa,
    nunca para AFIRMAR que são. A seção 6.3 é explícita ao mandar deixar essas
    linhas sem atribuição, para conferência humana.
    """
    ts = tokens(nome)
    mantidos = [
        t
        for t in ts
        if (t not in PARTICULAS_LIGACAO and t not in TITULOS_E_PATENTES)
        or t in SUFIXOS_GERACIONAIS
    ]
    return " ".join(mantidos)


def mesmo_nome(a: str, b: str) -> bool:
    """Igualdade estrita entre formas normalizadas.

    Deliberadamente NÃO faz correspondência aproximada. A Metodologia constrói
    confiança por convergência de sinais independentes, não por similaridade
    textual — que é exatamente o que fabrica falsos aceites entre pai e filho.
    """
    return bool(a) and bool(b) and normalizar(a) == normalizar(b)
