"""Testes da junção bicameral (§17) — o mesmo indivíduo nas duas casas.

Cada regra da §5.3 tem um caso que ACEITA e um que RECUSA (disciplina da
Metodologia §5.2: "verificação que sempre passa é indistinguível de desligada").
O caso positivo é o Alan Rick do gold set: senador (5672) que foi deputado
(178836), casado por nome civil + nascimento + naturalidade.
"""

import unittest
from datetime import date

from resolucao.bicameral import Alvo, Candidato, Grau, resolver_bicameral

_HOJE = date(1900, 1, 1)  # a junção bicameral ignora a data (não há filtro temporal)


def _alan_cand(profile_id="P-DEP"):
    return Candidato(
        profile_id=profile_id,
        nome_parlamentar="Alan Rick",
        mandatos=(),
        nome_civil="Alan Rick Miranda",
        data_nascimento=date(1976, 10, 23),
        naturalidade_municipio="Rio Branco",
        naturalidade_uf="AC",
    )


def _alan_alvo(**over):
    base = dict(
        nome="Alan Rick", data_do_fato=_HOJE, nome_civil="Alan Rick Miranda",
        data_nascimento=date(1976, 10, 23),
        naturalidade_municipio="Rio Branco", naturalidade_uf="AC",
    )
    base.update(over)
    return Alvo(**base)


class TestBicameral(unittest.TestCase):
    def test_convergencia_de_tres_familias_e_direto(self):
        r = resolver_bicameral(_alan_alvo(), [_alan_cand()])
        self.assertIs(r.grau, Grau.DIRETO)
        self.assertEqual(r.profile_id, "P-DEP")
        self.assertGreaterEqual(len(r.sinais), 2)
        self.assertFalse(r.pendente_conferencia)

    def test_duas_familias_bastam_para_direto(self):
        """Nome civil + nascimento, sem naturalidade, ainda é 'direto'."""
        alvo = _alan_alvo(naturalidade_municipio=None, naturalidade_uf=None)
        r = resolver_bicameral(alvo, [_alan_cand()])
        self.assertIs(r.grau, Grau.DIRETO)

    def test_um_sinal_isolado_fica_com_ressalva_e_pendente(self):
        """Só o nome civil converge (nascimento/naturalidade ausentes no alvo):
        1 família → com_ressalva, pendente de conferência humana (§13)."""
        alvo = _alan_alvo(data_nascimento=None,
                          naturalidade_municipio=None, naturalidade_uf=None)
        r = resolver_bicameral(alvo, [_alan_cand()])
        self.assertIs(r.grau, Grau.COM_RESSALVA)
        self.assertEqual(r.profile_id, "P-DEP")
        self.assertTrue(r.pendente_conferencia)

    def test_nascimento_divergente_recusa(self):
        """Nome civil igual mas nascimento diferente = CONTRADIÇÃO → recusa,
        nunca aceite pela data isolada (§5.3, colisão de 9% no universo)."""
        alvo = _alan_alvo(data_nascimento=date(1980, 5, 1))
        r = resolver_bicameral(alvo, [_alan_cand()])
        self.assertIs(r.grau, Grau.RECUSADO)
        self.assertIsNone(r.profile_id)

    def test_dois_candidatos_convergentes_e_ambiguidade(self):
        r = resolver_bicameral(
            _alan_alvo(), [_alan_cand("P-A"), _alan_cand("P-B")])
        self.assertIs(r.grau, Grau.RECUSADO)
        self.assertIsNone(r.profile_id)
        self.assertTrue(r.pendente_conferencia)
        self.assertIn("ambiguidade", r.divergencia)

    def test_universo_vazio_recusa(self):
        r = resolver_bicameral(_alan_alvo(), [])
        self.assertIs(r.grau, Grau.RECUSADO)
        self.assertIsNone(r.profile_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
