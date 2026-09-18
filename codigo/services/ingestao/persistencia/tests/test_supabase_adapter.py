"""Testes do adaptador Supabase contra um duble stateful do cliente supabase-py.

Prova duas coisas sem o pacote `supabase` nem rede:
  1. O adaptador traduz `ClienteBanco` para a API fluente do supabase-py com os
     argumentos certos (on_conflict, ignore_duplicates).
  2. É um `ClienteBanco` drop-in: as funções reais do repositório rodam por ele.
"""

import unittest

from camara.deputados import transformar_deputado
from persistencia.repositorio import lookup_id_externo, salvar_bronze, salvar_deputados
from persistencia.supabase_adapter import (
    BancoSupabase, BRONZE_CONFLITO, _com_retry, _e_gateway_transitorio)
from pipeline.camadas import RegistroBronze


# -----------------------------------------------------------------------------
# Duble stateful do cliente supabase-py (API fluente .table().upsert()...execute())
# -----------------------------------------------------------------------------

class _Resp:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self, store, nome, chamadas):
        self._store = store.setdefault(nome, [])
        self._nome = nome
        self._chamadas = chamadas
        self._op = None
        self._rows = None
        self._conflito = None
        self._ignore = False
        self._match = {}
        self._limit = None

    def upsert(self, rows, on_conflict=None, ignore_duplicates=False):
        self._op, self._rows = "upsert", rows
        self._conflito, self._ignore = on_conflict, ignore_duplicates
        self._chamadas.append(("upsert", self._nome, on_conflict, ignore_duplicates))
        return self

    def select(self, cols):
        self._op = "select"
        return self

    def match(self, onde):
        self._match = onde
        return self

    def limit(self, n):
        self._limit = n
        return self

    def execute(self):
        if self._op == "upsert":
            cols = [c.strip() for c in (self._conflito or "").split(",") if c.strip()]
            out = []
            for r in self._rows:
                existe = next(
                    (x for x in self._store
                     if cols and all(x.get(c) == r.get(c) for c in cols)),
                    None,
                )
                if existe is not None:
                    if self._ignore:
                        continue  # duplicata ignorada — não volta na resposta
                    existe.update(r)
                    out.append(dict(existe))
                else:
                    linha = dict(r)
                    linha.setdefault("id", f"{self._nome}-{len(self._store) + 1}")
                    self._store.append(linha)
                    out.append(dict(linha))
            return _Resp(out)
        if self._op == "select":
            res = [x for x in self._store
                   if all(x.get(k) == v for k, v in self._match.items())]
            return _Resp(res[: self._limit] if self._limit else res)
        return _Resp([])


class FakeSupabaseClient:
    def __init__(self):
        self.store: dict[str, list[dict]] = {}
        self.chamadas: list[tuple] = []

    def table(self, nome):
        return _FakeTable(self.store, nome, self.chamadas)


def _dep(did=204379):
    return {"id": did, "nome": "Fulana", "siglaPartido": "PT", "siglaUf": "SP",
            "idLegislatura": 57, "urlFoto": "http://x", "uri": "u"}


# -----------------------------------------------------------------------------
# Semântica do adaptador
# -----------------------------------------------------------------------------

class TestBancoSupabase(unittest.TestCase):
    def test_upsert_insere_e_depois_atualiza_por_conflito(self):
        banco = BancoSupabase(FakeSupabaseClient())
        [row] = banco.upsert("t", [{"slug": "a", "nome": "X"}], conflito="slug")
        self.assertIn("id", row)
        [row2] = banco.upsert("t", [{"slug": "a", "nome": "Y"}], conflito="slug")
        self.assertEqual(row2["id"], row["id"])   # mesmo registro
        self.assertEqual(row2["nome"], "Y")       # atualizado

    def test_inserir_ignorando_conflito_conta_so_os_novos(self):
        cli = FakeSupabaseClient()
        banco = BancoSupabase(cli)
        reg = RegistroBronze.de("camara.deputados", "u", _dep())
        self.assertEqual(salvar_bronze(banco, [reg]), 1)
        self.assertEqual(salvar_bronze(banco, [reg]), 0)  # recoleta idêntica ignorada
        # e usou a chave de conflito do bronze, com ignore_duplicates
        up = [c for c in cli.chamadas if c[0] == "upsert" and c[1] == "bronze_registro"]
        self.assertTrue(all(c[2] == BRONZE_CONFLITO and c[3] is True for c in up))

    def test_selecionar_um_casa_ou_devolve_none(self):
        banco = BancoSupabase(FakeSupabaseClient())
        banco.upsert("t", [{"sistema": "camara", "identificador": "1",
                            "profile_id": "P"}], conflito="sistema,identificador")
        self.assertEqual(
            banco.selecionar_um("t", {"sistema": "camara", "identificador": "1"})["profile_id"],
            "P")
        self.assertIsNone(banco.selecionar_um("t", {"identificador": "999"}))


# -----------------------------------------------------------------------------
# Drop-in: o repositório real roda pelo adaptador
# -----------------------------------------------------------------------------

class TestDropInClienteBanco(unittest.TestCase):
    def test_salvar_deputados_e_lookup_pelo_adaptador(self):
        banco = BancoSupabase(FakeSupabaseClient())
        [pid] = salvar_deputados(banco, [transformar_deputado(_dep(204379))])
        lookup = lookup_id_externo(banco)
        self.assertEqual(lookup("camara", "204379"), pid)
        self.assertIsNone(lookup("camara", "000000"))


# -----------------------------------------------------------------------------
# Retry em erro TRANSITÓRIO de gateway (502/503/504 do proxy na frente do Supabase)
# -----------------------------------------------------------------------------

class _FakeAPIError(Exception):
    """Imita o postgrest.APIError: str(e) é o dict com 'code' e o corpo de erro."""


class TestRetryGatewayTransitorio(unittest.TestCase):
    _ERRO_502 = _FakeAPIError(
        "{'message': 'JSON could not be generated', 'code': 502, "
        "'details': \"b'<html>502 Bad Gateway</html>'\"}")

    def test_reconhece_502_como_transitorio_mas_nao_erro_de_dado(self):
        self.assertTrue(_e_gateway_transitorio(self._ERRO_502))
        self.assertFalse(_e_gateway_transitorio(
            _FakeAPIError("duplicate key value violates unique constraint")))

    def test_com_retry_repete_no_502_e_depois_conclui(self):
        estado = {"n": 0}
        def fn():
            estado["n"] += 1
            if estado["n"] < 3:
                raise self._ERRO_502
            return "ok"
        self.assertEqual(_com_retry(fn, tentativas=5, espera=0), "ok")
        self.assertEqual(estado["n"], 3)   # 2 falhas + 1 sucesso

    def test_com_retry_nao_repete_erro_de_dado(self):
        estado = {"n": 0}
        def fn():
            estado["n"] += 1
            raise _FakeAPIError("violates foreign key constraint")
        with self.assertRaises(_FakeAPIError):
            _com_retry(fn, tentativas=5, espera=0)
        self.assertEqual(estado["n"], 1)   # subiu na hora, sem repetir


if __name__ == "__main__":
    unittest.main(verbosity=2)
