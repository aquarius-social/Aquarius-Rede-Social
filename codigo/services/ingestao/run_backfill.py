"""Backfill histórico — ingere um intervalo de anos (default 2018–2026).

É o MESMO código do `run_ingestao.py`, mas ITERA ano a ano, ligando TODAS as
áreas (as duas casas) e mapeando cada ano à sua legislatura. Cada `ingerir` de
um ano usa uma janela de ~1 ano terminando em 31/dez daquele ano.

Estratégia (conversada com o usuário): construir a base dos ÚLTIMOS MANDATOS
primeiro (2018–2026 ≈ legislaturas 55/56/57), barato, cobrindo a memória política
viva; o legado mais antigo entra depois, estendendo o intervalo — MUDANÇA DE
CONFIG, não de código.

Idempotente (tudo é upsert): pode rerodar, pode interromper (Ctrl+C) e continuar
— cada ANO é um checkpoint. Anos rodam em ordem crescente de propósito: os
deputados de uma legislatura mais antiga já estão no banco quando os fatos do
ano seguinte precisam resolvê-los.

⚠️ É PESADO — horas e centenas de milhares de chamadas de API (tramitações são
uma consulta por proposição; despesas/discursos uma por parlamentar por ano).
COMECE por um ano só para medir o tempo:

    $env:SUPABASE_URL="..."; $env:SUPABASE_SERVICE_KEY="..."
    $env:AQUARIUS_BACKFILL_INICIO="2025"; $env:AQUARIUS_BACKFILL_FIM="2025"
    py run_backfill.py

Depois solte o intervalo inteiro (INICIO=2018, FIM=2026). Emendas só entram com
`AQUARIUS_TRANSPARENCIA_KEY`; CEAPS e o resto não precisam de chave.
"""

from __future__ import annotations

import os
import traceback
from datetime import date

from env_local import carregar_env
from orquestracao.orquestrador import ingerir
from persistencia.supabase_adapter import criar_banco_supabase
from pipeline.coletor import JanelaMovel
from pipeline.http import ClienteHttpUrllib
from senado.despesas import baixar_ceaps_urllib
from transparencia.autores import abrir_mapa_padrao


def legislatura_do_ano(ano: int) -> int:
    """Mapeia um ano-calendário à legislatura predominante (para saber QUAIS
    parlamentares ingerir). 55ª: 2015–2019 · 56ª: 2019–2023 · 57ª: 2023–2027."""
    if ano <= 2018:
        return 55
    if ano <= 2022:
        return 56
    return 57


def main() -> None:
    carregar_env()  # segredos do .env local (padrão); não sobrescreve o ambiente
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    inicio = int(os.environ.get("AQUARIUS_BACKFILL_INICIO", "2018"))
    fim = int(os.environ.get("AQUARIUS_BACKFILL_FIM", "2026"))

    http = ClienteHttpUrllib()
    banco = criar_banco_supabase(url, key)

    # Emendas exigem a chave da Transparência; sem ela, a área é pulada.
    chave_transp = os.environ.get("AQUARIUS_TRANSPARENCIA_KEY")
    cliente_transp = (
        ClienteHttpUrllib(headers_extra={"chave-api-dados": chave_transp})
        if chave_transp else None)

    # ÁREAS por env (padrão LIGADO). Para caber no Free e priorizar dinheiro
    # público, desligue as grandes: AQUARIUS_BRONZE=0 (o maior peso — o app lê da
    # camada ouro, não do bronze), AQUARIUS_PROPOSICOES=0, AQUARIUS_VOTACOES=0,
    # AQUARIUS_DISCURSOS=0, AQUARIUS_EVENTOS=0, AQUARIUS_SENADO=0. Mantenha
    # AQUARIUS_DESPESAS=1 (e a chave da Transparência para emendas).
    def _flag(nome: str, padrao: bool = True) -> bool:
        v = os.environ.get(nome)
        if v is None:
            return padrao
        return v.strip().lower() not in ("0", "false", "nao", "não", "off", "no", "")

    print(f"=== BACKFILL {inicio}–{fim} — PESADO (horas). "
          "Ctrl+C pausa; rerodar continua (idempotente). ===")

    for ano in range(inicio, fim + 1):
        leg = legislatura_do_ano(ano)
        print(f"\n>>> Ano {ano} (legislatura {leg}) — ingerindo...", flush=True)
        try:
            r = ingerir(
                http, banco,
                ate=date(ano, 12, 31),
                janela=JanelaMovel(dias=366),
                id_legislatura=leg,
                legislatura_senado=leg,
                enriquecer_deputados=_flag("AQUARIUS_ENRIQUECER"),
                coletar_historico=_flag("AQUARIUS_HISTORICO"),
                coletar_despesas=_flag("AQUARIUS_DESPESAS"),
                ano_despesas=ano,
                cliente_transparencia=cliente_transp,
                anos_emendas=[ano],
                coletar_senado=_flag("AQUARIUS_SENADO"),
                coletar_despesas_senado=_flag("AQUARIUS_CEAPS"),
                coletar_discursos=_flag("AQUARIUS_DISCURSOS"),
                coletar_eventos=_flag("AQUARIUS_EVENTOS"),
                persistir_bronze=_flag("AQUARIUS_BRONZE"),
                coletar_proposicoes=_flag("AQUARIUS_PROPOSICOES"),
                coletar_votacoes=_flag("AQUARIUS_VOTACOES"),
                baixar_ceaps=baixar_ceaps_urllib,
                anos_ceaps=[ano],
                abrir_mapa_autores=abrir_mapa_padrao,
            )
            print(
                f"    OK {ano}: perfis={r.perfis_salvos} "
                f"proposicoes={r.proposicoes_salvas} votos={r.votos_salvos} "
                f"despesas={r.despesas_salvas} discursos={r.discursos_salvos} "
                f"eventos={r.eventos_salvos} emendas={r.emendas_salvas} "
                f"autores_nome={r.autores_emenda_por_nome} "
                f"materias_sen={r.materias_senado_salvas} "
                f"votos_sen={r.votos_senado_salvos} despesas_sen={r.despesas_senado_salvas} "
                f"bronze={r.bronze_salvo}",
                flush=True)
        except KeyboardInterrupt:
            print(f"\n[pausado no ano {ano}. Rerodar continua daqui.]")
            raise
        except Exception:  # noqa: BLE001 — um ano que falha não derruba o backfill
            print(f"    ERRO no ano {ano} — pulando (reveja depois):")
            traceback.print_exc()

    print("\n=== BACKFILL concluído ===")


if __name__ == "__main__":
    main()
