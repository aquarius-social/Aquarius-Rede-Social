"""Endpoint HTTP do Prometeus (face de chat). Um POST /perguntar roda o agente.

Cola fina sobre o agente (que já está testado em agente.py). Requer, em execução:
fastapi + uvicorn + anthropic + httpx, e as variáveis SUPABASE_URL /
SUPABASE_ANON_KEY / ANTHROPIC_API_KEY. Não é exercido pela suíte.

Subir local:  uvicorn api:app --reload
"""
from __future__ import annotations

from dataclasses import asdict

_agente = None


def _obter_agente():
    """Cria o agente uma vez (lazy) — assim importar este módulo não exige a chave."""
    global _agente
    if _agente is None:
        from agente import Agente
        from modelo import ModeloClaude
        from supabase_gateway import SupabaseGateway

        _agente = Agente(ModeloClaude(), SupabaseGateway())
    return _agente


def criar_app():
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel

    app = FastAPI(title="Prometeus — Congresso Nacional")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://aquarius-rede-social-app.vercel.app",
            "http://localhost:8081",   # Expo web (dev)
            "http://localhost:19006",  # Expo web (dev, legado)
        ],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    class Pergunta(BaseModel):
        pergunta: str

    @app.get("/saude")
    def saude():
        return {"ok": True, "servico": "prometeus"}

    @app.post("/perguntar")
    def perguntar(p: Pergunta):
        return asdict(_obter_agente().responder(p.pergunta))

    return app


app = criar_app()
