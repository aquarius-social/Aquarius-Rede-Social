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
    salvar_autores_orcamentarios,
    salvar_deputados,
    salvar_despesas,
    salvar_despesas_senado,
    salvar_partidos,
    salvar_discursos,
    salvar_emendas,
    salvar_eventos,
    salvar_perfis_coletivos,
    salvar_proposicoes,
    salvar_senadores,
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


class TestEventos(unittest.TestCase):
    def _ev(self, casa="senado", idf="14883", slug="comissao-sf-cdh-834"):
        return {"casa": casa, "id_fonte": idf, "tipo": "Reunião", "titulo": "56ª",
                "data_hora_inicio": "2026-08-06T10:00:00", "data_hora_fim": None,
                "situacao": "Agendada", "orgao_sigla": "CDH", "orgao_nome": "CDH",
                "orgao_slug": slug, "local": "Anexo II", "url": None}

    def test_resolve_orgao_por_slug(self):
        banco = FakeBanco()
        # cria o perfil da comissão com o mesmo slug
        banco.upsert("profiles", [{"tipo": "comissao", "nome": "CDH",
                                    "slug": "comissao-sf-cdh-834"}], conflito="slug")
        n = salvar_eventos(banco, [self._ev()], source="senado.eventos",
                           source_url="http://sen")
        self.assertEqual(n, 1)
        row = banco.tabelas["evento"][0]
        self.assertEqual(row["casa"], "senado")
        self.assertEqual(row["orgao_profile_id"], banco.tabelas["profiles"][0]["id"])

    def test_orgao_sem_perfil_fica_null(self):
        """Plenário e órgãos não-ingeridos → orgao_profile_id null (não inventa)."""
        banco = FakeBanco()
        salvar_eventos(banco, [self._ev(slug="comissao-plen-180")],
                       source="camara.eventos", source_url="http://cam")
        self.assertIsNone(banco.tabelas["evento"][0]["orgao_profile_id"])


class TestAutoresOrcamentarios(unittest.TestCase):
    def _autor(self, cod="4291", dep="220714", nome="ADAIL FILHO", sinais=("nome", "UF")):
        return {"codigo_autor": cod, "deputado_id": dep, "nome_na_fonte": nome,
                "sinais": list(sinais), "classe": "2 sinais"}

    def test_braco_camara_resolve_por_deputado_id(self):
        banco = FakeBanco()
        lookup = lambda s, i: "P-DEP" if (s, i) == ("camara", "220714") else None
        c = salvar_autores_orcamentarios(banco, [self._autor()], lookup)
        self.assertEqual(c["camara"], 1)
        ext = banco.tabelas["id_externo"][0]
        self.assertEqual(ext["sistema"], "autor_orcamentario")
        self.assertEqual(ext["identificador"], "4291")
        self.assertEqual(ext["profile_id"], "P-DEP")
        self.assertEqual(ext["grau"], "direto")            # 2 sinais

    def test_braco_senado_resolve_por_nome(self):
        """Autor que o mapa não achou na Câmara mas é senador → braço Senado."""
        banco = FakeBanco()
        autor = self._autor(cod="4273", dep="", nome="JORGE SEIF", sinais=())
        lookup = lambda s, i: None
        lookup_sen = lambda nome: "P-SEN" if nome == "JORGE SEIF" else None
        c = salvar_autores_orcamentarios(banco, [autor], lookup, lookup_sen)
        self.assertEqual(c["senado"], 1)
        self.assertEqual(c["pendentes"], 1)                # 1 sinal (nome) → ressalva
        ext = banco.tabelas["id_externo"][0]
        self.assertEqual(ext["profile_id"], "P-SEN")
        self.assertEqual(ext["grau"], "com_ressalva")
        self.assertTrue(ext["pendente_conferencia"])

    def test_bancada_sem_perfil_e_pulada(self):
        banco = FakeBanco()
        bancada = {"codigo_autor": "7106", "deputado_id": None,
                   "nome_na_fonte": "BANCADA DA BAHIA", "sinais": [], "classe": "coletivo"}
        c = salvar_autores_orcamentarios(banco, [bancada], lambda s, i: None,
                                         lambda nome: None)
        self.assertEqual(c, {"camara": 0, "senado": 0, "pendentes": 0})
        self.assertNotIn("id_externo", banco.tabelas)


class TestDespesasSenado(unittest.TestCase):
    def _ceaps(self, nome="ALAN RICK", cod=2221244):
        return {"senador_nome": nome, "ano": 2024, "mes": 1,
                "tipo_despesa": "Aluguel", "tipo_documento": None,
                "cod_documento": cod, "num_documento": "470160", "parcela": 0,
                "data_documento": "2024-01-17", "valor_documento": 583.58,
                "valor_glosa": None, "valor_liquido": 583.58,
                "fornecedor_nome": "CLARO", "fornecedor_cnpj_cpf": "66.970.229/0132-26",
                "url_documento": None}

    def test_resolve_por_nome_e_persiste(self):
        banco = FakeBanco()
        lookup_senador = lambda n: "P-AR" if n == "ALAN RICK" else None
        n = salvar_despesas_senado(banco, [self._ceaps()], lookup_senador)
        self.assertEqual(n, 1)
        row = banco.tabelas["despesa"][0]
        self.assertEqual(row["perfil_id"], "P-AR")
        self.assertEqual(row["valor_liquido"], 583.58)
        self.assertIsNone(row["valor_glosa"])
        self.assertEqual(row["parcela"], 0)

    def test_nome_nao_resolvido_e_pulado(self):
        """Ex-senador/suplente que não casa com a lista viva → pulado (§6)."""
        banco = FakeBanco()
        n = salvar_despesas_senado(banco, [self._ceaps("FULANO DESCONHECIDO")],
                                   lambda n: None)
        self.assertEqual(n, 0)
        self.assertNotIn("despesa", banco.tabelas)


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

    def test_fallback_por_nome_resolve_individual_recusa_o_resto(self):
        """§6.3 fallback: autor fora do mapa curado casa por NOME → id_externo
        com_ressalva + pendente, e alimenta salvar_emendas. Recusa (fica null):
        coletivo (bancada), ambíguo (homônimo → lookup None), e já-resolvido pelo
        mapa (grau 'direto' NÃO é rebaixado)."""
        from persistencia.repositorio import (
            resolver_autores_emenda_por_nome, lookup_id_externo)
        banco = FakeBanco()
        # já resolvido pelo mapa curado (2 sinais) — não pode ser rebaixado
        banco.tabelas.setdefault("id_externo", []).append({
            "sistema": "autor_orcamentario", "identificador": "4034",
            "profile_id": "P-CANZIANI", "grau": "direto"})
        lookup = lookup_id_externo(banco)
        lookup_nome = lambda nome: "P-ZUCCO" if (nome or "").strip().upper() == "ZUCCO" else None
        emendas = [
            {"codigo_emenda": "E1", "ano": 2024, "autor_codigo": "4484", "autor_nome": "ZUCCO"},
            {"codigo_emenda": "E2", "ano": 2024, "autor_codigo": "7120",
             "autor_nome": "BANCADA DO RIO DE JANEIRO"},
            {"codigo_emenda": "E3", "ano": 2024, "autor_codigo": "5555",
             "autor_nome": "FULANO HOMONIMO"},
            {"codigo_emenda": "E4", "ano": 2024, "autor_codigo": "4034",
             "autor_nome": "LUISA CANZIANI"},
        ]
        n = resolver_autores_emenda_por_nome(banco, emendas, lookup, lookup_nome)
        self.assertEqual(n, 1)  # só o Zucco entrou

        ext = {e["identificador"]: e for e in banco.tabelas["id_externo"]
               if e["sistema"] == "autor_orcamentario"}
        self.assertEqual(set(ext), {"4034", "4484"})       # bancada e homônimo fora
        self.assertEqual(ext["4484"]["grau"], "com_ressalva")
        self.assertTrue(ext["4484"]["pendente_conferencia"])
        self.assertEqual(ext["4484"]["sinais"], ["nome"])
        self.assertEqual(ext["4034"]["grau"], "direto")    # NÃO rebaixado

        # a chain: salvar_emendas resolve o autor pelo id_externo recém-criado
        salvar_emendas(banco, emendas, lookup)
        por_cod = {e["codigo_emenda"]: e for e in banco.tabelas["emenda"]}
        self.assertEqual(por_cod["E1"]["autor_profile_id"], "P-ZUCCO")   # nome
        self.assertEqual(por_cod["E4"]["autor_profile_id"], "P-CANZIANI")  # mapa
        self.assertIsNone(por_cod["E2"]["autor_profile_id"])   # bancada → null
        self.assertIsNone(por_cod["E3"]["autor_profile_id"])   # homônimo → null


def _senador(cod="5672", nome="Alan Rick", civil="Alan Rick Miranda",
             nasc="1976-10-23", mun="Rio Branco", uf_nasc="AC",
             uf="AC", partido="REPUBLICANOS"):
    return {
        "id_fonte": cod, "tipo": "parlamentar", "nome": nome,
        "slug": f"alan-rick-sen-{cod}", "foto_url": None, "ativo": True,
        "nome_civil": civil, "data_nascimento": nasc,
        "naturalidade_municipio": mun, "naturalidade_uf": uf_nasc,
        "sistema_externo": "senado", "identificador_externo": cod,
        "metodo_ligacao": "fonte_direta", "grau": "direto",
        "mandato_hint": {"casa": "senado", "uf": uf, "partido": partido,
                         "legislatura": 57, "vigencia_inicio": "2023-02-01",
                         "vigencia_fim": "2031-01-31", "ocupacao": "titular"},
    }


class TestSenadores(unittest.TestCase):
    def test_sem_candidatos_cria_perfil_proprio(self):
        banco = FakeBanco()
        c = salvar_senadores(banco, [_senador()])
        self.assertEqual(c, {"novos": 1, "vinculados": 0, "pendentes": 0})
        self.assertEqual(len(banco.tabelas["profiles"]), 1)
        ext = banco.tabelas["id_externo"][0]
        self.assertEqual(ext["sistema"], "senado")
        self.assertEqual(ext["metodo"], "fonte_direta")
        # vinculo_temporal NÃO é escrito aqui — é do passo de mandato histórico
        self.assertNotIn("vinculo_temporal", banco.tabelas)

    def test_match_forte_anexa_ao_deputado_sem_criar_perfil(self):
        """§17: 2+ sinais convergem → é a mesma pessoa. id_externo do Senado vai
        para o perfil do deputado; nenhum perfil novo nasce."""
        banco = FakeBanco()
        cand = [{"profile_id": "P-DEP", "nome": "Alan Rick",
                 "nome_civil": "Alan Rick Miranda", "data_nascimento": "1976-10-23",
                 "naturalidade_municipio": "Rio Branco", "naturalidade_uf": "AC"}]
        c = salvar_senadores(banco, [_senador()], cand)
        self.assertEqual(c["vinculados"], 1)
        self.assertEqual(c["novos"], 0)
        self.assertEqual(len(banco.tabelas.get("profiles", [])), 0)  # nenhum novo
        ext = banco.tabelas["id_externo"][0]
        self.assertEqual(ext["profile_id"], "P-DEP")
        self.assertEqual(ext["metodo"], "convergencia")
        self.assertGreaterEqual(len(ext["sinais"]), 2)

    def test_um_sinal_so_nao_auto_funde_e_marca_pendente(self):
        """Só o nome civil converge (deputado sem nascimento) → perfil próprio,
        mas id_externo marcado pendente de conferência (§5.3, ambíguo não funde)."""
        banco = FakeBanco()
        cand = [{"profile_id": "P-DEP", "nome": "Alan Rick",
                 "nome_civil": "Alan Rick Miranda", "data_nascimento": None,
                 "naturalidade_municipio": None, "naturalidade_uf": None}]
        c = salvar_senadores(banco, [_senador()], cand)
        self.assertEqual(c["novos"], 1)
        self.assertEqual(c["pendentes"], 1)
        self.assertEqual(c["vinculados"], 0)
        self.assertTrue(banco.tabelas["id_externo"][0]["pendente_conferencia"])


def _discurso(casa="camara", sistema="camara", pid_fonte="74784",
              id_fonte="74784:2024-12-18T14:00"):
    return {"casa": casa, "sistema": sistema, "parlamentar_id_fonte": pid_fonte,
            "id_fonte": id_fonte, "data": "2024-12-18", "tipo": "COMO LÍDER",
            "sumario": "resumo", "keywords": "A,B", "url_texto": "http://x/t",
            "url_video": "http://x/v", "url_audio": None, "tem_transcricao": True}


class TestDiscursos(unittest.TestCase):
    def test_resolve_autor_e_persiste(self):
        banco = FakeBanco()
        lookup = lambda s, i: "P-DEP" if (s, i) == ("camara", "74784") else None
        n = salvar_discursos(banco, [_discurso()], lookup,
                             source="camara.discursos", source_url="http://cam")
        self.assertEqual(n, 1)
        row = banco.tabelas["discurso"][0]
        self.assertEqual(row["profile_id"], "P-DEP")
        self.assertEqual(row["casa"], "camara")
        self.assertEqual(row["source"], "camara.discursos")

    def test_autor_nao_resolvido_e_pulado(self):
        """Integridade referencial §6: sem perfil, o discurso é pulado, não
        inventado (mesma disciplina do voto nominal órfão)."""
        banco = FakeBanco()
        n = salvar_discursos(banco, [_discurso()], lambda s, i: None,
                             source="camara.discursos", source_url="http://cam")
        self.assertEqual(n, 0)
        self.assertNotIn("discurso", banco.tabelas)

    def test_discurso_do_senado_resolve_por_sistema_senado(self):
        banco = FakeBanco()
        lookup = lambda s, i: "P-SEN" if (s, i) == ("senado", "5672") else None
        n = salvar_discursos(
            banco,
            [_discurso(casa="senado", sistema="senado", pid_fonte="5672",
                       id_fonte="510783")],
            lookup, source="senado.discursos", source_url="http://sen")
        self.assertEqual(n, 1)
        self.assertEqual(banco.tabelas["discurso"][0]["profile_id"], "P-SEN")
        self.assertEqual(banco.tabelas["discurso"][0]["casa"], "senado")


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
