"""Testes da curadoria autor-de-emenda → perfil (§6.3, dois braços §17)."""

import unittest

from contrato.canario import EstadoContrato
from transparencia.autores import (
    abrir_mapa_padrao,
    rodada_autores,
    transformar_autor,
)

_CAB = ("codigo_autor;nome_na_fonte;deputado_id;nome_camara;sinais;n_sinais;"
        "classe;ufs_do_gasto;conferido_por_humano\n")


def _mapa(linhas):
    return _CAB + "".join(linhas)


class TestTransformacao(unittest.TestCase):
    def test_com_deputado_id_e_sinais(self):
        row = {"codigo_autor": "4291", "nome_na_fonte": "ADAIL FILHO",
               "deputado_id": "220714", "sinais": "nome,UF", "classe": "2 sinais"}
        a = transformar_autor(row)
        self.assertEqual(a["codigo_autor"], "4291")
        self.assertEqual(a["deputado_id"], "220714")
        self.assertEqual(a["sinais"], ["nome", "UF"])

    def test_sem_deputado_id(self):
        row = {"codigo_autor": "4273", "nome_na_fonte": "JORGE SEIF",
               "deputado_id": "", "sinais": "", "classe": "nao resolvido"}
        a = transformar_autor(row)
        self.assertIsNone(a["deputado_id"])
        self.assertEqual(a["sinais"], [])


class TestRodada(unittest.TestCase):
    def test_le_o_mapa(self):
        texto = _mapa([
            '4291;ADAIL FILHO;220714;Adail Filho;nome,UF;2;2 sinais;;\n',
            '7106;BANCADA DA BAHIA;;;;;coletivo (bancada/comissao);;\n',
        ])
        r = rodada_autores(lambda: texto, canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 2)

    def test_mapa_real_do_repo_carrega(self):
        """O mapa versionado no repo abre e tem os 628 autores (§2)."""
        r = rodada_autores(abrir_mapa_padrao, canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertGreater(len(r.prata.aprovados), 600)
        com_dep = [a for a in r.prata.aprovados if a["deputado_id"]]
        self.assertGreater(len(com_dep), 500)   # braço Câmara


if __name__ == "__main__":
    unittest.main(verbosity=2)
