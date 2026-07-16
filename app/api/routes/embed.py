"""Snippet de embed <iframe> para o widget do tutor.

O widget e servido pelo frontend em /embed?token=<embed_token>. O backend
so entrega o snippet + o token publico (nao ha segredo aqui).
"""

import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.api.deps import get_session
from app.services import tutor_service

router = APIRouter(prefix="/api/embed", tags=["embed"])


@router.get("/{embed_token}")
def widget_config(embed_token: str, db: Session = Depends(get_session)) -> dict:
    """Config publica do widget (sem JWT): so titulo + saudacao do tutor ativo."""
    tutor = tutor_service.get_by_embed_token(db, embed_token)
    if not tutor or tutor.status != "active":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tutor indisponivel.")
    return {"title": tutor.title, "greeting": f"Olá! Sou {tutor.title}. Como posso ajudar?"}


def build_embed_payload(embed_token: str) -> dict:
    base = os.getenv("WIDGET_BASE_URL", "http://localhost:5173")
    embed_url = f"{base}/embed?token={embed_token}"
    snippet = (
        f'<iframe src="{embed_url}" width="400" height="600" '
        f'style="border:0" title="Magister"></iframe>'
    )
    return {"embed_token": embed_token, "embed_url": embed_url, "snippet": snippet}
