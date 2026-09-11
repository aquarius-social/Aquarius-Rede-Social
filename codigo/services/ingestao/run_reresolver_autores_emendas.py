"""Re-resolução da autoria de emendas — fecha os individuais que ficaram nulos.

POR QUE existe: o `orquestrador` resolve o autor de emenda por NOME
(`resolver_autores_emenda_por_nome`) contra APENAS os parlamentares ingeridos
NAQUELE ano/legislatura da rodada (orquestrador.py, montagem de
`lookup_parlamentar_nome`). Nos backfills, quando a casa do autor não estava
ingerida na hora (ex.: Senado desligado para caber no Free, ou legislatura do ano
diferente), autores como ZUCCO ficaram sem contra quem casar → `autor_profile_id`
nulo, corretamente. Os perfis deles JÁ existem hoje no banco; só nunca estiveram
no mapa na hora certa.

O QUE faz (OFFLINE — sem tocar API externa; idempotente):
  1. monta o `lookup_parlamentar_nome` com o universo COMPLETO de perfis
     `tipo='parlamentar'` do banco (as duas casas, todas as legislaturas), com a
     MESMA `normalizar` e a MESMA regra de homônimo→None do orquestrador;
  2. roda `resolver_autores_emenda_por_nome` sobre TODAS as emendas do banco →
     grava `id_externo(autor_orcamentario)` grau 'com_ressalva' +
     `pendente_conferencia` (nome = 1 sinal, §5.3) para os que casam; pula
     coletivo (bancada/comissão), homônimo e já-resolvido pelo mapa curado;
  3. re-preenche `emenda.autor_profile_id` (só as que estavam nulas e agora
     resolvem) a partir desse mesmo `id_externo`, via `rebackfill_autor_profile_id`.

NÃO inventa método novo: reusa as funções da ingestão. NÃO resolve autoria
COLETIVA (bancada/comissão) — isso é modelagem de entidade coletiva à parte.

Os vínculos entram como `pendente_conferencia=true` — a conferência humana revê
antes de o grau subir. Liste-os depois com, p.ex.:
    select identificador, profile_id, grau from id_externo
    where sistema='autor_orcamentario' and pendente_conferencia order by resolvido_em desc;

Uso (segredos SEMPRE no ambiente/.env, nunca no chat):
    $env:SUPABASE_URL="..."; $env:SUPABASE_SERVICE_KEY="..."
    py run_reresolver_autores_emendas.py
"""

from __future__ import annotations

import os

from persistencia.repositorio import (
    _autor_emenda_coletivo,
    lookup_id_externo,
    rebackfill_autor_profile_id,
    resolver_autores_emenda_por_nome,
)
from persistencia.supabase_adapter import criar_banco_supabase
from resolucao.normalizacao import normalizar

# Colunas mínimas lidas de cada tabela (a leitura é paginada no adapter).
_COLS_PERFIL = "id,nome"
_COLS_EMENDA = "codigo_emenda,autor_codigo,autor_nome,autor_profile_id"


def construir_lookup_parlamentar_nome(perfis):
    """Mapa nome-normalizado → profile_id a partir dos perfis dados. Nome que
    colide entre dois perfis vira AMBÍGUO → devolve None (homônimo não se atribui,
    §6.3). Mesma semântica do `orquestrador`, mas sobre o universo COMPLETO."""
    mapa: dict[str, str] = {}
    ambiguos: set[str] = set()
    for p in perfis:
        pid = p.get("id")
        nome = p.get("nome")
        if not pid or not nome:
            continue
        chave = normalizar(nome)
        if not chave:
            continue
        anterior = mapa.get(chave)
        if anterior is not None and anterior != pid:
            ambiguos.add(chave)          # dois perfis, mesmo nome → ambíguo
        else:
            mapa[chave] = pid

    def _lookup(nome):
        chave = normalizar(nome or "")
        if not chave or chave in ambiguos:
            return None
        return mapa.get(chave)

    return _lookup


def main() -> None:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    banco = criar_banco_supabase(url, key)

    perfis = banco.selecionar_muitos(
        "profiles", {"tipo": "parlamentar"}, _COLS_PERFIL, ordem="id")
    lookup_nome = construir_lookup_parlamentar_nome(perfis)
    lookup = lookup_id_externo(banco)

    emendas = banco.selecionar_muitos("emenda", None, _COLS_EMENDA, ordem="id")

    antes = sum(1 for e in emendas if e.get("autor_profile_id"))
    nulos_antes = len(emendas) - antes

    novos_ext = resolver_autores_emenda_por_nome(banco, emendas, lookup, lookup_nome)

    nulos = [e for e in emendas if not e.get("autor_profile_id")]
    revinculados = rebackfill_autor_profile_id(banco, nulos, lookup)

    # Sobras honestas entre os que continuam sem perfil.
    coletivo = sum(
        1 for e in nulos if _autor_emenda_coletivo(e.get("autor_nome") or ""))
    sem_match_cods = {
        e.get("autor_codigo") for e in nulos
        if not _autor_emenda_coletivo(e.get("autor_nome") or "")
        and lookup("autor_orcamentario", e.get("autor_codigo")) is None
        and e.get("autor_codigo")
    }

    print("=== Re-resolução de autoria de emendas (offline, idempotente) ===")
    print(f"  perfis parlamentares no mapa .... {len(perfis)}")
    print(f"  emendas lidas ................... {len(emendas)}")
    print(f"  já com perfil (antes) ........... {antes}  (nulas: {nulos_antes})")
    print(f"  id_externo novos (por nome) ..... {novos_ext}  [com_ressalva + pendente]")
    print(f"  emendas revinculadas ............ {revinculados}")
    print(f"  ainda sem perfil — coletivo ..... {coletivo}  [bancada/comissão: modelagem à parte]")
    print(f"  ainda sem perfil — sem match .... {len(sem_match_cods)} código(s) individual(is) p/ olhar manual")
    print("  Confira os pendentes em id_externo antes de subir o grau (ver docstring).")


if __name__ == "__main__":
    main()
