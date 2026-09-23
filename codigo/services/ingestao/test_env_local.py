"""Testes do carregador de `.env` (disciplina §5.2: um caso aceita, um recusa)."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from env_local import carregar_env


class TestCarregarEnv(unittest.TestCase):
    def _escrever(self, texto: str) -> Path:
        p = Path(tempfile.mkdtemp()) / ".env"
        p.write_text(texto, encoding="utf-8")
        return p

    def test_le_pares_ignora_comentarios_e_remove_aspas(self):
        for k in ("ZZ_URL", "ZZ_KEY"):
            os.environ.pop(k, None)
        p = self._escrever(
            "# comentário não vira chave\n"
            "\n"
            "ZZ_URL=https://exemplo.supabase.co\n"
            'ZZ_KEY="uma-chave-secreta"\n'
        )
        lidos = carregar_env(p)
        self.assertEqual(lidos["ZZ_URL"], "https://exemplo.supabase.co")
        self.assertEqual(os.environ["ZZ_URL"], "https://exemplo.supabase.co")
        self.assertEqual(os.environ["ZZ_KEY"], "uma-chave-secreta")  # aspas removidas
        self.assertNotIn("# comentário não vira chave", lidos)
        for k in ("ZZ_URL", "ZZ_KEY"):
            os.environ.pop(k, None)

    def test_nao_sobrescreve_ambiente_existente(self):
        # O ambiente real manda — comportamento do qual o CI depende (recusa a
        # sobrescrever). Sem isto, um .env esquecido mascararia o segredo do CI.
        os.environ["ZZ_EXISTENTE"] = "do-ambiente"
        p = self._escrever("ZZ_EXISTENTE=do-arquivo\n")
        lidos = carregar_env(p)
        self.assertEqual(lidos["ZZ_EXISTENTE"], "do-arquivo")      # leu do arquivo
        self.assertEqual(os.environ["ZZ_EXISTENTE"], "do-ambiente")  # mas não trocou
        os.environ.pop("ZZ_EXISTENTE", None)

    def test_arquivo_ausente_e_noop(self):
        ausente = Path(tempfile.mkdtemp()) / "nao-existe.env"
        self.assertEqual(carregar_env(ausente), {})


if __name__ == "__main__":
    unittest.main()
