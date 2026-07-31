"""Testes do repositório de persistência.

Banco INJETADO por um fake em memória — sem rede, sem Supabase. Os shapes prata
vêm dos transforms REAIS dos coletores, então um desalinhamento entre o que o
coletor produz e o que o repositório mapeia quebra o teste (é o ponto).
"""

import unittest

from camara.deputados import transformar_deputado
from camara.proposicoes import transformar_proposicao
from camara.votacoes import VotoNominalResolvido, transformar_votacao
from camara.coletivos import transformar_comissao, transformar_frente
from camara.despesas import transformar_despesa
from camara.partidos import transformar_partido
from camara.tramitacoes import transformar_tramitacao
from persistencia.repositorio import (
    lookup_id_externo,
    lookup_partido_por_sigla,
    salvar_bronze,
    salvar_deputados,
    salvar_despesas,
    salvar_partidos,
    salvar_emendas,
    salvar_perfis_coletivos,
    salvar_proposicoes,
    salvar_tramitacoes,
    salvar_vinculos_temporais,
    salvar_votacoes,
    salvar_votos_nominais,
)
from pipeline.camadas import RegistroBronze


class FakeBanco:
    """Banco em memória: tabela = lista de dicts; id gerado na inserção."""

    _CHAVE_BRONZE = ("fonte", "id_na_fonte", "hash_conteudo")

    def __init__(self):
        self.tabelas: dict[str, list[dict]] = {}
        self._seq = 0

    def _t(self, nome: str) -> list[dict]:
        return self.tabelas.setdefault(nome, [])

    def upsert(self, tabela, linhas, *, conflito):
        cols = [c.strip() for c in conflito.split(",")]
        out = []
        for linha in linhas:
            existente = next(
                (r for r in self._t(tabela)
                 if all(r.get(c) == linha.get(c) for c in cols)), None)
            if existente is not None:
                existente.update(linha)
                out.append(dict(existente))
            else:
                self._seq += 1
                row = dict(linha)
                row.setdefault("id", f"{tabela}-{self._seq}")
                self._t(tabela).append(row)
                out.append(dict(row))
        return out

    def inserir_ignorando_conflito(self, tabela, linhas):
        n = 0
        for linha in linhas:
            if any(all(r.get(c) == linha.get(c) for c in self._CHAVE_BRONZE)
                   for r in self._t(tabela)):
                continue
            self._seq += 1
            row = dict(linha)
            row.setdefault("id", f"{tabela}-{self._seq}")
            self._t(tabela).append(row)
            n += 1
        return n

    def selecionar_um(self, tabela, onde):
        for r in self._t(tabela):
            if all(r.get(k) == v for k, v in onde.items()):
                return dict(r)
        return None


def _dep(did=204379, nome="Acácio Favacho", partido="MDB", uf="AP"):
    return {"id": did, "nome": nome, "siglaPartido": partido, "siglaUf": uf,
            "idLegislatura": 57,
            "urlFoto": f"https://x/{did}.jpg", "uri": f"https://x/{did}"}


# =============================================================================
# Bronze
# =============================================================================

class TestBronze(unittest.TestCase):
    def test_insere_e_ignora_recoleta_identica(self):
        banco = FakeBanco()
        reg = RegistroBronze.de("camara.deputados", "https://x", _dep())
        self.assertEqual(salvar_bronze(banco, [reg]), 1)
        # Recoleta com mesmo conteúdo (mesmo hash) é ignorada (evento imutável).
        self.assertEqual(salvar_bronze(banco, [reg]), 0)
        self.assertEqual(len(banco.tabelas["bronze_registro"]), 1)

    def test_id_composto_para_voto_que_nao_tem_id_proprio(self):
        """O voto não tem id de fonte — identidade é o par (votação, deputado).
        `id_na_fonte_de` compõe a chave para o bronze preservar isso (§3.1)."""
        banco = FakeBanco()
        voto = {"tipoVoto": "Sim", "deputado_": {"id": 101}}
        reg = RegistroBronze.de(
            "camara.votos",
            "https://dadosabertos.camara.leg.br/api/v2/votacoes/V1/votos", voto)
        salvar_bronze(banco, [reg],
                      id_na_fonte_de=lambda r: f"V1:{r.payload['deputado_']['id']}")
        self.assertEqual(
            banco.tabelas["bronze_registro"][0]["id_na_fonte"], "V1:101")


# =============================================================================
# Deputados → profiles + id_externo + o lookup real
# =============================================================================

class TestDeputados(unittest.TestCase):
    def test_cria_perfil_e_id_externo_e_o_lookup_resolve(self):
        banco = FakeBanco()
        prata = [transformar_deputado(_dep(did=204379))]
        [pid] = salvar_deputados(banco, prata)

        # profile e id_externo criados
        self.assertEqual(len(banco.tabelas["profiles"]), 1)
        ext = banco.tabelas["id_externo"][0]
        self.assertEqual(ext["sistema"], "camara")
        self.assertEqual(ext["identificador"], "204379")
        self.assertEqual(ext["profile_id"], pid)
        self.assertEqual(ext["metodo"], "fonte_direta")
        self.assertEqual(ext["grau"], "direto")

        # o lookup real fecha o ciclo: camara id -> profile_id
        lookup = lookup_id_externo(banco)
        self.assertEqual(lookup("camara", "204379"), pid)
        self.assertIsNone(lookup("camara", "999999"))

    def test_perfil_so_carrega_colunas_do_schema_nao_o_mandato_hint(self):
        banco = FakeBanco()
        salvar_deputados(banco, [transformar_deputado(_dep())])
        perfil = banco.tabelas["profiles"][0]
        self.assertNotIn("mandato_hint", perfil)       # temporal, não é do perfil
        self.assertNotIn("sistema_externo", perfil)    # vai em id_externo
        self.assertEqual(perfil["tipo"], "parlamentar")
        self.assertEqual(perfil["source"], "camara.deputados")

    def test_upsert_e_idempotente_por_slug(self):
        banco = FakeBanco()
        prata = [transformar_deputado(_dep(did=204379))]
        salvar_deputados(banco, prata)
        salvar_deputados(banco, prata)  # de novo
        self.assertEqual(len(banco.tabelas["profiles"]), 1)
        self.assertEqual(len(banco.tabelas["id_externo"]), 1)


# =============================================================================
# Proposições
# =============================================================================

class TestProposicoes(unittest.TestCase):
    def _prop_fonte(self, pid="123", tipo="PL"):
        return {"id": pid, "siglaTipo": tipo, "numero": 736, "ano": 2015,
                "ementa": "Dispõe sobre algo.",
                "dataApresentacao": "2015-03-12T18:32"}

    def test_data_apresentacao_e_truncada_para_date(self):
        banco = FakeBanco()
        prata = [transformar_proposicao(self._prop_fonte())]
        salvar_proposicoes(banco, prata)
        row = banco.tabelas["proposicao"][0]
        self.assertEqual(row["data_apresentacao"], "2015-03-12")  # sem a hora
        self.assertEqual(row["casa_origem"], "camara")
        self.assertEqual(row["id_na_fonte"], "123")


# =============================================================================
# Vínculos temporais — resolve profile_id, monta daterange
# =============================================================================

class TestPartidos(unittest.TestCase):
    def _partido(self, pid=36898, sigla="AVANTE", nome="Avante"):
        return transformar_partido({"id": pid, "sigla": sigla, "nome": nome})

    def test_cria_profile_partido_e_linha_partido(self):
        banco = FakeBanco()
        salvar_partidos(banco, [self._partido()])
        self.assertEqual(banco.tabelas["profiles"][0]["tipo"], "partido")
        self.assertEqual(banco.tabelas["partido"][0]["sigla_atual"], "AVANTE")

    def test_lookup_por_sigla_devolve_id_do_partido(self):
        banco = FakeBanco()
        salvar_partidos(banco, [self._partido(sigla="PT", nome="Partido dos Trabalhadores")])
        partido_id = banco.tabelas["partido"][0]["id"]
        lookup = lookup_partido_por_sigla(banco)
        self.assertEqual(lookup("PT"), partido_id)
        self.assertIsNone(lookup("S.PART."))   # sigla desconhecida → None
        self.assertIsNone(lookup(None))


class TestDespesas(unittest.TestCase):
    def _desp(self, did="204379"):
        return transformar_despesa({
            "ano": 2025, "mes": 12, "tipoDespesa": "DIVULGAÇÃO",
            "codDocumento": 123, "parcela": 0, "dataDocumento": "2025-12-15",
            "valorDocumento": 2000.0, "valorGlosa": 0.0, "valorLiquido": 2000.0,
            "nomeFornecedor": "F", "cnpjCpfFornecedor": "00000000000191"}, did)

    def test_prende_ao_perfil_do_parlamentar(self):
        banco = FakeBanco()
        [pid] = salvar_deputados(banco, [transformar_deputado(_dep(204379))])
        lookup = lookup_id_externo(banco)
        n = salvar_despesas(banco, [self._desp("204379")], lookup)
        self.assertEqual(n, 1)
        self.assertEqual(banco.tabelas["despesa"][0]["perfil_id"], pid)
        self.assertEqual(banco.tabelas["despesa"][0]["valor_liquido"], 2000.0)

    def test_sem_perfil_nao_inventa(self):
        banco = FakeBanco()
        lookup = lookup_id_externo(banco)
        self.assertEqual(salvar_despesas(banco, [self._desp("000")], lookup), 0)


class TestEmendas(unittest.TestCase):
    def _emenda(self):
        from transparencia.emendas import transformar_emenda
        return transformar_emenda({
            "codigoEmenda": "202440340007", "ano": 2024,
            "tipoEmenda": "Individual", "autor": "LUISA CANZIANI",
            "numeroEmenda": "0007", "funcao": "Saúde",
            "valorEmpenhado": "10.000,00", "valorLiquidado": "10.000,00",
            "valorPago": "10.000,00"})

    def test_persiste_com_valores_e_autor_null_sem_mapa(self):
        banco = FakeBanco()
        n = salvar_emendas(banco, [self._emenda()])
        self.assertEqual(n, 1)
        row = banco.tabelas["emenda"][0]
        self.assertEqual(row["codigo_emenda"], "202440340007")
        self.assertEqual(row["valor_empenhado"], 10000.0)
        self.assertEqual(row["autor_codigo"], "4034")
        self.assertIsNone(row["autor_profile_id"])  # sem mapa carregado

    def test_resolve_autor_quando_mapa_existe(self):
        """§6.3: com id_externo 'autor_orcamentario' carregado, o autor resolve."""
        banco = FakeBanco()
        lookup = lambda s, i: "P-CANZIANI" if (s, i) == ("autor_orcamentario", "4034") else None
        salvar_emendas(banco, [self._emenda()], lookup)
        self.assertEqual(banco.tabelas["emenda"][0]["autor_profile_id"], "P-CANZIANI")


class TestPerfisColetivos(unittest.TestCase):
    def test_comissao_e_frente_viram_profiles_por_tipo(self):
        banco = FakeBanco()
        n1 = salvar_perfis_coletivos(
            banco, [transformar_comissao({"id": 2003, "sigla": "CCJC", "nome": "CCJC"})],
            source="camara.orgaos")
        n2 = salvar_perfis_coletivos(
            banco, [transformar_frente({"id": 55703, "titulo": "Frente X"})],
            source="camara.frentes")
        self.assertEqual((n1, n2), (1, 1))
        tipos = {p["tipo"] for p in banco.tabelas["profiles"]}
        self.assertEqual(tipos, {"comissao", "frente"})
        # comissão carrega sigla; frente não
        com = next(p for p in banco.tabelas["profiles"] if p["tipo"] == "comissao")
        self.assertEqual(com["sigla"], "CCJC")


class TestVinculosTemporais(unittest.TestCase):
    def _vinc(self, id_fonte="204379", fim="2015-09-24", sigla="MDB",
              inicio="2015-02-01"):
        return {"id_fonte": id_fonte, "casa": "camara", "legislatura": 55,
                "uf": "AP", "partido_id": None, "partido_sigla_fonte": sigla,
                "ocupacao": "titular", "vigencia_inicio": inicio,
                "vigencia_fim": fim}

    def test_prende_ao_perfil_e_monta_daterange(self):
        banco = FakeBanco()
        salvar_deputados(banco, [transformar_deputado(_dep())])
        lookup = lookup_id_externo(banco)
        n = salvar_vinculos_temporais(banco, [self._vinc()], lookup)
        self.assertEqual(n, 1)
        row = banco.tabelas["vinculo_temporal"][0]
        self.assertEqual(row["vigencia"], "[2015-02-01,2015-09-24)")
        self.assertEqual(row["partido_sigla_fonte"], "MDB")
        self.assertIsNone(row["partido_id"])  # canônico resolvido depois

    def test_vigencia_aberta_quando_sem_fim(self):
        banco = FakeBanco()
        salvar_deputados(banco, [transformar_deputado(_dep())])
        lookup = lookup_id_externo(banco)
        salvar_vinculos_temporais(banco, [self._vinc(fim=None)], lookup)
        self.assertEqual(banco.tabelas["vinculo_temporal"][0]["vigencia"],
                         "[2015-02-01,)")

    def test_sem_perfil_persistido_nao_inventa(self):
        banco = FakeBanco()
        lookup = lookup_id_externo(banco)  # nada cadastrado
        self.assertEqual(
            salvar_vinculos_temporais(banco, [self._vinc("000000")], lookup), 0)

    def test_resolve_partido_id_por_sigla_quando_conhecida(self):
        """Sigla atual conhecida → partido_id resolvido; sigla histórica → None,
        com a sigla-fonte preservada (curadoria resolve depois, §4)."""
        banco = FakeBanco()
        salvar_deputados(banco, [transformar_deputado(_dep())])
        salvar_partidos(banco, [transformar_partido(
            {"id": 1, "sigla": "MDB", "nome": "Movimento Democrático Brasileiro"})])
        partido_id = banco.tabelas["partido"][0]["id"]
        lookup = lookup_id_externo(banco)
        lookup_part = lookup_partido_por_sigla(banco)

        # vínculo com sigla MDB (conhecida) e outro com PMDB (histórica)
        salvar_vinculos_temporais(
            banco,
            [self._vinc(sigla="MDB", inicio="2015-02-01", fim="2015-09-24"),
             self._vinc(sigla="PMDB", inicio="2015-09-24", fim=None)],
            lookup, lookup_partido=lookup_part)
        por_sigla = {v["partido_sigla_fonte"]: v
                     for v in banco.tabelas["vinculo_temporal"]}
        self.assertEqual(por_sigla["MDB"]["partido_id"], partido_id)
        self.assertIsNone(por_sigla["PMDB"]["partido_id"])  # histórica → curadoria


# =============================================================================
# Tramitações — resolução da FK de proposição
# =============================================================================

class TestTramitacoes(unittest.TestCase):
    def _prop(self, banco, pid="996958"):
        salvar_proposicoes(banco, [transformar_proposicao({
            "id": pid, "siglaTipo": "PL", "numero": 736, "ano": 2015,
            "ementa": "x", "dataApresentacao": "2015-03-12T18:32"})])
        return banco.tabelas["proposicao"][0]["id"]

    def _tram(self, pid="996958"):
        return transformar_tramitacao(
            {"sequencia": 1, "dataHora": "2015-03-12T18:32",
             "siglaOrgao": "PLEN", "descricaoTramitacao": "Apresentação",
             "despacho": None},
            pid)

    def test_prende_tramitacao_a_proposicao_persistida(self):
        banco = FakeBanco()
        prop_uuid = self._prop(banco)
        n = salvar_tramitacoes(banco, [self._tram()])
        self.assertEqual(n, 1)
        self.assertEqual(banco.tabelas["tramitacao"][0]["proposicao_id"], prop_uuid)

    def test_sem_proposicao_persistida_nao_inventa(self):
        banco = FakeBanco()
        n = salvar_tramitacoes(banco, [self._tram(pid="000000")])
        self.assertEqual(n, 0)
        self.assertNotIn("tramitacao", banco.tabelas)


# =============================================================================
# Votações — resolução da FK de proposição e placar None
# =============================================================================

class TestVotacoes(unittest.TestCase):
    def _votacao(self, vid="996958-88", desc="Aprovado. Sim: 2; não: 1; total: 3.",
                 afetada="996958"):
        return transformar_votacao({
            "id": vid, "data": "2023-06-01",
            "dataHoraRegistro": "2023-06-01T12:00:00",
            "descricao": desc, "aprovacao": 1,
            "proposicoesAfetadas": [{"id": afetada, "uri": f"x/{afetada}"}],
        })

    def test_resolve_proposicao_id_quando_proposicao_existe(self):
        banco = FakeBanco()
        # proposição 996958 já persistida
        salvar_proposicoes(banco, [transformar_proposicao({
            "id": "996958", "siglaTipo": "PL", "numero": 736, "ano": 2015,
            "ementa": "x", "dataApresentacao": "2015-03-12T18:32"})])
        prop_uuid = banco.tabelas["proposicao"][0]["id"]

        salvar_votacoes(banco, [self._votacao()])
        vot = banco.tabelas["votacao"][0]
        self.assertEqual(vot["proposicao_id"], prop_uuid)

    def test_proposicao_id_none_quando_nao_ingerida(self):
        banco = FakeBanco()
        salvar_votacoes(banco, [self._votacao(afetada="000000")])
        self.assertIsNone(banco.tabelas["votacao"][0]["proposicao_id"])

    def test_placar_nao_extraido_vira_none_nunca_zero(self):
        banco = FakeBanco()
        # descrição narrativa: sem placar
        salvar_votacoes(banco, [self._votacao(desc="Aprovado o Parecer.")])
        vot = banco.tabelas["votacao"][0]
        self.assertIsNone(vot["sim"])
        self.assertIsNone(vot["nao"])
        self.assertIsNone(vot["abstencao"])


# =============================================================================
# Votos nominais — resolução da FK de votação; perfil já resolvido
# =============================================================================

class TestVotosNominais(unittest.TestCase):
    def _resolvido(self, perfil_id, voto="sim"):
        return VotoNominalResolvido(
            votacao_id_fonte="996958-88", perfil_id=perfil_id, voto=voto,
            modalidade_fonte=voto, partido_sigla_na_epoca="PT")

    def test_persiste_votos_quando_votacao_existe(self):
        banco = FakeBanco()
        # votação precisa existir para prender o voto
        salvar_votacoes(banco, [transformar_votacao({
            "id": "996958-88", "data": "2023-06-01",
            "dataHoraRegistro": "2023-06-01T12:00:00",
            "descricao": "Aprovado.", "aprovacao": 1,
            "proposicoesAfetadas": []})])
        n = salvar_votos_nominais(
            banco, "996958-88",
            [self._resolvido("P-1"), self._resolvido("P-2", "nao")])
        self.assertEqual(n, 2)
        vid = banco.tabelas["votacao"][0]["id"]
        for v in banco.tabelas["voto_nominal"]:
            self.assertEqual(v["votacao_id"], vid)

    def test_sem_votacao_persistida_nao_inventa(self):
        banco = FakeBanco()
        n = salvar_votos_nominais(banco, "inexistente", [self._resolvido("P-1")])
        self.assertEqual(n, 0)
        self.assertNotIn("voto_nominal", banco.tabelas)

    def test_lista_vazia_e_zero(self):
        banco = FakeBanco()
        self.assertEqual(salvar_votos_nominais(banco, "996958-88", []), 0)


# =============================================================================
# Fluxo ponta a ponta: deputado → lookup → voto nominal resolvido
# =============================================================================

class TestFluxoIntegrado(unittest.TestCase):
    def test_deputado_persistido_torna_o_voto_resolvivel(self):
        banco = FakeBanco()
        # 1. persiste o deputado → cria id_externo
        [pid] = salvar_deputados(banco, [transformar_deputado(_dep(did=101))])
        # 2. o lookup real resolve o id da Câmara para o perfil
        lookup = lookup_id_externo(banco)
        perfil = lookup("camara", "101")
        self.assertEqual(perfil, pid)
        # 3. persiste a votação e o voto nominal com o perfil resolvido
        salvar_votacoes(banco, [transformar_votacao({
            "id": "V-1", "data": "2023-06-01",
            "dataHoraRegistro": "2023-06-01T12:00:00",
            "descricao": "Aprovado.", "aprovacao": 1,
            "proposicoesAfetadas": []})])
        n = salvar_votos_nominais(banco, "V-1", [VotoNominalResolvido(
            votacao_id_fonte="V-1", perfil_id=perfil, voto="sim",
            modalidade_fonte="Sim", partido_sigla_na_epoca="MDB")])
        self.assertEqual(n, 1)
        self.assertEqual(banco.tabelas["voto_nominal"][0]["perfil_id"], pid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
