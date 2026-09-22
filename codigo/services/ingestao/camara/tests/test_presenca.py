"""Testes do coletor e persistência de presença (Área E).

Sem rede: cliente HTTP e banco são dubles. Cada regra tem um caso que ACEITA e
um que RECUSA (disciplina da Metodologia §5.2)."""
import unittest
from typing import Any

from camara.presenca import (
    rodada_sessoes, rodada_presencas, transformar_sessao, transformar_presenca,
    processar_presencas_para_prata)
from persistencia.repositorio import salvar_sessoes, salvar_presencas
from pipeline.camadas import RegistroBronze


class _Resp:
    def __init__(self, status: int, corpo: Any):
        self.status = status
        self.corpo = corpo
    def texto(self) -> str:
        return str(self.corpo)


class _ClienteFake:
    """Roteia por substring da URL: presença (/deputados) antes de sessões."""
    def __init__(self, sessoes: Any, presencas: dict[str, Any]):
        self._sessoes = sessoes
        self._presencas = presencas
    def get(self, url: str, params: dict | None = None) -> _Resp:
        if "/deputados" in url:
            vid = url.split("/eventos/")[1].split("/")[0]
            return _Resp(200, {"dados": self._presencas.get(vid, [])})
        if "/eventos" in url:
            return _Resp(200, {"dados": self._sessoes, "links": []})
        return _Resp(200, {"dados": [], "links": []})


_SESSAO_PLEN = {"id": 71957, "descricaoTipo": "Sessão Deliberativa",
                "dataHoraInicio": "2024-03-05T17:04", "orgaos": [{"sigla": "PLEN"}]}
_SESSAO_COMISSAO = {"id": 999, "descricaoTipo": "Sessão Deliberativa",
                    "dataHoraInicio": "2024-03-05T10:00", "orgaos": [{"sigla": "CCJC"}]}


class TestColetorSessoes(unittest.TestCase):
    def test_so_plenario_entra_comissao_fica_de_fora(self):
        cli = _ClienteFake([_SESSAO_PLEN, _SESSAO_COMISSAO], {})
        r = rodada_sessoes(cli, data_inicio="2024-03-01", data_fim="2024-03-31",
                           canario_validado=True, linha_base=None)
        self.assertEqual(len(r.prata.aprovados), 1)              # só a do PLEN
        self.assertEqual(r.prata.aprovados[0]["id_fonte"], "71957")
        self.assertEqual(r.prata.aprovados[0]["orgao_sigla"], "PLEN")

    def test_janela_vazia_e_ok_nao_falha(self):
        cli = _ClienteFake([], {})
        r = rodada_sessoes(cli, data_inicio="2024-01-01", data_fim="2024-01-10",
                           canario_validado=True, linha_base=None)
        self.assertEqual(r.estado.value, "ok")
        self.assertEqual(len(r.prata.aprovados), 0)

    def test_transform_mapeia_campos(self):
        s = transformar_sessao(_SESSAO_PLEN)
        self.assertEqual(s["id_fonte"], "71957")
        self.assertEqual(s["casa"], "camara")
        self.assertEqual(s["data_hora"], "2024-03-05T17:04")


class TestColetorPresencas(unittest.TestCase):
    def test_presentes_resolvem_e_sem_id_vai_para_quarentena(self):
        presentes = [{"id": 62881, "nome": "Ana"}, {"id": 111, "nome": "Beto"},
                     {"nome": "Sem Id"}]
        cli = _ClienteFake([_SESSAO_PLEN], {"71957": presentes})
        r = rodada_presencas(cli, "71957", canario_validado=True, linha_base=None)
        self.assertEqual(len(r.prata.aprovados), 2)     # os 2 com id
        self.assertEqual(len(r.prata.quarentena), 1)    # o sem id
        self.assertEqual(r.prata.aprovados[0]["id_camara"], "62881")

    def test_transform_presenca(self):
        p = transformar_presenca({"id": 62881}, "71957")
        self.assertEqual(p, {"sessao_id_fonte": "71957", "casa": "camara",
                             "id_camara": "62881", "presente": True})


# ----------------------------- persistência ---------------------------------

class _FakeBanco:
    def __init__(self):
        self.tabelas: dict[str, list[dict]] = {}
        self._seq = 0
    def _t(self, n): return self.tabelas.setdefault(n, [])
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
    def selecionar_um(self, tabela, onde):
        for r in self._t(tabela):
            if all(r.get(k) == v for k, v in onde.items()):
                return dict(r)
        return None


class TestPersistencia(unittest.TestCase):
    def test_salvar_sessoes_upsert_idempotente(self):
        banco = _FakeBanco()
        sess = [{"id_fonte": "71957", "casa": "camara", "tipo": "Sessão Deliberativa",
                 "data_hora": "2024-03-05T17:04", "orgao_sigla": "PLEN"}]
        self.assertEqual(salvar_sessoes(banco, sess), 1)
        self.assertEqual(salvar_sessoes(banco, sess), 1)          # idempotente
        self.assertEqual(len(banco.tabelas["sessao"]), 1)         # não duplica

    def test_salvar_presencas_resolve_perfil_e_pula_nao_resolvido(self):
        banco = _FakeBanco()
        salvar_sessoes(banco, [{"id_fonte": "71957", "casa": "camara",
                                "data_hora": "2024-03-05T17:04", "orgao_sigla": "PLEN"}])
        # lookup resolve só o deputado 62881
        lookup = lambda casa, idc: "P-ANA" if (casa, idc) == ("camara", "62881") else None
        aprovados = [{"id_camara": "62881", "presente": True},
                     {"id_camara": "999", "presente": True}]   # não resolve
        n = salvar_presencas(banco, "71957", aprovados, lookup)
        self.assertEqual(n, 1)                                    # só o resolvido
        self.assertEqual(len(banco.tabelas["presenca"]), 1)
        self.assertEqual(banco.tabelas["presenca"][0]["perfil_id"], "P-ANA")

    def test_salvar_presencas_sem_sessao_persistida_nao_salva(self):
        banco = _FakeBanco()   # sessão 71957 NÃO existe
        n = salvar_presencas(banco, "71957", [{"id_camara": "62881"}],
                             lambda c, i: "P-ANA")
        self.assertEqual(n, 0)


if __name__ == "__main__":
    unittest.main()
