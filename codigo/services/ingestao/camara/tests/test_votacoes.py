"""Testes do coletor de votações da Câmara.

Cobre a novidade desta etapa: resolução de identidade via id_externo, com
quarentena por integridade referencial quando o deputado não foi ingerido.
E a regra 6 do contrato — votação secreta não pode trazer nominal.
"""

import unittest
from typing import Any

from camara.votacoes import (
    CAMPOS_CRITICOS_VOTACAO,
    MAPA_VOTO,
    TAMANHO_CAMARA,
    LookupIdExterno,
    ResultadoVotos,
    VotoNominalResolvido,
    conferir_placar_contra_nominais,
    extrair_placar,
    processar_votacoes_para_prata,
    processar_votos_para_prata,
    rodada_votacoes,
    transformar_votacao,
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
    """Aceita fila por URL. Retorna 200 vazio se URL desconhecida em modo permissivo."""

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
        item = fila.pop(0)
        return item


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

def _votacao_fonte(vid="V1", secreta=False, com_proposicao=True,
                   descricao: str | None = None, afetadas=None):
    """Payload do DETALHE da votação (é o que a prata transforma).

    O vínculo à matéria vive em `proposicoesAfetadas` (Metodologia §10). O placar
    NÃO é campo da fonte — vive no texto da `descricao`, e o teste que precisa de
    placar passa uma descrição com placar (formato de plenário ou de comissão).
    """
    if descricao is None:
        descricao = "Votação secreta" if secreta else "Votação em turno único"
    if afetadas is None:
        afetadas = [
            {"id": "PL-1001", "uri": ".../PL-1001", "siglaTipo": "PL"}
        ] if com_proposicao else []
    return {
        "id": vid,
        "data": "2025-06-10",
        "dataHoraRegistro": "2025-06-10T14:32:00",
        "descricao": descricao,
        "aprovacao": 1 if not secreta else 0,
        "proposicoesAfetadas": afetadas,
    }


def _voto_fonte(dep_id=1001, tipo="Sim", partido="PT", uf="SP"):
    return {
        "tipoVoto": tipo,
        "deputado_": {
            "id": dep_id, "nome": "Fulana da Silva",
            "siglaPartido": partido, "siglaUf": uf,
        },
    }


def _bronze(fonte, payload):
    return RegistroBronze.de(fonte, "https://x", payload)


# =============================================================================
# Transformação da votação
# =============================================================================

class TestTransformacaoVotacao(unittest.TestCase):
    def test_shape_basico(self):
        p = transformar_votacao(_votacao_fonte())
        self.assertEqual(p["id_fonte"], "V1")
        self.assertEqual(p["casa"], "camara")
        self.assertEqual(p["resultado"], "aprovada")
        self.assertEqual(p["proposicao_id_fonte"], "PL-1001")
        self.assertIsNone(p["secreta"])  # não declarada explicitamente

    def test_declaracao_de_secreta_por_descricao(self):
        p = transformar_votacao(_votacao_fonte(secreta=True))
        self.assertTrue(p["secreta"])

    def test_sem_proposicao_vinculada(self):
        p = transformar_votacao(_votacao_fonte(com_proposicao=False))
        self.assertIsNone(p["proposicao_id_fonte"])

    def test_materia_vem_de_proposicoes_afetadas(self):
        """V1 (Metodologia §10): o vínculo à matéria vem de `proposicoesAfetadas`
        no detalhe, não de um campo da lista."""
        p = transformar_votacao(_votacao_fonte(
            afetadas=[{"id": "996958", "uri": ".../996958"}]
        ))
        self.assertEqual(p["proposicao_id_fonte"], "996958")

    def test_prefixo_do_id_corrobora_a_materia_certa(self):
        """V2 (Metodologia §10): o id da votação começa pelo id da proposição.
        Com várias afetadas, escolhe-se a que casa com o prefixo — não a
        primeira da lista."""
        p = transformar_votacao(_votacao_fonte(
            vid="996958-88",
            afetadas=[
                {"id": "111111", "uri": ".../111111"},   # procedimental, primeira
                {"id": "996958", "uri": ".../996958"},   # a matéria de fato
            ],
        ))
        self.assertEqual(p["proposicao_id_fonte"], "996958")

    def test_placar_none_quando_descricao_e_narrativa(self):
        """Descrição sem número não produz placar: fica None, nunca 0."""
        p = transformar_votacao(_votacao_fonte(
            descricao="Aprovado o Parecer do Relator, com voto contrário do Dep. X."
        ))
        self.assertIsNone(p["sim"])
        self.assertIsNone(p["nao"])
        self.assertIsNone(p["abstencao"])
        self.assertIsNone(p["total_declarado"])

    def test_placar_de_plenario_extraido_da_descricao(self):
        """V4 — formato de plenário (Metodologia §10)."""
        p = transformar_votacao(_votacao_fonte(
            descricao="Aprovado o Requerimento. Sim: 278; não: 88; "
                      "abstenção: 4; total: 370."
        ))
        self.assertEqual(p["sim"], 278)
        self.assertEqual(p["nao"], 88)
        self.assertEqual(p["abstencao"], 4)
        self.assertEqual(p["total_declarado"], 370)

    def test_deteccao_de_nominal_por_descricao(self):
        # Explicitamente nominal
        p = transformar_votacao(_votacao_fonte(descricao="Votação nominal - PLP 1/2024"))
        self.assertTrue(p["nominal"])

    def test_deteccao_de_simbolica_por_descricao(self):
        # Simbólica com "ó" acentuado — como a Câmara costuma publicar
        p = transformar_votacao(_votacao_fonte(descricao="Votação Simbólica"))
        self.assertFalse(p["nominal"])

    def test_deteccao_de_simbolica_sem_acento(self):
        # Defesa contra variação de fonte
        p = transformar_votacao(_votacao_fonte(descricao="Votacao Simbolica"))
        self.assertFalse(p["nominal"])

    def test_deteccao_de_por_acordo(self):
        p = transformar_votacao(_votacao_fonte(descricao="Aprovada por acordo"))
        self.assertFalse(p["nominal"])

    def test_nominal_none_quando_descricao_e_ambigua(self):
        """Heurística NÃO deve chutar. None significa 'leitura humana decide'."""
        p = transformar_votacao(_votacao_fonte(descricao="Votação em turno único"))
        self.assertIsNone(p["nominal"])


# =============================================================================
# Portão da votação
# =============================================================================

class TestPortaoVotacao(unittest.TestCase):
    def test_votacao_valida_passa(self):
        r = processar_votacoes_para_prata([_bronze("camara.votacoes", _votacao_fonte())])
        self.assertEqual(len(r.aprovados), 1)

    def test_data_ausente_vai_para_quarentena(self):
        p = _votacao_fonte()
        del p["data"]
        del p["dataHoraRegistro"]
        r = processar_votacoes_para_prata([_bronze("camara.votacoes", p)])
        self.assertEqual(r.aprovados, [])
        _, v = r.quarentena[0]
        self.assertEqual(v.dimensao, "completude")

    def test_placar_incoerente_vai_para_quarentena(self):
        """Identidade aritmética §5.2: as posições declaradas somam o total. Se
        o texto traz um total que não fecha com a soma, é erro de dado."""
        p = _votacao_fonte(descricao="Aprovado. Sim: 300; não: 88; total: 370.")
        r = processar_votacoes_para_prata([_bronze("camara.votacoes", p)])
        self.assertEqual(r.aprovados, [])
        _, v = r.quarentena[0]
        self.assertEqual(v.dimensao, "precisao")

    def test_placar_coerente_passa(self):
        """Contraparte: total que fecha com a soma passa o portão."""
        p = _votacao_fonte(descricao="Aprovado. Sim: 282; não: 88; total: 370.")
        r = processar_votacoes_para_prata([_bronze("camara.votacoes", p)])
        self.assertEqual(len(r.aprovados), 1)


# =============================================================================
# Resolução de identidade — o coração desta etapa
# =============================================================================

class TestResolucaoDeVoto(unittest.TestCase):
    def _lookup(self, mapa: dict[str, str]) -> LookupIdExterno:
        def _l(sistema: str, identificador: str) -> str | None:
            return mapa.get(f"{sistema}:{identificador}")
        return _l

    def test_voto_de_deputado_conhecido_e_resolvido_como_direto(self):
        lookup = self._lookup({"camara:1001": "PROFILE-1001"})
        bronze = [_bronze("camara.votos", _voto_fonte(dep_id=1001))]
        r = processar_votos_para_prata(bronze, "V1", lookup=lookup)
        self.assertEqual(len(r.resolvidos), 1)
        v = r.resolvidos[0]
        self.assertEqual(v.perfil_id, "PROFILE-1001")
        self.assertEqual(v.voto, "sim")
        self.assertEqual(v.modalidade_fonte, "Sim")
        self.assertEqual(v.grau_atribuicao, "direto")
        self.assertEqual(r.quarentena, [])

    def test_deputado_desconhecido_vai_para_quarentena_nao_e_criado_inline(self):
        """A disciplina da seção 6: identidade não se cria em ingestão de voto."""
        lookup = self._lookup({})  # nada cadastrado
        bronze = [_bronze("camara.votos", _voto_fonte(dep_id=9999))]
        r = processar_votos_para_prata(bronze, "V1", lookup=lookup)
        self.assertEqual(r.resolvidos, [])
        self.assertEqual(len(r.quarentena), 1)
        _, viol = r.quarentena[0]
        self.assertEqual(viol.dimensao, "integridade_referencial")
        self.assertIn("9999", viol.motivo)

    def test_voto_sem_deputado_id_vai_para_quarentena(self):
        lookup = self._lookup({"camara:1": "P1"})
        payload = _voto_fonte()
        del payload["deputado_"]["id"]
        r = processar_votos_para_prata([_bronze("camara.votos", payload)],
                                       "V1", lookup=lookup)
        _, viol = r.quarentena[0]
        self.assertEqual(viol.dimensao, "integridade_referencial")

    def test_modalidade_desconhecida_vai_para_quarentena_nao_e_adivinhada(self):
        lookup = self._lookup({"camara:1001": "P1"})
        bronze = [_bronze("camara.votos", _voto_fonte(tipo="Liberado"))]
        r = processar_votos_para_prata(bronze, "V1", lookup=lookup)
        self.assertEqual(r.resolvidos, [])
        _, viol = r.quarentena[0]
        self.assertEqual(viol.dimensao, "precisao")
        self.assertIn("Liberado", viol.motivo)

    def test_artigo_17_registra_presidencia_e_nao_e_posicao(self):
        """Metodologia §10: 'Artigo 17' marca quem PRESIDIU a votação. Nunca é
        posição nem ausência, e fica fora do placar. Vai a `presidencia`, não a
        `resolvidos`, e não é erro (não vai à quarentena)."""
        lookup = self._lookup({"camara:1001": "P1"})
        bronze = [_bronze("camara.votos", _voto_fonte(dep_id=1001, tipo="Artigo 17"))]
        r = processar_votos_para_prata(bronze, "V1", lookup=lookup)
        self.assertEqual(r.resolvidos, [])          # não é posição
        self.assertEqual(r.presidencia, ["P1"])     # registra quem presidiu
        self.assertEqual(r.quarentena, [])          # não é erro

    def test_voto_de_posicao_nao_entra_em_presidencia(self):
        """Contraparte: um voto normal ('Sim') é posição e NÃO vira presidência."""
        lookup = self._lookup({"camara:1001": "P1"})
        bronze = [_bronze("camara.votos", _voto_fonte(dep_id=1001, tipo="Sim"))]
        r = processar_votos_para_prata(bronze, "V1", lookup=lookup)
        self.assertEqual(r.presidencia, [])
        self.assertEqual(len(r.resolvidos), 1)
        self.assertEqual(r.resolvidos[0].voto, "sim")

    def test_artigo_17_de_deputado_desconhecido_ainda_precisa_de_perfil(self):
        """Presidência também exige identidade resolvida: sem perfil, quem
        presidiu não é registrável — vai à quarentena, não a `presidencia`."""
        lookup = self._lookup({})  # ninguém cadastrado
        bronze = [_bronze("camara.votos", _voto_fonte(dep_id=9999, tipo="Artigo 17"))]
        r = processar_votos_para_prata(bronze, "V1", lookup=lookup)
        self.assertEqual(r.presidencia, [])
        self.assertEqual(len(r.quarentena), 1)
        _, viol = r.quarentena[0]
        self.assertEqual(viol.dimensao, "integridade_referencial")

    def test_mapa_de_voto_cobre_variantes_com_e_sem_acento(self):
        """Sanidade: se a fonte mandar 'Nao' (sem acento) por bug, aceitamos."""
        self.assertEqual(MAPA_VOTO["Não"], "nao")
        self.assertEqual(MAPA_VOTO["Nao"], "nao")
        self.assertEqual(MAPA_VOTO["Abstenção"], "abstencao")


# =============================================================================
# Regra 6 do contrato de resposta — votação secreta não traz nominal
# =============================================================================

class TestVotacaoSecretaNaoTrazNominal(unittest.TestCase):
    def _lookup(self, mapa):
        def _l(s, i): return mapa.get(f"{s}:{i}")
        return _l

    def test_nominal_em_votacao_secreta_e_recusado_em_lote(self):
        """Não é caso a caso: se a fonte é incoerente, o lote inteiro vai fora.

        Salvar "só alguns nominais de uma votação secreta" produziria índice
        parcial que a regra 6 do contrato existe para impedir.
        """
        lookup = self._lookup({"camara:1": "P1", "camara:2": "P2"})
        bronze = [
            _bronze("camara.votos", _voto_fonte(dep_id=1)),
            _bronze("camara.votos", _voto_fonte(dep_id=2)),
        ]
        r = processar_votos_para_prata(
            bronze, "V1", lookup=lookup,
            votacao_declarada_secreta=True,
        )
        self.assertEqual(r.resolvidos, [])
        self.assertEqual(len(r.quarentena), 2)
        for _, v in r.quarentena:
            self.assertEqual(v.dimensao, "consistencia")
            self.assertIn("secreta", v.motivo.lower())


# =============================================================================
# Novo estado: votação não nominal (simbólica ou por acordo)
# Bug corrigido depois de comparar com o schema do Parlametria
# =============================================================================

class TestVotacaoSimbolicaSemNominal(unittest.TestCase):
    def _lookup(self, mapa):
        def _l(s, i): return mapa.get(f"{s}:{i}")
        return _l

    def test_simbolica_sem_nominal_e_o_caso_normal(self):
        """O caso NORMAL: descrição diz simbólica, resposta de votos vem
        vazia. Antes tratávamos como quarentena por integridade. Agora é OK."""
        r = processar_votos_para_prata(
            [], "V1", lookup=self._lookup({}),
            votacao_declarada_nominal=False,
        )
        self.assertEqual(r.resolvidos, [])
        self.assertEqual(r.quarentena, [])

    def test_simbolica_que_vem_com_nominal_e_incoerencia_da_fonte(self):
        """Se a fonte diz simbólica mas manda nominal, é incoerência dela.
        Vai à quarentena por consistência, com motivo explicativo."""
        lookup = self._lookup({"camara:1": "P1"})
        bronze = [_bronze("camara.votos", _voto_fonte(dep_id=1))]
        r = processar_votos_para_prata(
            bronze, "V1", lookup=lookup,
            votacao_declarada_nominal=False,
        )
        self.assertEqual(r.resolvidos, [])
        self.assertEqual(len(r.quarentena), 1)
        _, v = r.quarentena[0]
        self.assertEqual(v.dimensao, "consistencia")
        self.assertIn("não nominal", v.motivo)

    def test_nominal_none_permite_processar_normalmente(self):
        """Heurística indefinida (None) deve deixar passar — recusa só quando
        a fonte foi EXPLÍCITA sobre não ser nominal."""
        lookup = self._lookup({"camara:1": "P1"})
        bronze = [_bronze("camara.votos", _voto_fonte(dep_id=1))]
        r = processar_votos_para_prata(
            bronze, "V1", lookup=lookup,
            votacao_declarada_nominal=None,
        )
        self.assertEqual(len(r.resolvidos), 1)
        self.assertEqual(r.quarentena, [])

    def test_nominal_true_processa_normalmente(self):
        lookup = self._lookup({"camara:1": "P1"})
        bronze = [_bronze("camara.votos", _voto_fonte(dep_id=1))]
        r = processar_votos_para_prata(
            bronze, "V1", lookup=lookup,
            votacao_declarada_nominal=True,
        )
        self.assertEqual(len(r.resolvidos), 1)


# =============================================================================
# Rodada completa integrando o resolvedor via id_externo
# =============================================================================

class TestRodadaVotacoes(unittest.TestCase):
    def test_rodada_feliz_resolve_nominais_via_lookup(self):
        votacoes = _Resp(200, {
            "dados": [_votacao_fonte(vid="V1")],
            "links": [],
        })
        detalhe_v1 = _Resp(200, {"dados": _votacao_fonte(vid="V1")})
        votos_v1 = _Resp(200, {"dados": [
            _voto_fonte(dep_id=101, tipo="Sim"),
            _voto_fonte(dep_id=202, tipo="Não"),
            _voto_fonte(dep_id=999, tipo="Sim"),  # desconhecido
        ]})
        cliente = ClienteFake({
            "https://dadosabertos.camara.leg.br/api/v2/votacoes": [votacoes],
            # V1 agora exige o DETALHE (onde vive proposicoesAfetadas) antes dos votos
            "https://dadosabertos.camara.leg.br/api/v2/votacoes/V1": [detalhe_v1],
            "https://dadosabertos.camara.leg.br/api/v2/votacoes/V1/votos": [votos_v1],
        })
        lookup_mapa = {"camara:101": "P-101", "camara:202": "P-202"}
        def lookup(s, i): return lookup_mapa.get(f"{s}:{i}")

        # linha_base = payload realista da LISTA dessa fonte (o contrato roda
        # sobre a lista). Sem `proposicoes_`: a matéria vem do detalhe.
        base = frozenset({
            "id", "data", "dataHoraRegistro", "descricao",
            "aprovacao", "sim", "nao", "abstencao", "proposicoesAfetadas",
        })
        r = rodada_votacoes(
            cliente,
            data_inicio="2025-06-01", data_fim="2025-06-30",
            canario_validado=True, linha_base=base,
            lookup=lookup,
        )

        self.assertIs(r.estado, EstadoContrato.OK)
        self.assertEqual(len(r.votacoes_prata.aprovados), 1)
        self.assertIn("V1", r.nominais)
        nom = r.nominais["V1"]
        self.assertEqual(len(nom.resolvidos), 2)  # 999 ficou fora
        self.assertEqual(len(nom.quarentena), 1)

        # Bronze das outras requisições exposto para persistência (§3.1)
        self.assertEqual(len(r.detalhes_bronze), 1)              # 1 detalhe de votação
        self.assertIn("V1", r.votos_bronze)
        self.assertEqual(len(r.votos_bronze["V1"]), 3)           # 3 votos crus (incl. 999)

    def test_falha_na_lista_de_votacoes_nao_tenta_buscar_nominais(self):
        cliente = ClienteFake({
            "https://dadosabertos.camara.leg.br/api/v2/votacoes":
                [_Resp(404, "not found")],
        })
        r = rodada_votacoes(
            cliente,
            data_inicio="2025-06-01", data_fim="2025-06-30",
            canario_validado=True, linha_base=None,
            lookup=lambda s, i: None,
        )
        self.assertIs(r.estado, EstadoContrato.FALHA)
        self.assertEqual(r.nominais, {})


# =============================================================================
# V4 — extração do placar do texto da descrição (os dois formatos, §10)
# =============================================================================

class TestExtrairPlacar(unittest.TestCase):
    def test_formato_plenario(self):
        p = extrair_placar("Aprovado o Requerimento de Urgência (Art. 155 do "
                           "RICD). Sim: 278; não: 88; abstenção: 4; total: 370.")
        self.assertEqual(p["sim"], 278)
        self.assertEqual(p["nao"], 88)
        self.assertEqual(p["abstencao"], 4)
        self.assertEqual(p["total_declarado"], 370)

    def test_formato_plenario_sem_abstencao(self):
        p = extrair_placar("Aprovado o Substitutivo. Sim: 252; não: 163; "
                           "total: 415.")
        self.assertEqual(p["sim"], 252)
        self.assertEqual(p["nao"], 163)
        self.assertIsNone(p["abstencao"])
        self.assertEqual(p["total_declarado"], 415)

    def test_formato_comissao_com_rotulo_e_total_de_votantes(self):
        p = extrair_placar("Submetido à votação pelo processo nominal, o "
                           "requerimento foi APROVADO. Sim: 10; Não: 4; "
                           "Abstenção: 0; e Quórum de Votação: 10. Obstrução: 0; "
                           "e Total de Votantes: 14.")
        self.assertEqual(p["sim"], 10)
        self.assertEqual(p["nao"], 4)
        self.assertEqual(p["abstencao"], 0)
        self.assertEqual(p["obstrucao"], 0)
        self.assertEqual(p["total_declarado"], 14)

    def test_formato_comissao_n_votos_rotulo(self):
        p = extrair_placar('Aprovado o Parecer com o seguinte resultado: 34 '
                           'votos "Sim", 30 votos "Não". Quórum de votação: 64 '
                           'votos.')
        self.assertEqual(p["sim"], 34)
        self.assertEqual(p["nao"], 30)
        # "Quórum de votação" não é "total" — não se extrai como tal (conservador)
        self.assertIsNone(p["total_declarado"])

    def test_formato_comissao_resultado_de_tipo_unico(self):
        p = extrair_placar('Rejeitada a votação nominal do Requerimento de '
                           'Retirada de Pauta. Resultado: 13 votos "Não". '
                           'Quórum de votação: 13 votos.')
        self.assertIsNone(p["sim"])
        self.assertEqual(p["nao"], 13)

    def test_descricao_narrativa_sem_numero_nao_produz_placar(self):
        p = extrair_placar("Aprovado o Parecer do Relator, com voto contrário "
                           "do Deputado Alexandre Lindenmeyer.")
        self.assertIsNone(p)

    def test_descricao_vazia(self):
        self.assertIsNone(extrair_placar(None))
        self.assertIsNone(extrair_placar(""))


# =============================================================================
# V4 — reconciliação placar declarado × votos individuais (§5.2)
# =============================================================================

def _resolvido(voto: str) -> VotoNominalResolvido:
    return VotoNominalResolvido(
        votacao_id_fonte="V1", perfil_id="P", voto=voto,
        modalidade_fonte=voto, partido_sigla_na_epoca=None,
    )


class TestReconciliacaoPlacar(unittest.TestCase):
    def test_placar_que_bate_com_nominais_nao_gera_violacao(self):
        votos = ResultadoVotos(resolvidos=[
            _resolvido("sim"), _resolvido("sim"), _resolvido("nao"),
        ])
        prata = {"sim": 2, "nao": 1, "abstencao": None, "obstrucao": None}
        self.assertEqual(conferir_placar_contra_nominais(prata, votos), [])

    def test_placar_que_nao_bate_gera_violacao(self):
        votos = ResultadoVotos(resolvidos=[_resolvido("sim"), _resolvido("nao")])
        prata = {"sim": 3, "nao": 1, "abstencao": None, "obstrucao": None}
        viols = conferir_placar_contra_nominais(prata, votos)
        self.assertTrue(any(v.dimensao == "consistencia" for v in viols))
        self.assertTrue(any("sim" in v.motivo for v in viols))

    def test_votantes_acima_do_tamanho_da_casa_gera_violacao(self):
        votos = ResultadoVotos(
            resolvidos=[_resolvido("sim") for _ in range(TAMANHO_CAMARA + 1)]
        )
        prata = {"sim": None, "nao": None, "abstencao": None, "obstrucao": None}
        viols = conferir_placar_contra_nominais(prata, votos)
        self.assertTrue(any("excedem o tamanho da casa" in v.motivo for v in viols))

    def test_sem_nominais_nao_reconcilia(self):
        """Votação simbólica não tem votos individuais — nada a reconciliar."""
        prata = {"sim": 10, "nao": 5, "abstencao": None, "obstrucao": None}
        self.assertEqual(
            conferir_placar_contra_nominais(prata, ResultadoVotos()), []
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
