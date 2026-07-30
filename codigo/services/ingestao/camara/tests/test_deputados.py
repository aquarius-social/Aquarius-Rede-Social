"""Testes do coletor de deputados da Câmara.

A novidade desta etapa é a disciplina da §12: dedup por identificador ANTES de
qualquer contagem (a lista repete o id por filiação), e a separação entre
identidade estável do perfil e os atributos temporais de mandato.
"""

import unittest
from typing import Any

from camara.deputados import (
    CAMPOS_CRITICOS_DEPUTADO,
    deduplicar_por_id,
    processar_deputados_para_prata,
    rodada_deputados,
    transformar_deputado,
)
from contrato.canario import EstadoContrato
from pipeline.camadas import RegistroBronze


class _Resp:
    def __init__(self, status: int, corpo: Any):
        self.status = status
        self.corpo = corpo
    def texto(self) -> str:
        return str(self.corpo)


class ClienteFake:
    def __init__(self, por_url: dict[str, list[Any]]):
        self.por_url = {k: list(v) for k, v in por_url.items()}
        self.chamadas: list[tuple[str, dict | None]] = []

    def get(self, url: str, params: dict | None = None) -> _Resp:
        self.chamadas.append((url, params))
        fila = self.por_url.get(url)
        if fila is None:
            raise AssertionError(f"sem resposta programada para {url}")
        if not fila:
            raise AssertionError(f"fila esgotada para {url}")
        return fila.pop(0)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

def _dep_fonte(did=204379, nome="Acácio Favacho", partido="MDB", uf="AP", leg=57):
    return {
        "id": did,
        "uri": f"https://dadosabertos.camara.leg.br/api/v2/deputados/{did}",
        "nome": nome,
        "siglaPartido": partido,
        "uriPartido": "https://dadosabertos.camara.leg.br/api/v2/partidos/1",
        "siglaUf": uf,
        "idLegislatura": leg,
        "urlFoto": f"https://www.camara.leg.br/internet/deputado/bandep/{did}.jpg",
        "email": "dep@camara.leg.br",
    }


def _dep_detalhe(did=204379, nome_civil="Acácio da Silva Favacho",
                 nasc="1980-05-10", municipio="Macapá", uf_nasc="AP"):
    """Resposta de GET /deputados/{id} — atributos de pessoa natural + o
    aninhado `ultimoStatus` (temporal, deve ser ignorado pela transformação)."""
    return {
        "id": did,
        "nomeCivil": nome_civil,
        "dataNascimento": nasc,
        "municipioNascimento": municipio,
        "ufNascimento": uf_nasc,
        "sexo": "M",
        "escolaridade": "Superior",
        "ultimoStatus": {"siglaPartido": "PSD", "siglaUf": "SP"},  # temporal!
    }


def _bronze(payload):
    return RegistroBronze.de("camara.deputados", "https://x", payload)


# =============================================================================
# Transformação — perfil + vínculo
# =============================================================================

class TestTransformacaoDeputado(unittest.TestCase):
    def test_shape_basico(self):
        p = transformar_deputado(_dep_fonte())
        self.assertEqual(p["id_fonte"], "204379")
        self.assertEqual(p["tipo"], "parlamentar")
        self.assertEqual(p["nome"], "Acácio Favacho")
        self.assertEqual(p["sistema_externo"], "camara")
        self.assertEqual(p["identificador_externo"], "204379")
        self.assertEqual(p["metodo_ligacao"], "fonte_direta")
        self.assertEqual(p["grau"], "direto")

    def test_slug_desambigua_por_id(self):
        """Homonímia (§6.2): dois 'João Silva' não podem colidir no slug."""
        a = transformar_deputado(_dep_fonte(did=1, nome="João Silva"))
        b = transformar_deputado(_dep_fonte(did=2, nome="João Silva"))
        self.assertEqual(a["slug"], "joao-silva-1")
        self.assertEqual(b["slug"], "joao-silva-2")
        self.assertNotEqual(a["slug"], b["slug"])

    def test_uf_e_partido_sao_temporais_nao_viram_atributo_do_perfil(self):
        """§12 (D3): UF de mandato e partido são pista temporal, não atributo
        atemporal do perfil. Ficam em mandato_hint, fora do topo."""
        p = transformar_deputado(_dep_fonte(uf="AP", partido="MDB", leg=57))
        self.assertNotIn("uf", p)
        self.assertNotIn("partido", p)
        self.assertEqual(p["mandato_hint"],
                         {"uf": "AP", "partido": "MDB", "id_legislatura": 57})

    def test_sem_detalhe_atributos_de_pessoa_ficam_none(self):
        """Passe só-lista: sem detalhe, a PII fica None (não erro)."""
        p = transformar_deputado(_dep_fonte())
        self.assertIsNone(p["nome_civil"])
        self.assertIsNone(p["data_nascimento"])
        self.assertIsNone(p["naturalidade_municipio"])
        self.assertIsNone(p["naturalidade_uf"])

    def test_detalhe_preenche_atributos_de_pessoa_natural(self):
        """§5.3/§3.5: o detalhe adiciona nome civil, nascimento e naturalidade."""
        p = transformar_deputado(_dep_fonte(), _dep_detalhe())
        self.assertEqual(p["nome_civil"], "Acácio da Silva Favacho")
        self.assertEqual(p["data_nascimento"], "1980-05-10")
        self.assertEqual(p["naturalidade_municipio"], "Macapá")
        self.assertEqual(p["naturalidade_uf"], "AP")

    def test_ultimo_status_do_detalhe_e_ignorado_por_ser_temporal(self):
        """O detalhe traz `ultimoStatus` (partido/UF correntes). É temporal e NÃO
        pode contaminar o perfil nem o mandato_hint (que vem da lista, da época
        daquela linha). D3."""
        item = _dep_fonte(partido="MDB", uf="AP")
        det = _dep_detalhe()  # ultimoStatus diz PSD/SP
        p = transformar_deputado(item, det)
        self.assertEqual(p["mandato_hint"]["partido"], "MDB")  # da lista, não PSD
        self.assertEqual(p["mandato_hint"]["uf"], "AP")        # da lista, não SP
        self.assertNotIn("ultimoStatus", p)


# =============================================================================
# Dedup por identificador — a disciplina central da §12
# =============================================================================

class TestDedupPorId(unittest.TestCase):
    def test_mesmo_id_em_duas_filiacoes_vira_uma_pessoa(self):
        """A lista repete o id por filiação. Dedup conta pessoas, não linhas."""
        bronze = [
            _bronze(_dep_fonte(did=204379, partido="MDB")),
            _bronze(_dep_fonte(did=204379, partido="PSD")),  # trocou de partido
        ]
        unicos = deduplicar_por_id(bronze)
        self.assertEqual(len(unicos), 1)
        self.assertEqual(unicos[0].payload["siglaPartido"], "MDB")  # 1ª ocorrência

    def test_ids_diferentes_sao_preservados(self):
        """Contraparte: pessoas distintas não são coladas."""
        bronze = [
            _bronze(_dep_fonte(did=1)),
            _bronze(_dep_fonte(did=2)),
        ]
        self.assertEqual(len(deduplicar_por_id(bronze)), 2)

    def test_prata_deduplica_antes_de_aprovar(self):
        bronze = [
            _bronze(_dep_fonte(did=204379, partido="MDB")),
            _bronze(_dep_fonte(did=204379, partido="PSD")),
            _bronze(_dep_fonte(did=220575, nome="Sonize Barbosa", partido="PL")),
        ]
        r = processar_deputados_para_prata(bronze)
        self.assertEqual(len(r.aprovados), 2)  # duas pessoas, não três linhas
        ids = {a["id_fonte"] for a in r.aprovados}
        self.assertEqual(ids, {"204379", "220575"})


# =============================================================================
# Portão
# =============================================================================

class TestPortaoDeputado(unittest.TestCase):
    def test_deputado_valido_passa(self):
        r = processar_deputados_para_prata([_bronze(_dep_fonte())])
        self.assertEqual(len(r.aprovados), 1)

    def test_sem_nome_vai_para_quarentena(self):
        p = _dep_fonte()
        del p["nome"]
        r = processar_deputados_para_prata([_bronze(p)])
        self.assertEqual(r.aprovados, [])
        _, v = r.quarentena[0]
        self.assertEqual(v.dimensao, "completude")

    def test_ligacao_direta_sem_fonte_direta_e_recusada(self):
        """Reject de _ligacao_coerente: grau 'direto' com método incoerente não
        pode ir à persistência (a constraint do banco recusaria)."""
        # transformar produz sempre fonte_direta; simulamos a incoerência
        # injetando um verificador sobre um registro já transformado.
        from camara.deputados import _ligacao_coerente
        reg = transformar_deputado(_dep_fonte())
        reg["metodo_ligacao"] = "convergencia"
        v = _ligacao_coerente(reg)
        self.assertIsNotNone(v)
        self.assertEqual(v.dimensao, "integridade_referencial")

    def test_ligacao_direta_por_fonte_direta_passa(self):
        from camara.deputados import _ligacao_coerente
        reg = transformar_deputado(_dep_fonte())
        self.assertIsNone(_ligacao_coerente(reg))


# =============================================================================
# Rodada completa com contrato
# =============================================================================

class TestRodadaDeputados(unittest.TestCase):
    def test_rodada_feliz_deduplica_e_aprova_pessoas(self):
        lista = _Resp(200, {
            "dados": [
                _dep_fonte(did=204379, partido="MDB"),
                _dep_fonte(did=204379, partido="PSD"),   # duplicata por filiação
                _dep_fonte(did=220575, nome="Sonize Barbosa", partido="PL"),
            ],
            "links": [],
        })
        cliente = ClienteFake({
            "https://dadosabertos.camara.leg.br/api/v2/deputados": [lista],
        })
        base = frozenset({
            "id", "uri", "nome", "siglaPartido", "uriPartido",
            "siglaUf", "idLegislatura", "urlFoto", "email",
        })
        r = rodada_deputados(
            cliente, canario_validado=True, linha_base=base, id_legislatura=57,
            enriquecer=False,
        )
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 2)

    def test_falha_na_lista_nao_processa_prata(self):
        cliente = ClienteFake({
            "https://dadosabertos.camara.leg.br/api/v2/deputados":
                [_Resp(404, "not found")],
        })
        r = rodada_deputados(
            cliente, canario_validado=True, linha_base=None,
        )
        self.assertIs(r.estado, EstadoContrato.FALHA)
        self.assertIsNone(r.prata)

    def test_rodada_com_enriquecimento_preenche_pii_do_detalhe(self):
        lista = _Resp(200, {"dados": [
            _dep_fonte(did=204379, partido="MDB"),
            _dep_fonte(did=204379, partido="PSD"),  # duplicata → 1 detalhe só
        ], "links": []})
        det = _Resp(200, {"dados": _dep_detalhe(did=204379)})
        cliente = ClienteFake({
            "https://dadosabertos.camara.leg.br/api/v2/deputados": [lista],
            "https://dadosabertos.camara.leg.br/api/v2/deputados/204379": [det],
        })
        r = rodada_deputados(cliente, canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 1)  # deduplicado
        perfil = r.prata.aprovados[0]
        self.assertEqual(perfil["nome_civil"], "Acácio da Silva Favacho")
        self.assertEqual(perfil["naturalidade_uf"], "AP")
        # o detalhe foi buscado UMA vez (id deduplicado), não duas
        chamadas_det = [u for u, _ in cliente.chamadas if u.endswith("/deputados/204379")]
        self.assertEqual(len(chamadas_det), 1)

    def test_rodada_tolera_falha_no_detalhe_de_uma_pessoa(self):
        """§12 (D2): o detalhe pode falhar. Quem falhou entra sem PII; os demais
        ficam completos. A rodada não cai."""
        lista = _Resp(200, {"dados": [
            _dep_fonte(did=1, nome="Com Detalhe"),
            _dep_fonte(did=2, nome="Sem Detalhe"),
        ], "links": []})
        cliente = ClienteFake({
            "https://dadosabertos.camara.leg.br/api/v2/deputados": [lista],
            "https://dadosabertos.camara.leg.br/api/v2/deputados/1":
                [_Resp(200, {"dados": _dep_detalhe(did=1, nome_civil="Fulano Civil")})],
            "https://dadosabertos.camara.leg.br/api/v2/deputados/2":
                [_Resp(404, "not found")],  # detalhe falha (sem retry/sleep)
        })
        r = rodada_deputados(cliente, canario_validado=True, linha_base=None)
        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.prata.aprovados), 2)
        por_id = {p["id_fonte"]: p for p in r.prata.aprovados}
        self.assertEqual(por_id["1"]["nome_civil"], "Fulano Civil")
        self.assertIsNone(por_id["2"]["nome_civil"])  # detalhe falhou, sem PII


if __name__ == "__main__":
    unittest.main(verbosity=2)
