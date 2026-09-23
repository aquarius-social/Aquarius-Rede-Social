"""Teste do re-resolver de autoria de emendas — a montagem do mapa nome→perfil.

Disciplina da Metodologia (§5.2): cada regra tem um caso que ACEITA e um que
RECUSA. Aqui: casa por nome normalizado (aceita), recusa homônimo (ambíguo →
None) e desconhecido. O runner em si é I/O de banco; a lógica pura é esta.
"""
import unittest

from run_reresolver_autores_emendas import construir_lookup_parlamentar_nome


class TestLookupParlamentarNome(unittest.TestCase):
    def test_casa_por_nome_ignorando_acento_e_caixa(self):
        # A fonte (Transparência) manda SEM acento e em MAIÚSCULAS; o perfil é
        # acentuado. A `normalizar` aproxima os dois — o furo do `ilike`.
        lk = construir_lookup_parlamentar_nome([
            {"id": "P1", "nome": "João Carlos Bacelar"},
            {"id": "P2", "nome": "Zé Vitor"},
        ])
        self.assertEqual(lk("JOAO CARLOS BACELAR"), "P1")
        self.assertEqual(lk("ZE VITOR"), "P2")

    def test_recusa_homonimo(self):  # §6.3: nome que colide não se atribui
        lk = construir_lookup_parlamentar_nome([
            {"id": "P1", "nome": "José Silva"},
            {"id": "P2", "nome": "JOSE SILVA"},   # mesmo nome normalizado, outro perfil
        ])
        self.assertIsNone(lk("Jose Silva"))

    def test_recusa_desconhecido_e_vazio(self):
        lk = construir_lookup_parlamentar_nome([{"id": "P1", "nome": "Fulano"}])
        self.assertIsNone(lk("Beltrano"))
        self.assertIsNone(lk(""))


if __name__ == "__main__":
    unittest.main()
