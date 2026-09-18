"""Teste de integração do orquestrador — HTTP e banco fakes, sem rede.

Prova o que o orquestrador existe para garantir: como os deputados são
ingeridos ANTES das votações, o lookup real de id_externo resolve os votos
nominais de ponta a ponta. Se a ordem quebrar, os votos caem na quarentena e
`votos_salvos` despenca — é o que o segundo teste fixa.
"""

import unittest
from datetime import date
from typing import Any

from orquestracao.orquestrador import LinhasBase, ingerir
from pipeline.coletor import JanelaMovel

BASE = "https://dadosabertos.camara.leg.br/api/v2"
SBASE = "https://legis.senado.leg.br/dadosabertos"


class _Resp:
    def __init__(self, status: int, corpo: Any):
        self.status = status
        self.corpo = corpo
    def texto(self) -> str:
        return str(self.corpo)


class ClienteHttpFake:
    """Responde por URL (ignora params). Fila por URL; erro se URL não mapeada."""
    def __init__(self, por_url: dict[str, Any]):
        self.por_url = por_url
        self.chamadas: list[str] = []
    def get(self, url: str, params: dict | None = None) -> _Resp:
        self.chamadas.append(url)
        if url not in self.por_url:
            raise AssertionError(f"sem resposta para {url}")
        return self.por_url[url]


class FakeBanco:
    _CHAVE_BRONZE = ("fonte", "id_na_fonte", "hash_conteudo")
    def __init__(self):
        self.tabelas: dict[str, list[dict]] = {}
        self._seq = 0
    def _t(self, nome): return self.tabelas.setdefault(nome, [])
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
    def inserir_ignorando_conflito(self, tabela, linhas):
        n = 0
        for linha in linhas:
            if any(all(r.get(c) == linha.get(c) for c in self._CHAVE_BRONZE)
                   for r in self._t(tabela)):
                continue
            self._seq += 1
            row = dict(linha); row.setdefault("id", f"{tabela}-{self._seq}")
            self._t(tabela).append(row); n += 1
        return n
    def selecionar_um(self, tabela, onde):
        for r in self._t(tabela):
            if all(r.get(k) == v for k, v in onde.items()):
                return dict(r)
        return None


# -----------------------------------------------------------------------------
# Fixtures de payload
# -----------------------------------------------------------------------------

def _dep(did, nome):
    return {"id": did, "nome": nome, "siglaPartido": "PT", "siglaUf": "SP",
            "idLegislatura": 57, "urlFoto": f"https://x/{did}.jpg",
            "uri": f"{BASE}/deputados/{did}"}

def _dep_det(did):
    return {"id": did, "nomeCivil": f"Nome Civil {did}",
            "dataNascimento": "1970-01-01", "municipioNascimento": "São Paulo",
            "ufNascimento": "SP", "ultimoStatus": {"siglaPartido": "PSD"}}

def _prop(pid):
    return {"id": pid, "siglaTipo": "PL", "numero": 736, "ano": 2015,
            "ementa": "Dispõe sobre algo.", "dataApresentacao": "2015-03-12T18:32"}

def _votacao():
    return {"id": "V-1", "data": "2023-06-10",
            "dataHoraRegistro": "2023-06-10T14:00:00",
            "descricao": "Aprovado. Sim: 1; não: 1; total: 2.",
            "aprovacao": 1,
            "proposicoesAfetadas": [{"id": "100", "uri": f"{BASE}/proposicoes/100"}]}

def _voto(did, tipo):
    return {"tipoVoto": tipo, "deputado_": {
        "id": did, "nome": f"n{did}", "siglaPartido": "PT", "siglaUf": "SP"}}

def _hist(did):
    return {"id": did, "dataHora": "2023-02-01T10:00", "idLegislatura": 57,
            "siglaPartido": "PT", "siglaUf": "SP",
            "condicaoEleitoral": "Titular", "situacao": "Exercício"}

def _desp(did):
    return {"ano": 2023, "mes": 6, "tipoDespesa": "COMBUSTÍVEIS",
            "codDocumento": 1000 + did, "parcela": 0, "dataDocumento": "2023-06-10",
            "valorDocumento": 500.0, "valorGlosa": 0.0, "valorLiquido": 500.0,
            "nomeFornecedor": "Posto X", "cnpjCpfFornecedor": "00000000000191"}


# Um senador (código 900) que é a MESMA pessoa que a deputada Ana (id 1): o
# detalhe da Câmara dá nomeCivil "Nome Civil 1", nascimento 1970-01-01, São
# Paulo/SP — o senador bate por nome civil + nascimento + naturalidade (§17).
def _sen_item():
    return {"IdentificacaoParlamentar": {
        "CodigoParlamentar": "900", "NomeParlamentar": "Ana Senadora",
        "NomeCompletoParlamentar": "Nome Civil 1", "SiglaPartidoParlamentar": "PT",
        "UfParlamentar": "SP", "UrlFotoParlamentar": "http://x/900.jpg"},
        "Mandato": {"PrimeiraLegislaturaDoMandato": {
            "NumeroLegislatura": "57", "DataInicio": "2023-02-01",
            "DataFim": "2027-01-31"}, "DescricaoParticipacao": "Titular"}}


def _mundo(deputados_resp=None):
    """Fábrica do fake HTTP com o mundo inteiro programado."""
    dep_list = deputados_resp if deputados_resp is not None else _Resp(200, {
        "dados": [_dep(1, "Ana"), _dep(2, "Bruno")], "links": []})
    return ClienteHttpFake({
        f"{SBASE}/senador/lista/atual": _Resp(200, {
            "ListaParlamentarEmExercicio": {"Parlamentares": {
                "Parlamentar": [_sen_item()]}}}),
        f"{SBASE}/senador/900": _Resp(200, {"DetalheParlamentar": {"Parlamentar": {
            "IdentificacaoParlamentar": {"CodigoParlamentar": "900"},
            "DadosBasicosParlamentar": {"DataNascimento": "1970-01-01",
                "Naturalidade": "São Paulo", "UfNaturalidade": "SP"}}}}),
        f"{SBASE}/senador/900/mandatos": _Resp(200, {"MandatoParlamentar": {
            "Parlamentar": {"Codigo": "900", "Mandatos": {"Mandato": [{
                "CodigoMandato": "700", "UfParlamentar": "SP",
                "DescricaoParticipacao": "Titular",
                "PrimeiraLegislaturaDoMandato": {"NumeroLegislatura": "57",
                    "DataInicio": "2023-02-01", "DataFim": "2027-01-31"},
                "Partidos": {"Partido": [
                    {"Sigla": "PT", "DataFiliacao": "2023-02-01"}]}}]}}}}),
        # discursos: deputada 1 tem um, deputado 2 nenhum; senador 900 tem um
        f"{BASE}/deputados/1/discursos": _Resp(200, {"dados": [
            {"dataHoraInicio": "2023-06-10T14:00", "tipoDiscurso": "COMO LÍDER",
             "keywords": "A,B", "sumario": "resumo", "urlTexto": "http://x/t",
             "urlVideo": None, "urlAudio": None, "transcricao": "texto"}],
            "links": []}),
        f"{BASE}/deputados/2/discursos": _Resp(200, {"dados": [], "links": []}),
        f"{SBASE}/comissao/lista/colegiados": _Resp(200, {"ListaColegiados": {
            "Colegiados": {"Colegiado": [
                {"Codigo": "34", "Sigla": "CCJ", "Nome": "Comissão de Constituição",
                 "DescricaoTipoColegiado": "Comissão Permanente", "SiglaCasa": "SF"},
                {"Codigo": "99", "Sigla": "FPX", "Nome": "Frente X",
                 "DescricaoTipoColegiado": "Frente Parlamentar", "SiglaCasa": "SF"}]}}}),
        f"{SBASE}/composicao/lista/blocos": _Resp(200, {"ListaBlocoParlamentar": {
            "Blocos": {"Bloco": [{"CodigoBloco": "346",
                "NomeBloco": "Bloco Parlamentar Aliança", "NomeApelido": "BLALIANÇA",
                "DataCriacao": "2023-03-20"}]}}}),
        f"{SBASE}/materia/pesquisa/lista": _Resp(200, {"PesquisaBasicaMateria": {
            "Materias": {"Materia": [{"Codigo": "161856",
                "IdentificacaoProcesso": "8614284",
                "DescricaoIdentificacao": "PL 1/2024", "Sigla": "PL",
                "Numero": "00001", "Ano": "2024", "Ementa": "Ementa do Senado",
                "Data": "2023-06-05", "UrlDetalheMateria": "http://x/m/161856"}]}}}),
        f"{SBASE}/processo/8614284": _Resp(200, {"id": 8614284,
            "codigoMateria": "161856", "autuacoes": [{"numero": 1,
                "movimentacoes": [], "informesLegislativos": [
                    {"id": 1, "data": "2023-06-05 10:00:00",
                     "colegiado": {"sigla": "PLEN"}, "descricao": "Recebida"},
                    {"id": 2, "data": "2023-06-06 11:00:00",
                     "colegiado": {"sigla": "CCJ"}, "descricao": "Distribuída"}]}]}),
        f"{SBASE}/votacao": _Resp(200, [{
            "codigoSessaoVotacao": 6883, "codigoMateria": "161856", "sigla": "PL",
            "numero": "1", "ano": 2024, "dataSessao": "2023-06-10",
            "descricaoVotacao": "Votação do PL 1/2024", "identificacao": "PL 1/2024",
            "resultadoVotacao": "A", "votacaoSecreta": "N", "totalVotosSim": 1,
            "totalVotosNao": 0, "totalVotosAbstencao": 0, "votos": [
                {"codigoParlamentar": 900, "siglaVotoParlamentar": "Sim",
                 "nomeParlamentar": "Ana Senadora", "siglaPartidoParlamentar": "PT",
                 "siglaUFParlamentar": "SP"}]}]),
        f"{SBASE}/senador/900/discursos": _Resp(200, {"DiscursosParlamentar": {
            "Parlamentar": {"Pronunciamentos": {"Pronunciamento": [
                {"CodigoPronunciamento": "777", "DataPronunciamento": "2023-06-11",
                 "TipoUsoPalavra": {"Descricao": "Discurso"}, "TextoResumo": "r",
                 "Indexacao": "X", "UrlTexto": "http://x/p",
                 "UrlTextoBinario": "http://x/b"}]}}}}),
        f"{BASE}/partidos": _Resp(200, {"dados": [
            {"id": 10, "sigla": "PT", "nome": "Partido dos Trabalhadores"}],
            "links": []}),
        f"{BASE}/partidos/10": _Resp(200, {"dados": {
            "id": 10, "numeroEleitoral": 13, "status": {"situacao": "Ativo"}}}),
        f"{BASE}/orgaos": _Resp(200, {"dados": [
            {"id": 2003, "sigla": "CCJC", "nome": "Comissão CCJC", "codTipoOrgao": 2}],
            "links": []}),
        f"{BASE}/frentes": _Resp(200, {"dados": [
            {"id": 55703, "titulo": "Frente Parlamentar X", "idLegislatura": 57}],
            "links": []}),
        f"{BASE}/deputados": dep_list,
        f"{BASE}/deputados/1": _Resp(200, {"dados": _dep_det(1)}),
        f"{BASE}/deputados/2": _Resp(200, {"dados": _dep_det(2)}),
        f"{BASE}/deputados/1/historico": _Resp(200, {"dados": [_hist(1)]}),
        f"{BASE}/deputados/2/historico": _Resp(200, {"dados": [_hist(2)]}),
        f"{BASE}/deputados/1/despesas": _Resp(200, {"dados": [_desp(1)], "links": []}),
        f"{BASE}/deputados/2/despesas": _Resp(200, {"dados": [_desp(2)], "links": []}),
        f"{BASE}/proposicoes": _Resp(200, {"dados": [_prop("100")], "links": []}),
        f"{BASE}/proposicoes/100/tramitacoes": _Resp(200, {"dados": [
            {"sequencia": 1, "dataHora": "2015-03-12T18:32", "siglaOrgao": "PLEN",
             "descricaoTramitacao": "Apresentação", "despacho": None},
            {"sequencia": 2, "dataHora": "2015-03-15T09:00", "siglaOrgao": "CCJC",
             "descricaoTramitacao": "Às Comissões", "despacho": "Despacho x"},
        ], "links": []}),
        f"{BASE}/eventos": _Resp(200, {"dados": [{"id": 9001,
            "dataHoraInicio": "2023-06-10T14:00", "dataHoraFim": None,
            "situacao": "Realizada", "descricaoTipo": "Audiência Pública",
            "descricao": "Debate sobre X", "localExterno": None,
            "orgaos": [{"id": 2003, "sigla": "CCJC", "nome": "CCJC"}],
            "localCamara": {"nome": "Sala 1"}, "urlRegistro": "http://x/e"}],
            "links": []}),
        f"{SBASE}/comissao/agenda/mes/202305": _Resp(200, {"AgendaReuniao": {
            "reunioes": {"reuniao": []}}}),
        f"{SBASE}/comissao/agenda/mes/202306": _Resp(200, {"AgendaReuniao": {
            "reunioes": {"reuniao": [{"codigo": "7001", "titulo": "Reunião Y",
                "dataInicio": "2023-06-11T10:00:00.000", "situacao": "Agendada",
                "local": "Anexo", "colegiadoCriador": {"codigo": "834",
                    "sigla": "CDH", "nome": "CDH",
                    "descricaoTipo": "Comissão Permanente"}}]}}}),
        f"{BASE}/votacoes": _Resp(200, {"dados": [_votacao()], "links": []}),
        f"{BASE}/votacoes/V-1": _Resp(200, {"dados": _votacao()}),
        f"{BASE}/votacoes/V-1/votos": _Resp(200, {"dados": [
            _voto(1, "Sim"), _voto(2, "Não")]}),
    })


class TestOrquestrador(unittest.TestCase):
    def test_fluxo_completo_resolve_votos_ponta_a_ponta(self):
        http = _mundo()
        banco = FakeBanco()
        # curadoria: o código de autor 9001 mapeia para a deputada Ana (id 1)
        mapa_csv = (
            "codigo_autor;nome_na_fonte;deputado_id;nome_camara;sinais;n_sinais;"
            "classe;ufs_do_gasto;conferido_por_humano\n"
            "9001;ANA;1;Ana;nome,UF;2;2 sinais;;\n")
        r = ingerir(http, banco, ate=date(2023, 6, 30), janela=JanelaMovel(dias=30),
                    id_legislatura=57, abrir_mapa_autores=lambda: mapa_csv)

        # curadoria materializou o autor orçamentário 9001 → perfil da Ana
        self.assertEqual(r.autores_camara_resolvidos, 1)
        ana_dep = next(e for e in banco.tabelas["id_externo"]
                       if e["sistema"] == "camara" and e["identificador"] == "1")
        autor = next(e for e in banco.tabelas["id_externo"]
                     if e["sistema"] == "autor_orcamentario")
        self.assertEqual(autor["identificador"], "9001")
        self.assertEqual(autor["profile_id"], ana_dep["profile_id"])

        # perfis + id_externo (profiles inclui os 2 parlamentares + 1 partido)
        self.assertEqual(r.perfis_salvos, 2)
        parlamentares = [p for p in banco.tabelas["profiles"]
                         if p["tipo"] == "parlamentar"]
        self.assertEqual(len(parlamentares), 2)
        camara_ext = [e for e in banco.tabelas["id_externo"] if e["sistema"] == "camara"]
        self.assertEqual(len(camara_ext), 2)

        # partidos canônicos ingeridos (profile tipo=partido + partido)
        self.assertEqual(r.partidos_salvos, 1)

        # perfis coletivos: comissão + frente (polimórficos, mesma tabela)
        self.assertEqual(r.comissoes_salvas, 1)
        self.assertEqual(r.frentes_salvas, 1)
        tipos = {p["tipo"] for p in banco.tabelas["profiles"]}
        self.assertTrue({"comissao", "frente", "partido", "parlamentar"} <= tipos)

        # despesas / CEAP por parlamentar (§8) — uma por pessoa
        self.assertEqual(r.despesas_salvas, 2)
        self.assertEqual(len(banco.tabelas["despesa"]), 2)

        # vínculos temporais (um titular por pessoa, em aberto) — camada §4
        self.assertEqual(r.vinculos_salvos, 2)
        self.assertEqual(len(banco.tabelas["vinculo_temporal"]), 2)
        # partido_id RESOLVIDO por sigla (PT foi ingerido no passo 0)
        partido_pt = banco.tabelas["partido"][0]["id"]
        v0 = banco.tabelas["vinculo_temporal"][0]
        self.assertEqual(v0["partido_sigla_fonte"], "PT")
        self.assertEqual(v0["partido_id"], partido_pt)

        # proposição + suas tramitações (prendem-se à proposição já persistida)
        self.assertEqual(r.proposicoes_salvas, 1)
        self.assertEqual(r.tramitacoes_salvas, 2)
        self.assertEqual(len(banco.tabelas["tramitacao"]), 2)
        prop_uuid_t = banco.tabelas["proposicao"][0]["id"]
        for t in banco.tabelas["tramitacao"]:
            self.assertEqual(t["proposicao_id"], prop_uuid_t)

        # votação com a matéria resolvida (FK uuid, não o id da fonte)
        self.assertEqual(r.votacoes_salvas, 1)
        prop_uuid = banco.tabelas["proposicao"][0]["id"]
        self.assertEqual(banco.tabelas["votacao"][0]["proposicao_id"], prop_uuid)

        # OS VOTOS RESOLVERAM porque os deputados vieram antes → lookup real
        self.assertEqual(r.votos_salvos, 2)
        perfis_ids = {p["id"] for p in banco.tabelas["profiles"]}
        for v in banco.tabelas["voto_nominal"]:
            self.assertIn(v["perfil_id"], perfis_ids)

        # placar bate com os nominais → sem divergência (§5.2)
        self.assertEqual(r.placar_violacoes, {})

        # Preservação de bronze COMPLETA (§3.1): lista+detalhe da votação e os
        # votos, além de deputados e proposição. O voto tem id composto.
        ids_bronze = {b["id_na_fonte"] for b in banco.tabelas["bronze_registro"]}
        self.assertIn("V-1:1", ids_bronze)   # voto do deputado 1 na votação V-1
        self.assertIn("V-1:2", ids_bronze)   # voto do deputado 2
        # 2 deputados + 1 prop + 1 tramitação(seq via prop) ... ao menos as
        # listas + detalhe da votação + 2 votos entram na contagem.
        self.assertGreaterEqual(r.bronze_salvo, 6)

    def test_tramitacoes_desligadas_nao_salvam_mas_proposicao_entra(self):
        """Par do teste ponta-a-ponta (que liga tramitações → 2): com
        `coletar_tramitacoes=False` a cauda cara não roda (0 tramitações), mas a
        proposição continua entrando. É o gate que faz o backfill de atividade
        caber num job de nuvem (<6h)."""
        http = _mundo()
        banco = FakeBanco()
        r = ingerir(http, banco, ate=date(2023, 6, 30), janela=JanelaMovel(dias=30),
                    id_legislatura=57, coletar_tramitacoes=False)
        # proposição AINDA entra (é dado de alto valor, leve)
        self.assertEqual(r.proposicoes_salvas, 1)
        self.assertEqual(len(banco.tabelas["proposicao"]), 1)
        # tramitações NÃO — nem contagem nem linha
        self.assertEqual(r.tramitacoes_salvas, 0)
        self.assertEqual(len(banco.tabelas.get("tramitacao", [])), 0)

    def test_data_apresentacao_persistida_como_date(self):
        http = _mundo()
        banco = FakeBanco()
        ingerir(http, banco, ate=date(2023, 6, 30), janela=JanelaMovel(dias=30))
        self.assertEqual(
            banco.tabelas["proposicao"][0]["data_apresentacao"], "2015-03-12")

    def test_senado_bicameral_vincula_senador_ao_deputado(self):
        """§17 ponta a ponta: o senador 900 é a mesma pessoa que a deputada Ana
        (id 1). Com `coletar_senado`, o id_externo do Senado prende NO PERFIL da
        deputada — sem criar perfil novo."""
        http = _mundo()
        banco = FakeBanco()
        # CEAPS: a senadora Ana (= deputada Ana, §17) tem uma despesa em 2023
        ceaps_csv = (
            '"ANO";"MES";"SENADOR";"TIPO_DESPESA";"CNPJ_CPF";"FORNECEDOR";'
            '"DOCUMENTO";"DATA";"DETALHAMENTO";"VALOR_REEMBOLSADO";"COD_DOCUMENTO"\n'
            '"2023";"6";"ANA SENADORA";"Aluguel";"00.0/0001-00";"X";"1";'
            '"10/06/2023";"";"1.000,00";"555"\n')
        r = ingerir(http, banco, ate=date(2023, 6, 30), janela=JanelaMovel(dias=30),
                    id_legislatura=57, coletar_senado=True, coletar_eventos=True,
                    baixar_ceaps=lambda url: ceaps_csv, anos_ceaps=[2023])

        self.assertEqual(r.senadores_vinculados, 1)
        self.assertEqual(r.senadores_novos, 0)

        # comissões (só a permanente, não a frente) + bloco do Senado — o tipo
        # 'bloco' estreia na tabela polimórfica profiles
        self.assertEqual(r.comissoes_senado_salvas, 1)
        self.assertEqual(r.blocos_senado_salvos, 1)
        tipos = {p["tipo"] for p in banco.tabelas["profiles"]}
        self.assertIn("bloco", tipos)
        com_sf = [p for p in banco.tabelas["profiles"]
                  if p["tipo"] == "comissao" and p["slug"].startswith("comissao-sf")]
        self.assertEqual(len(com_sf), 1)

        # mandato histórico do Senado → vinculo_temporal (casa=senado), preso ao
        # perfil unificado da Ana; partido/UF por período (§4)
        ana = next(e for e in banco.tabelas["id_externo"]
                   if e["sistema"] == "camara" and e["identificador"] == "1")
        self.assertGreaterEqual(r.vinculos_senado_salvos, 1)
        vt_sen = [v for v in banco.tabelas["vinculo_temporal"] if v["casa"] == "senado"]
        self.assertEqual(len(vt_sen), 1)
        self.assertEqual(vt_sen[0]["profile_id"], ana["profile_id"])
        self.assertEqual(vt_sen[0]["partido_sigla_fonte"], "PT")

        # eventos das DUAS casas (área nova): 1 da Câmara + 1 do Senado
        self.assertEqual(r.eventos_salvos, 2)
        casas_ev = {e["casa"] for e in banco.tabelas["evento"]}
        self.assertEqual(casas_ev, {"camara", "senado"})
        # o evento da Câmara (CCJC id 2003) resolve ao perfil da comissão pelo slug
        ev_cam = next(e for e in banco.tabelas["evento"] if e["casa"] == "camara")
        com_ccjc = next(p for p in banco.tabelas["profiles"]
                        if p.get("slug") == "comissao-ccjc-2003")
        self.assertEqual(ev_cam["orgao_profile_id"], com_ccjc["id"])

        # CEAPS do Senado resolvido por NOME → cai no perfil unificado da Ana
        self.assertEqual(r.despesas_senado_salvas, 1)
        desp = banco.tabelas["despesa"]
        ana_desp = [d for d in desp if d["perfil_id"] == ana["profile_id"]
                    and d["source"] == "senado.ceaps"]
        self.assertEqual(len(ana_desp), 1)
        self.assertEqual(ana_desp[0]["valor_liquido"], 1000.0)
        # ainda só 2 parlamentares (Ana e Bruno) — o senador não virou um terceiro
        parlamentares = [p for p in banco.tabelas["profiles"]
                         if p["tipo"] == "parlamentar"]
        self.assertEqual(len(parlamentares), 2)
        # o id_externo do Senado aponta ao mesmo perfil da deputada da Câmara
        ext_sen = [e for e in banco.tabelas["id_externo"] if e["sistema"] == "senado"]
        self.assertEqual(len(ext_sen), 1)
        ana_camara = next(e for e in banco.tabelas["id_externo"]
                          if e["sistema"] == "camara" and e["identificador"] == "1")
        self.assertEqual(ext_sen[0]["profile_id"], ana_camara["profile_id"])
        self.assertEqual(ext_sen[0]["metodo"], "convergencia")

    def test_ceaps_off_ainda_ingere_senadores_para_resolver_autor(self):
        """Fase 1 da curadoria de autor-senador: com CEAPS desligado
        (coletar_despesas_senado=False) mas Senado ligado, os senadores AINDA
        entram — é o que mantém o `lookup_senador_nome` vivo para resolver os
        autores de emenda —, e nenhuma despesa de CEAPS é gravada."""
        http = _mundo()
        banco = FakeBanco()
        r = ingerir(http, banco, ate=date(2023, 6, 30), janela=JanelaMovel(dias=30),
                    id_legislatura=57, coletar_senado=True,
                    coletar_despesas_senado=False,
                    baixar_ceaps=lambda url: "", anos_ceaps=[2023])
        # CEAPS NÃO grava (o flag desligou o passo)
        self.assertEqual(r.despesas_senado_salvas, 0)
        ceaps = [d for d in banco.tabelas.get("despesa", [])
                 if d.get("source") == "senado.ceaps"]
        self.assertEqual(ceaps, [])
        # mas o senador entrou e foi unificado (§17) — braço de resolução vivo
        self.assertEqual(r.senadores_vinculados, 1)
        self.assertEqual(len([e for e in banco.tabelas["id_externo"]
                              if e["sistema"] == "senado"]), 1)

    def test_config_dinheiro_senado_traz_ceaps_sem_legislativo(self):
        """Desempacotamento CEAPS: com o Senado LIGADO mas proposições/votações
        DESLIGADAS (a base de dinheiro no Free), entram senadores + CEAPS e NÃO
        entram matérias nem votações do Senado — o gate duplo em ação."""
        http = _mundo()
        banco = FakeBanco()
        ceaps_csv = (
            '"ANO";"MES";"SENADOR";"TIPO_DESPESA";"CNPJ_CPF";"FORNECEDOR";'
            '"DOCUMENTO";"DATA";"DETALHAMENTO";"VALOR_REEMBOLSADO";"COD_DOCUMENTO"\n'
            '"2023";"6";"ANA SENADORA";"Aluguel";"00.0/0001-00";"X";"1";'
            '"10/06/2023";"";"1.000,00";"555"\n')
        r = ingerir(http, banco, ate=date(2023, 6, 30), janela=JanelaMovel(dias=30),
                    id_legislatura=57, coletar_senado=True,
                    coletar_proposicoes=False, coletar_votacoes=False,
                    baixar_ceaps=lambda url: ceaps_csv, anos_ceaps=[2023])
        # dinheiro do Senado ENTRA: senador resolvido (§17) + CEAPS
        self.assertEqual(r.despesas_senado_salvas, 1)
        self.assertEqual(r.senadores_vinculados, 1)
        # legislativo do Senado NÃO entra (desempacotado do coletar_senado)
        self.assertEqual(r.materias_senado_salvas, 0)
        self.assertEqual(r.votacoes_senado_salvas, 0)
        self.assertEqual(r.votos_senado_salvos, 0)
        self.assertNotIn("votacao", banco.tabelas)
        casas_prop = {p["casa_origem"] for p in banco.tabelas.get("proposicao", [])}
        self.assertNotIn("senado", casas_prop)

    def test_materias_do_senado_entram_na_tabela_proposicao(self):
        """Área B bicameral: a matéria do Senado cai na MESMA tabela `proposicao`
        (casa_origem='senado'), ao lado das proposições da Câmara."""
        http = _mundo()
        banco = FakeBanco()
        r = ingerir(http, banco, ate=date(2023, 6, 30), janela=JanelaMovel(dias=30),
                    id_legislatura=57, coletar_senado=True)
        self.assertGreaterEqual(r.materias_senado_salvas, 1)
        casas = {p["casa_origem"] for p in banco.tabelas["proposicao"]}
        self.assertEqual(casas, {"camara", "senado"})
        mat = next(p for p in banco.tabelas["proposicao"]
                   if p["casa_origem"] == "senado")
        self.assertEqual(mat["identificador"], "PL 1/2024")
        self.assertEqual(mat["id_na_fonte"], "161856")

        # tramitações do Senado prendem-se à matéria (via /processo/{idProcesso})
        self.assertGreaterEqual(r.tramitacoes_senado_salvas, 2)
        tr = [t for t in banco.tabelas["tramitacao"]
              if t["proposicao_id"] == mat["id"]]
        self.assertEqual(len(tr), 2)
        self.assertEqual({t["sequencia"] for t in tr}, {1, 2})

        # votação do Senado + voto nominal resolvido ao perfil do senador (que é
        # a deputada Ana unificada, §17): a votação prende à matéria do Senado
        self.assertEqual(r.votacoes_senado_salvas, 1)
        self.assertEqual(r.votos_senado_salvos, 1)
        vs = next(v for v in banco.tabelas["votacao"] if v["casa"] == "senado")
        self.assertEqual(vs["proposicao_id"], mat["id"])
        self.assertEqual(vs["sim"], 1)
        ana = next(e for e in banco.tabelas["id_externo"]
                   if e["sistema"] == "camara" and e["identificador"] == "1")
        vn = next(v for v in banco.tabelas["voto_nominal"]
                  if v["votacao_id"] == vs["id"])
        self.assertEqual(vn["perfil_id"], ana["profile_id"])
        self.assertEqual(vn["voto"], "sim")

    def test_discursos_bicamerais_resolvem_o_autor(self):
        """Área G ponta a ponta: discurso da Câmara (dep 1) + do Senado (sen 900)
        entram na MESMA tabela, cada um resolvido ao seu perfil. O do senador
        cai no perfil da deputada Ana (mesma pessoa, §17)."""
        http = _mundo()
        banco = FakeBanco()
        r = ingerir(http, banco, ate=date(2023, 6, 30), janela=JanelaMovel(dias=30),
                    id_legislatura=57, coletar_senado=True, coletar_discursos=True)

        self.assertEqual(r.discursos_salvos, 2)   # 1 câmara + 1 senado
        casas = {d["casa"] for d in banco.tabelas["discurso"]}
        self.assertEqual(casas, {"camara", "senado"})
        sen_disc = next(d for d in banco.tabelas["discurso"] if d["casa"] == "senado")
        ana = next(e for e in banco.tabelas["id_externo"]
                   if e["sistema"] == "camara" and e["identificador"] == "1")
        self.assertEqual(sen_disc["profile_id"], ana["profile_id"])

    def test_config_enxuta_dinheiro_liga_so_o_essencial(self):
        """Caber no Free/priorizar dinheiro: bronze + proposições + votações OFF,
        despesas ON. Sem essas tabelas gordas; a despesa (o alvo) entra."""
        http = _mundo()
        banco = FakeBanco()
        r = ingerir(http, banco, ate=date(2023, 6, 30), janela=JanelaMovel(dias=30),
                    id_legislatura=57, persistir_bronze=False,
                    coletar_proposicoes=False, coletar_votacoes=False)
        # dinheiro entra (despesas dos deputados)
        self.assertEqual(r.despesas_salvas, 2)
        self.assertIn("despesa", banco.tabelas)
        # o que foi desligado NÃO entra
        self.assertEqual(r.bronze_salvo, 0)
        self.assertNotIn("bronze_registro", banco.tabelas)
        self.assertNotIn("proposicao", banco.tabelas)
        self.assertNotIn("votacao", banco.tabelas)
        self.assertEqual(r.proposicoes_salvas, 0)
        self.assertEqual(r.votos_salvos, 0)

    def test_deputados_ausentes_deixam_votos_sem_resolver(self):
        """A dependência de ordem, provada pela negativa: sem deputados, o lookup
        não resolve e nenhum voto nominal é persistido — mas a rodada não cai."""
        http = _mundo(deputados_resp=_Resp(404, "not found"))
        banco = FakeBanco()
        r = ingerir(http, banco, ate=date(2023, 6, 30), janela=JanelaMovel(dias=30))

        self.assertEqual(r.perfis_salvos, 0)
        self.assertEqual(r.votos_salvos, 0)            # votos caíram na quarentena
        self.assertEqual(r.votacoes_salvas, 1)         # a votação em si persiste
        self.assertNotIn("voto_nominal", banco.tabelas)


if __name__ == "__main__":
    unittest.main(verbosity=2)
