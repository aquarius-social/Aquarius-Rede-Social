"""Testes da camada de identidade.

Cada teste ataca um dos modos de falha catalogados na Tabela 9 da Metodologia
de Dados. A disciplina vem da seção 5.2:

    "como verificação que sempre passa é indistinguível de verificação
     desligada, cada identidade é exercitada contra um registro
     deliberadamente corrompido antes de entrar em regime."

Por isso, para cada regra há um caso que ela deve ACEITAR e um caso que ela
deve RECUSAR.

Escritos sobre `unittest` da biblioteca padrão, sem dependência externa:
rodam com `python -m unittest` em qualquer máquina e também sob `pytest`.
"""

import unittest
from datetime import date

from resolucao.normalizacao import (
    mesmo_nome,
    normalizar,
    sem_titulos,
    sufixo_geracional,
    tem_titulo_ou_patente,
)
from resolucao.resolvedor import (
    Alvo,
    Candidato,
    Grau,
    Mandato,
    resolver,
    verificar_bijecao_autoria,
)

# -----------------------------------------------------------------------------
# Fixtures: um universo mínimo mas realista
# -----------------------------------------------------------------------------

MANDATO_ATUAL = Mandato(casa="camara", inicio=date(2023, 2, 1), fim=None, uf="SP")
MANDATO_ANTERIOR = Mandato(
    casa="camara", inicio=date(2019, 2, 1), fim=date(2023, 1, 31), uf="SP"
)


def _dep(pid, nome, civil=None, nasc=None, mun=None, uf=None, mandatos=(MANDATO_ATUAL,)):
    return Candidato(
        profile_id=pid,
        nome_parlamentar=nome,
        nome_civil=civil,
        data_nascimento=nasc,
        naturalidade_municipio=mun,
        naturalidade_uf=uf,
        mandatos=tuple(mandatos),
    )


# =============================================================================
# Modo de falha: "Normalização excessiva de nomes"
#   comportamento observado: pai e filho diferem por uma palavra final
#   resposta errada que produziria: duas pessoas fundidas num perfil
# =============================================================================

class TestNormalizacaoPreservaSufixo(unittest.TestCase):
    def test_particulas_de_ligacao_sao_removidas(self):
        self.assertEqual(normalizar("José de Souza"), normalizar("Jose Souza"))

    def test_acentos_e_caixa_sao_removidos(self):
        self.assertEqual(normalizar("JOSÉ SOUZA"), normalizar("josé souza"))

    def test_pai_e_filho_nao_colapsam(self):
        """O caso-limite real da seção 6.2."""
        pai = "Antonio Carlos Rodrigues"
        filho = "Antonio Carlos Rodrigues Filho"
        self.assertNotEqual(normalizar(pai), normalizar(filho))
        self.assertFalse(mesmo_nome(pai, filho))

    def test_deteccao_de_sufixo(self):
        casos = [
            ("Antonio Rodrigues Filho", "filho"),
            ("Maria Silva Neto", "neto"),
            ("João Santos Júnior", "junior"),
            ("Ana Paula Costa", None),
            # Partícula depois do sufixo não deve confundir a busca.
            ("Pedro de Alcântara Neto", "neto"),
        ]
        for nome, esperado in casos:
            with self.subTest(nome=nome):
                self.assertEqual(sufixo_geracional(nome), esperado)

    def test_registro_corrompido_e_rejeitado(self):
        """Exercita o detector contra o caso que ele existe para pegar."""
        self.assertFalse(mesmo_nome("Carlos Silva Filho", "Carlos Silva Neto"))


# =============================================================================
# Modo de falha: "Condição necessária tratada como evidência"
#   comportamento observado: candidato fora de mandato somava pontos
#   resposta errada que produziria: ambiguidade fabricada
# =============================================================================

class TestFiltrosAntesDeEvidencias(unittest.TestCase):
    def test_candidato_sem_mandato_na_data_e_eliminado_nao_pontuado(self):
        universo = [
            _dep("A", "Ana Costa", civil="Ana Costa", mandatos=(MANDATO_ATUAL,)),
            # Homônima perfeita, mas mandato encerrado antes do fato.
            _dep("B", "Ana Costa", civil="Ana Costa", mandatos=(MANDATO_ANTERIOR,)),
        ]
        alvo = Alvo(
            nome="Ana Costa",
            nome_civil="Ana Costa",
            data_do_fato=date(2025, 6, 1),
            casa="camara",
        )
        r = resolver(alvo, universo)

        # Se o filtro tivesse virado evidência, teríamos ambiguidade entre A e B.
        self.assertEqual(r.candidatos_apos_filtro, 1)
        self.assertEqual(r.profile_id, "A")
        self.assertIs(r.grau, Grau.COM_RESSALVA)  # um sinal só (família NOME)

    def test_casa_incompativel_elimina(self):
        universo = [_dep("A", "Ana Costa", civil="Ana Costa")]
        alvo = Alvo(
            nome="Ana Costa",
            nome_civil="Ana Costa",
            data_do_fato=date(2025, 6, 1),
            casa="senado",
        )
        r = resolver(alvo, universo)
        self.assertIs(r.grau, Grau.RECUSADO)
        self.assertEqual(r.candidatos_apos_filtro, 0)
        self.assertIn("mandato vigente", r.divergencia)

    def test_fato_anterior_ao_mandato_elimina(self):
        universo = [_dep("A", "Ana Costa", civil="Ana Costa")]
        alvo = Alvo(
            nome="Ana Costa", nome_civil="Ana Costa", data_do_fato=date(2020, 6, 1)
        )
        self.assertIs(resolver(alvo, universo).grau, Grau.RECUSADO)


# =============================================================================
# Modo de falha: "Atributo resolvido no presente"
#   comportamento observado: partido muda ao longo do mandato
#   resposta errada que produziria: voto antigo atribuído ao partido atual
#
# E o caso da seção 6.3: resolver autor de emenda de 2025 contra a composição
# de 2026 desloca suplentes que efetivamente exerceram.
# =============================================================================

class TestResolucaoNaDataDoFato(unittest.TestCase):
    def test_suplente_do_exercicio_anterior_e_encontrado_na_data_certa(self):
        titular_volta = Mandato(
            casa="senado", inicio=date(2026, 1, 1), fim=None, uf="BA"
        )
        suplente_exerceu = Mandato(
            casa="senado", inicio=date(2024, 3, 1), fim=date(2025, 12, 31), uf="BA"
        )
        universo = [
            _dep("TITULAR", "Fulano Titular", civil="Fulano Titular",
                 mandatos=(titular_volta,)),
            _dep("SUPLENTE", "Beltrano Suplente", civil="Beltrano Suplente",
                 mandatos=(suplente_exerceu,)),
        ]
        # Emenda apresentada em 2025 — quem exercia era o suplente.
        alvo_2025 = Alvo(
            nome="Beltrano Suplente",
            nome_civil="Beltrano Suplente",
            data_do_fato=date(2025, 8, 15),
            casa="senado",
        )
        self.assertEqual(resolver(alvo_2025, universo).profile_id, "SUPLENTE")

        # A mesma pessoa NÃO deve ser resolvida para um fato de 2026.
        alvo_2026 = Alvo(
            nome="Beltrano Suplente",
            nome_civil="Beltrano Suplente",
            data_do_fato=date(2026, 8, 15),
            casa="senado",
        )
        self.assertIs(resolver(alvo_2026, universo).grau, Grau.RECUSADO)


# =============================================================================
# Regra de independência de sinais (seção 5.3)
#   "o município de nascimento implica a unidade federativa, e contá-los como
#    dois fabrica confiança"
# =============================================================================

class TestIndependenciaDeSinais(unittest.TestCase):
    def test_municipio_e_uf_contam_uma_vez_so(self):
        universo = [_dep("A", "Ana Costa", civil="Ana Costa", mun="Santos", uf="SP")]
        alvo = Alvo(
            nome="Ana Costa",
            nome_civil="Ana Costa",
            naturalidade_municipio="Santos",
            naturalidade_uf="SP",
            data_do_fato=date(2025, 6, 1),
        )
        r = resolver(alvo, universo)
        # NOME + ORIGEM = 2 famílias. Se município e UF contassem separado,
        # seriam 3 sinais — confiança inflada.
        self.assertEqual(len(r.sinais), 2)
        self.assertIn("naturalidade_municipio", r.sinais)
        self.assertNotIn("naturalidade_uf", r.sinais)
        self.assertIs(r.grau, Grau.DIRETO)

    def test_nome_civil_e_parlamentar_nao_somam(self):
        universo = [_dep("A", "Ana Costa", civil="Ana Maria Costa")]
        alvo = Alvo(
            nome="Ana Costa",
            nome_civil="Ana Maria Costa",
            data_do_fato=date(2025, 6, 1),
        )
        r = resolver(alvo, universo)
        self.assertEqual(r.sinais, ["nome_civil"])
        self.assertIs(r.grau, Grau.COM_RESSALVA)

    def test_dois_sinais_independentes_dao_grau_direto(self):
        universo = [
            _dep("A", "Ana Costa", civil="Ana Costa", nasc=date(1980, 5, 12))
        ]
        alvo = Alvo(
            nome="Ana Costa",
            nome_civil="Ana Costa",
            data_nascimento=date(1980, 5, 12),
            data_do_fato=date(2025, 6, 1),
        )
        r = resolver(alvo, universo)
        self.assertIs(r.grau, Grau.DIRETO)
        self.assertEqual(set(r.sinais), {"nome_civil", "data_nascimento"})


# =============================================================================
# Modo de falha: "Colisão de rótulo lida como ambiguidade"
#   comportamento observado: seis colisões de nome; nenhuma ambiguidade real
#   resposta errada que produziria: recusa onde há resposta
#
# E o inverso — ambiguidade real deve produzir recusa, nunca escolha do mais
# provável (seção 5.3).
# =============================================================================

class TestColisaoVersusAmbiguidade(unittest.TestCase):
    def test_colisao_de_nome_parlamentar_e_resolvida_pelo_nome_civil(self):
        """Dois deputados com o mesmo nome de urna, nomes civis distintos."""
        universo = [
            _dep("A", "Dr. Carlos", civil="Carlos Alberto Souza",
                 nasc=date(1970, 1, 1)),
            _dep("B", "Dr. Carlos", civil="Carlos Eduardo Lima",
                 nasc=date(1982, 9, 30)),
        ]
        alvo = Alvo(
            nome="Dr. Carlos",
            nome_civil="Carlos Eduardo Lima",
            data_nascimento=date(1982, 9, 30),
            data_do_fato=date(2025, 6, 1),
        )
        r = resolver(alvo, universo)
        self.assertIs(r.grau, Grau.DIRETO)
        self.assertEqual(r.profile_id, "B")

    def test_ambiguidade_real_produz_recusa_e_nao_escolha(self):
        universo = [
            _dep("A", "Ana Costa", civil="Ana Costa"),
            _dep("B", "Ana Costa", civil="Ana Costa"),
        ]
        alvo = Alvo(
            nome="Ana Costa", nome_civil="Ana Costa", data_do_fato=date(2025, 6, 1)
        )
        r = resolver(alvo, universo)
        self.assertIs(r.grau, Grau.RECUSADO)
        self.assertIsNone(r.profile_id)
        self.assertIn("ambiguidade", r.divergencia)
        self.assertTrue(r.pendente_conferencia)

    def test_data_de_nascimento_coincidente_com_nome_divergente_e_rejeitada(self):
        """A seção 6.1 mediu: dez pares de mesma data de nascimento com nome
        divergente foram todos rejeitados, sem falso aceite."""
        universo = [
            _dep("A", "Ana Costa", civil="Ana Costa", nasc=date(1980, 5, 12))
        ]
        alvo = Alvo(
            nome="Bruno Dias",
            nome_civil="Bruno Dias",
            data_nascimento=date(1980, 5, 12),
            data_do_fato=date(2025, 6, 1),
        )
        r = resolver(alvo, universo)
        self.assertIs(r.grau, Grau.RECUSADO)
        self.assertIsNone(r.profile_id)


# =============================================================================
# Resíduo por variante de nome (seção 6.3)
#   "patente militar presente numa fonte e ausente na outra, título religioso
#    abreviado... o resolvedor deixa a linha sem atribuição"
# =============================================================================

class TestResiduoParaConferenciaHumana(unittest.TestCase):
    def test_titulo_e_detectado(self):
        self.assertTrue(tem_titulo_ou_patente("Capitão Silva"))
        self.assertTrue(tem_titulo_ou_patente("Pastor João"))
        self.assertFalse(tem_titulo_ou_patente("Ana Costa"))

    def test_sem_titulos_apenas_detecta_nao_afirma(self):
        self.assertEqual(sem_titulos("Capitão Silva"), "silva")
        self.assertEqual(sem_titulos("Silva"), "silva")

    def test_variante_com_patente_vai_para_conferencia_humana(self):
        universo = [_dep("A", "Roberto Silva", civil="Roberto Silva")]
        alvo = Alvo(nome="Capitão Silva", data_do_fato=date(2025, 6, 1))
        r = resolver(alvo, universo)
        self.assertIs(r.grau, Grau.RECUSADO)
        self.assertTrue(r.pendente_conferencia)
        self.assertIn("título ou patente", r.divergencia)


# =============================================================================
# Bijeção do código de autor de emendas (seção 6.3)
#   verificação de CONJUNTO, não de amostra
# =============================================================================

class TestBijecaoAutoria(unittest.TestCase):
    def test_bijecao_perfeita(self):
        registros = [("001", "Ana"), ("002", "Bruno"), ("001", "Ana")]
        ok, violacoes = verificar_bijecao_autoria(registros)
        self.assertTrue(ok)
        self.assertEqual(violacoes, {})

    def test_um_codigo_com_dois_nomes_viola(self):
        ok, violacoes = verificar_bijecao_autoria([("001", "Ana"), ("001", "Bruno")])
        self.assertFalse(ok)
        self.assertIn("001", violacoes)

    def test_um_nome_com_dois_codigos_viola(self):
        ok, violacoes = verificar_bijecao_autoria([("001", "Ana"), ("002", "Ana")])
        self.assertFalse(ok)
        self.assertIn("Ana", violacoes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
