"""Entrypoint de produção da ingestão da Câmara.

Amarra o cliente HTTP real (urllib, stdlib) e o banco Supabase concreto ao
orquestrador. É o artefato de DEPLOY: aqui a lógica testada com fakes passa a
falar com a fonte viva e o banco real.

Rodar (no deploy, com o pacote `supabase` instalado e as variáveis definidas —
ver .env.example):

    pip install supabase
    export SUPABASE_URL=... SUPABASE_SERVICE_KEY=...
    python run_ingestao.py

Neste ambiente de desenvolvimento NÃO roda: o pacote `supabase` não está
instalado (a lógica inteira é coberta por 170+ testes sem rede). O import de
`supabase` é tardio (dentro de `criar_banco_supabase`), então este módulo é
importável sem o pacote.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from orquestracao.orquestrador import ingerir
from persistencia.supabase_adapter import criar_banco_supabase
from pipeline.coletor import JanelaMovel
from pipeline.http import ClienteHttpUrllib


def _flag(nome: str, padrao: bool = True) -> bool:
    """Lê uma flag booleana de ambiente. Ausente = `padrao`. Desliga com
    0/false/nao/off. Serve para separar a rodada LEVE (dado diário) das partes
    pesadas por deputado (histórico, despesas, enriquecimento), que têm
    volatilidade baixa e não precisam rodar toda vez (§3.3, cadência por área)."""
    v = os.environ.get(nome)
    if v is None:
        return padrao
    return v.strip().lower() not in ("0", "false", "nao", "não", "off", "no", "")


def main() -> None:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    janela_dias = int(os.environ.get("AQUARIUS_JANELA_DIAS", "30"))
    id_legislatura = os.environ.get("AQUARIUS_LEGISLATURA")

    http = ClienteHttpUrllib()
    banco = criar_banco_supabase(url, key)

    # Emendas (Portal da Transparência) só rodam com a chave `chave-api-dados`.
    # Sem ela, a área é pulada. Anos via AQUARIUS_EMENDAS_ANOS ("2024,2025").
    cliente_transparencia = None
    anos_emendas = None
    chave_transp = os.environ.get("AQUARIUS_TRANSPARENCIA_KEY")
    if chave_transp:
        cliente_transparencia = ClienteHttpUrllib(
            headers_extra={"chave-api-dados": chave_transp})
        anos_env = os.environ.get("AQUARIUS_EMENDAS_ANOS")
        anos_emendas = ([int(a) for a in anos_env.split(",") if a.strip()]
                        if anos_env else [datetime.now(timezone.utc).year])

    r = ingerir(
        http, banco,
        ate=datetime.now(timezone.utc).date(),
        janela=JanelaMovel(dias=janela_dias),
        id_legislatura=int(id_legislatura) if id_legislatura else None,
        # Partes pesadas por deputado — controláveis por env (padrão: ligadas).
        enriquecer_deputados=_flag("AQUARIUS_ENRIQUECER"),
        coletar_historico=_flag("AQUARIUS_HISTORICO"),
        coletar_despesas=_flag("AQUARIUS_DESPESAS"),
        cliente_transparencia=cliente_transparencia,
        anos_emendas=anos_emendas,
        # Senado (Área I, §17): fonte pública sem chave. Padrão ligado; a rodada
        # leve pode desligar com AQUARIUS_SENADO=0.
        coletar_senado=_flag("AQUARIUS_SENADO"),
        # Discursos das duas casas (Área G): por parlamentar, volumoso. Padrão
        # LIGADO na rodada completa; desligue na leve com AQUARIUS_DISCURSOS=0.
        coletar_discursos=_flag("AQUARIUS_DISCURSOS"),
    )

    print(
        "ingestão concluída — "
        f"partidos={r.partidos_salvos} perfis={r.perfis_salvos} "
        f"senado(novos={r.senadores_novos} vinculados={r.senadores_vinculados} "
        f"pendentes={r.senadores_pendentes}) "
        f"vinculos={r.vinculos_salvos} despesas={r.despesas_salvas} "
        f"emendas={r.emendas_salvas} discursos={r.discursos_salvos} "
        f"proposicoes={r.proposicoes_salvas} "
        f"comissoes_senado={r.comissoes_senado_salvas} "
        f"blocos_senado={r.blocos_senado_salvos} "
        f"vinculos_senado={r.vinculos_senado_salvos} "
        f"materias_senado={r.materias_senado_salvas} "
        f"tramitacoes_senado={r.tramitacoes_senado_salvas} "
        f"votacoes_senado={r.votacoes_senado_salvas} "
        f"votos_senado={r.votos_senado_salvos} "
        f"tramitacoes={r.tramitacoes_salvas} votacoes={r.votacoes_salvas} "
        f"votos={r.votos_salvos} bronze={r.bronze_salvo}"
    )
    if r.placar_violacoes:
        print(f"ATENÇÃO: {len(r.placar_violacoes)} votação(ões) da Câmara com "
              "divergência entre placar declarado e nominais (§5.2)")
    if r.placar_violacoes_senado:
        print(f"ATENÇÃO: {len(r.placar_violacoes_senado)} votação(ões) do Senado "
              "com divergência entre placar declarado e nominais (§5.2)")


if __name__ == "__main__":
    main()
