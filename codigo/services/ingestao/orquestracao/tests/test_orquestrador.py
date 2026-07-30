"""Teste de integração do orquestrador — HTTP e banco fakes, sem rede.

Prova o que o orquestrador existe para garantir: como os deputados são
ingeridos ANTES das votações, o lookup real de id_externo resolve os votos
nominais de ponta a ponta. Se a ordem quebrar, os votos caem na quarentena e
`votos_salvos` despenca — é o que o segundo teste fixa.
"""

import unittest
from datetime import date
from typing import Any

from orquestracao.orquestrador import LinhasBase, ingerir
from pipeline.coletor import JanelaMovel

BASE = "https://dadosabertos.camara.leg.br/api/v2"


class _Resp:
    def __init__(self, status: int, corpo: Any):
        self.status = status
        self.corpo = corpo
    def texto(self) -> str:
        return str(self.corpo)


class ClienteHttpFake:
    """Responde por URL (ignora params). Fila por URL; erro se URL não mapeada."""
    def __init__(self, por_url: dict[str, Any]):
        self.por_url = por_url
        self.chamadas: list[str] = []
    def get(self, url: str, params: dict | None = None) -> _Resp:
        self.chamadas.append(url)
        if url not in self.por_url:
            raise AssertionError(f"sem resposta para {url}")
        return self.por_url[url]


class FakeBanco:
    _CHAVE_BRONZE = ("fonte", "id_na_fonte", "hash_conteudo")
    def __init__(self):
        self.tabelas: dict[str, list[dict]] = {}
        self._seq = 0
    def _t(self, nome): return self.tabelas.setdefault(nome, [])
    def upsert(self, tabela, linhas, *, conflito):
        cols = [c.strip() for c in conflito.split(",")]
        out = []
        for linha in linhas:
            ex = next((r for r in self._t(tabela)
                       if all(r.get(c) == linha.get(c) for c in cols)), None)
            if ex is not None:
                ex.update(linha); out.append(dict(ex))
            else:
                self._seq += 1
                row = dict(linha); row.setdefault("id", f"{tabela}-{self._seq}")
                self._t(tabela).append(row); out.append(dict(row))
        return out
    def inserir_ignorando_conflito(self, tabela, linhas):
        n = 0
        for linha in linhas:
            if any(all(r.get(c) == linha.get(c) for c in self._CHAVE_BRONZE)
                   for r in self._t(tabela)):
                continue
            self._seq += 1
            row = dict(linha); row.setdefault("id", f"{tabela}-{self._seq}")
            self._t(tabela).append(row); n += 1
        return n
    def selecionar_um(self, tabela, onde):
        for r in self._t(tabela):
            if all(r.get(k) == v for k, v in onde.items()):
                return dict(r)
        return None


# -----------------------------------------------------------------------------
# Fixtures de payload
# -----------------------------------------------------------------------------

def _dep(did, nome):
    return {"id": did, "nome": nome, "siglaPartido": "PT", "siglaUf": "SP",
            "idLegislatura": 57, "urlFoto": f"https://x/{did}.jpg",
            "uri": f"{BASE}/deputados/{did}"}

def _dep_det(did):
    return {"id": did, "nomeCivil": f"Nome Civil {did}",
            "dataNascimento": "1970-01-01", "municipioNascimento": "São Paulo",
            "ufNascimento": "SP", "ultimoStatus": {"siglaPartido": "PSD"}}

def _prop(pid):
    return {"id": pid, "siglaTipo": "PL", "numero": 736, "ano": 2015,
            "ementa": "Dispõe sobre algo.", "dataApresentacao": "2015-03-12T18:32"}

def _votacao():
    return {"id": "V-1", "data": "2023-06-10",
            "dataHoraRegistro": "2023-06-10T14:00:00",
            "descricao": "Aprovado. Sim: 1; não: 1; total: 2.",
            "aprovacao": 1,
            "proposicoesAfetadas": [{"id": "100", "uri": f"{BASE}/proposicoes/100"}]}

def _voto(did, tipo):
    return {"tipoVoto": tipo, "deputado_": {
        "id": did, "nome": f"n{did}", "siglaPartido": "PT", "siglaUf": "SP"}}

def _hist(did):
    return {"id": did, "dataHora": "2023-02-01T10:00", "idLegislatura": 57,
            "siglaPartido": "PT", "siglaUf": "SP",
            "condicaoEleitoral": "Titular", "situacao": "Exercício"}


def _mundo(deputados_resp=None):
    """Fábrica do fake HTTP com o mundo inteiro programado."""
    dep_list = deputados_resp if deputados_resp is not None else _Resp(200, {
        "dados": [_dep(1, "Ana"), _dep(2, "Bruno")], "links": []})
    return ClienteHttpFake({
        f"{BASE}/partidos": _Resp(200, {"dados": [
            {"id": 10, "sigla": "PT", "nome": "Partido dos Trabalhadores"}],
            "links": []}),
        f"{BASE}/partidos/10": _Resp(200, {"dados": {
            "id": 10, "numeroEleitoral": 13, "status": {"situacao": "Ativo"}}}),
        f"{BASE}/deputados": dep_list,
        f"{BASE}/deputados/1": _Resp(200, {"dados": _dep_det(1)}),
        f"{BASE}/deputados/2": _Resp(200, {"dados": _dep_det(2)}),
        f"{BASE}/deputados/1/historico": _Resp(200, {"dados": [_hist(1)]}),
        f"{BASE}/deputados/2/historico": _Resp(200, {"dados": [_hist(2)]}),
        f"{BASE}/proposicoes": _Resp(200, {"dados": [_prop("100")], "links": []}),
        f"{BASE}/proposicoes/100/tramitacoes": _Resp(200, {"dados": [
            {"sequencia": 1, "dataHora": "2015-03-12T18:32", "siglaOrgao": "PLEN",
             "descricaoTramitacao": "Apresentação", "despacho": None},
            {"sequencia": 2, "dataHora": "2015-03-15T09:00", "siglaOrgao": "CCJC",
             "descricaoTramitacao": "Às Comissões", "despacho": "Despacho x"},
        ], "links": []}),
        f"{BASE}/votacoes": _Resp(200, {"dados": [_votacao()], "links": []}),
        f"{BASE}/votacoes/V-1": _Resp(200, {"dados": _votacao()}),
        f"{BASE}/votacoes/V-1/votos": _Resp(200, {"dados": [
            _voto(1, "Sim"), _voto(2, "Não")]}),
    })


class TestOrquestrador(unittest.TestCase):
    def test_fluxo_completo_resolve_votos_ponta_a_ponta(self):
        http = _mundo()
        banco = FakeBanco()
        r = ingerir(http, banco, ate=date(2023, 6, 30), janela=JanelaMovel(dias=30),
                    id_legislatura=57)

        # perfis + id_externo (profiles inclui os 2 parlamentares + 1 partido)
        self.assertEqual(r.perfis_salvos, 2)
        parlamentares = [p for p in banco.tabelas["profiles"]
                         if p["tipo"] == "parlamentar"]
        self.assertEqual(len(parlamentares), 2)
        self.assertEqual(len(banco.tabelas["id_externo"]), 2)

        # partidos canônicos ingeridos (profile tipo=partido + partido)
        self.assertEqual(r.partidos_salvos, 1)

        # vínculos temporais (um titular por pessoa, em aberto) — camada §4
        self.assertEqual(r.vinculos_salvos, 2)
        self.assertEqual(len(banco.tabelas["vinculo_temporal"]), 2)
        # partido_id RESOLVIDO por sigla (PT foi ingerido no passo 0)
        partido_pt = banco.tabelas["partido"][0]["id"]
        v0 = banco.tabelas["vinculo_temporal"][0]
        self.assertEqual(v0["partido_sigla_fonte"], "PT")
        self.assertEqual(v0["partido_id"], partido_pt)

        # proposição + suas tramitações (prendem-se à proposição já persistida)
        self.assertEqual(r.proposicoes_salvas, 1)
        self.assertEqual(r.tramitacoes_salvas, 2)
        self.assertEqual(len(banco.tabelas["tramitacao"]), 2)
        prop_uuid_t = banco.tabelas["proposicao"][0]["id"]
        for t in banco.tabelas["tramitacao"]:
            self.assertEqual(t["proposicao_id"], prop_uuid_t)

        # votação com a matéria resolvida (FK uuid, não o id da fonte)
        self.assertEqual(r.votacoes_salvas, 1)
        prop_uuid = banco.tabelas["proposicao"][0]["id"]
        self.assertEqual(banco.tabelas["votacao"][0]["proposicao_id"], prop_uuid)

        # OS VOTOS RESOLVERAM porque os deputados vieram antes → lookup real
        self.assertEqual(r.votos_salvos, 2)
        perfis_ids = {p["id"] for p in banco.tabelas["profiles"]}
        for v in banco.tabelas["voto_nominal"]:
            self.assertIn(v["perfil_id"], perfis_ids)

        # placar bate com os nominais → sem divergência (§5.2)
        self.assertEqual(r.placar_violacoes, {})

        # Preservação de bronze COMPLETA (§3.1): lista+detalhe da votação e os
        # votos, além de deputados e proposição. O voto tem id composto.
        ids_bronze = {b["id_na_fonte"] for b in banco.tabelas["bronze_registro"]}
        self.assertIn("V-1:1", ids_bronze)   # voto do deputado 1 na votação V-1
        self.assertIn("V-1:2", ids_bronze)   # voto do deputado 2
        # 2 deputados + 1 prop + 1 tramitação(seq via prop) ... ao menos as
        # listas + detalhe da votação + 2 votos entram na contagem.
        self.assertGreaterEqual(r.bronze_salvo, 6)

    def test_data_apresentacao_persistida_como_date(self):
        http = _mundo()
        banco = FakeBanco()
        ingerir(http, banco, ate=date(2023, 6, 30), janela=JanelaMovel(dias=30))
        self.assertEqual(
            banco.tabelas["proposicao"][0]["data_apresentacao"], "2015-03-12")

    def test_deputados_ausentes_deixam_votos_sem_resolver(self):
        """A dependência de ordem, provada pela negativa: sem deputados, o lookup
        não resolve e nenhum voto nominal é persistido — mas a rodada não cai."""
        http = _mundo(deputados_resp=_Resp(404, "not found"))
        banco = FakeBanco()
        r = ingerir(http, banco, ate=date(2023, 6, 30), janela=JanelaMovel(dias=30))

        self.assertEqual(r.perfis_salvos, 0)
        self.assertEqual(r.votos_salvos, 0)            # votos caíram na quarentena
        self.assertEqual(r.votacoes_salvas, 1)         # a votação em si persiste
        self.assertNotIn("voto_nominal", banco.tabelas)


if __name__ == "__main__":
    unittest.main(verbosity=2)
