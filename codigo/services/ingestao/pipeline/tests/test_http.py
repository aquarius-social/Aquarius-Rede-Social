"""Testes do cliente HTTP concreto (urllib) — sem rede, opener injetado."""

import io
import unittest
import urllib.error

from pipeline.coletor import ErroFalha, obter_com_retry
from pipeline.http import ClienteHttpUrllib


class _FakeCtx:
    def __init__(self, status, body):
        self.status = status
        self._body = body
    def read(self):
        return self._body.encode("utf-8")
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def _abrir_ok(body, status=200, capturado=None):
    def _a(req, timeout=None):
        if capturado is not None:
            capturado.append(req.full_url)
        return _FakeCtx(status, body)
    return _a


def _abrir_http_error(code, body="erro"):
    def _a(req, timeout=None):
        raise urllib.error.HTTPError(
            req.full_url, code, "erro", {}, io.BytesIO(body.encode("utf-8")))
    return _a


class TestClienteHttpUrllib(unittest.TestCase):
    def test_200_parseia_json(self):
        cli = ClienteHttpUrllib(abrir=_abrir_ok('{"dados": [1, 2]}'))
        r = cli.get("https://x/api")
        self.assertEqual(r.status, 200)
        self.assertEqual(r.corpo, {"dados": [1, 2]})

    def test_4xx_devolve_status_sem_levantar(self):
        cli = ClienteHttpUrllib(abrir=_abrir_http_error(404))
        r = cli.get("https://x/api")
        self.assertEqual(r.status, 404)
        self.assertIsNone(r.corpo)          # corpo não é parseado em erro
        self.assertIn("erro", r.texto())

    def test_params_viram_query_string(self):
        capturado: list[str] = []
        cli = ClienteHttpUrllib(abrir=_abrir_ok('{}', capturado=capturado))
        cli.get("https://x/api", params={"itens": 1, "ordem": "ASC"})
        self.assertEqual(capturado[0], "https://x/api?itens=1&ordem=ASC")

    # -- contrato com obter_com_retry (a classificação dos estados §19) --------

    def test_integra_com_obter_com_retry_no_caminho_feliz(self):
        cli = ClienteHttpUrllib(abrir=_abrir_ok('{"dados": []}'))
        corpo = obter_com_retry(cli, "https://x/api")
        self.assertEqual(corpo, {"dados": []})

    def test_4xx_vira_erro_falha_no_obter_com_retry(self):
        cli = ClienteHttpUrllib(abrir=_abrir_http_error(404))
        with self.assertRaises(ErroFalha):
            obter_com_retry(cli, "https://x/api")


if __name__ == "__main__":
    unittest.main(verbosity=2)
