"""Teste do mapeamento ano → legislatura do backfill (fronteiras)."""

import unittest

from run_backfill import legislatura_do_ano


class TestLegislaturaDoAno(unittest.TestCase):
    def test_fronteiras(self):
        # 55ª: até 2018 · 56ª: 2019–2022 · 57ª: 2023+
        self.assertEqual(legislatura_do_ano(2018), 55)
        self.assertEqual(legislatura_do_ano(2019), 56)   # troca 55→56
        self.assertEqual(legislatura_do_ano(2022), 56)
        self.assertEqual(legislatura_do_ano(2023), 57)   # troca 56→57
        self.assertEqual(legislatura_do_ano(2026), 57)


if __name__ == "__main__":
    unittest.main(verbosity=2)
