"""Testes do mandato histórico do Senado → vinculo_temporal (§4/§17).

Campos conferidos contra a fonte viva (2026-08-01, senador 5672 = Alan Rick, que
trocou de UNIÃO para REPUBLICANOS no meio do mandato).
"""

import unittest

from contrato.canario import EstadoContrato
from senado.mandatos import (
    construir_vinculos_senado,
    rodada_mandatos_senado,
)

BASE = "https://legis.senado.leg.br/dadosabertos"


class _Resp:
    def __init__(self, status, corpo):
        self.status = status
        self.corpo = corpo
    def texto(self):
        return str(self.corpo)


class ClienteFake:
    def __init__(self, corpo):
        self._corpo = corpo
    def get(self, url, params=None):
        return _Resp(200, self._corpo)


def _mandato(uf="AC", part="Titular", leg="57", ini="2023-02-01", fim="2027-01-31",
            partidos=None, seg_fim=None):
    m = {"CodigoMandato": "596", "UfParlamentar": uf,
         "DescricaoParticipacao": part,
         "PrimeiraLegislaturaDoMandato": {"NumeroLegislatura": leg,
                                          "DataInicio": ini, "DataFim": fim}}
    if seg_fim:
        m["SegundaLegislaturaDoMandato"] = {"NumeroLegislatura": "58",
                                            "DataInicio": "2027-02-01", "DataFim": seg_fim}
    if partidos is not None:
        m["Partidos"] = {"Partido": partidos}
    return m


def _wrap(mandatos):
    return {"MandatoParlamentar": {"Parlamentar": {"Codigo": "5672",
            "Mandatos": {"Mandato": mandatos}}}}


class TestConstruirVinculos(unittest.TestCase):
    def test_troca_de_partido_rende_dois_vinculos_clipados(self):
        m = _mandato(seg_fim="2031-01-31", partidos=[
            {"Sigla": "REPUBLICANOS", "DataFiliacao": "2025-11-12"},
            {"Sigla": "UNIÃO", "DataFiliacao": "2022-02-24",
             "DataDesfiliacao": "2025-11-10"}])
        vs = construir_vinculos_senado([m], "5672")
        self.assertEqual(len(vs), 2)
        # ordenados por início; UNIÃO primeiro (filiação clipada ao início do mandato)
        self.assertEqual(vs[0]["partido_sigla_fonte"], "UNIÃO")
        self.assertEqual(vs[0]["vigencia_inicio"], "2023-02-01")   # clip: filiação 2022 → início mandato
        self.assertEqual(vs[0]["vigencia_fim"], "2025-11-10")
        self.assertEqual(vs[1]["partido_sigla_fonte"], "REPUBLICANOS")
        self.assertEqual(vs[1]["vigencia_inicio"], "2025-11-12")
        self.assertEqual(vs[1]["vigencia_fim"], "2031-01-31")      # clip: aberto → fim do mandato
        # não sobrepõem
        self.assertLessEqual(vs[0]["vigencia_fim"], vs[1]["vigencia_inicio"])
        self.assertEqual(vs[0]["casa"], "senado")
        self.assertEqual(vs[0]["uf"], "AC")

    def test_sem_partidos_rende_um_vinculo_do_mandato_inteiro(self):
        vs = construir_vinculos_senado([_mandato()], "5672")
        self.assertEqual(len(vs), 1)
        self.assertIsNone(vs[0]["partido_sigla_fonte"])
        self.assertEqual(vs[0]["vigencia_inicio"], "2023-02-01")
        self.assertEqual(vs[0]["vigencia_fim"], "2027-01-31")

    def test_filiacao_inteiramente_fora_da_janela_e_descartada(self):
        """Partido que o senador deixou ANTES deste mandato não vira vínculo."""
        m = _mandato(partidos=[
            {"Sigla": "PVELHO", "DataFiliacao": "2018-01-01", "DataDesfiliacao": "2020-01-01"},
            {"Sigla": "REPUBLICANOS", "DataFiliacao": "2023-02-01"}])
        vs = construir_vinculos_senado([m], "5672")
        self.assertEqual([v["partido_sigla_fonte"] for v in vs], ["REPUBLICANOS"])

    def test_suplente_e_pulado(self):
        """Suplente (roster) não rende vínculo por ora: exigiria titular_profile_id
        + vigência de exercício real (§6.4, constraint vinculo_suplente_coerente)."""
        vs = construir_vinculos_senado([_mandato(part="1º Suplente")], "5672")
        self.assertEqual(vs, [])


class TestRodada(unittest.TestCase):
    def test_rodada_feliz(self):
        cli = ClienteFake(_wrap([_mandato(seg_fim="2031-01-31", partidos=[
            {"Sigla": "REPUBLICANOS", "DataFiliacao": "2025-11-12"},
            {"Sigla": "UNIÃO", "DataFiliacao": "2022-02-24",
             "DataDesfiliacao": "2025-11-10"}])]))
        r = rodada_mandatos_senado(cli, "5672", canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.vinculos), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
