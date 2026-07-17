"""Snippet de embed <iframe> para o widget do tutor.

O widget e servido pelo frontend em /embed?token=<embed_token>. O backend
so entrega o snippet + o token publico (nao ha segredo aqui).
"""

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.api.deps import get_session
from app.core.security import chat_rate_limiter
from app.models.conversation import ChatSession
from app.services import conversation_service as convo
from app.services import tutor_service

router = APIRouter(prefix="/api/embed", tags=["embed"])


@router.get("/{embed_token}")
def widget_config(embed_token: str, db: Session = Depends(get_session)) -> dict:
    """Config publica do widget (sem JWT): so titulo + saudacao do tutor ativo."""
    tutor = tutor_service.get_by_embed_token(db, embed_token)
    if not tutor or tutor.status != "active":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tutor indisponivel.")
    return {"title": tutor.title, "greeting": f"Olá! Sou {tutor.title}. Como posso ajudar?"}


@router.post("/{embed_token}/session")
def resume_session(
    embed_token: str, request: Request, db: Session = Depends(get_session)
) -> dict:
    """Clona a conversa-modelo numa sessao nova por visitante e a devolve.

    POST porque cria estado. O cliente nunca envia session_id (evita IDOR): o
    servidor minta um uuid e clona o template (somente leitura) para ele.
    """
    ip = request.client.host if request.client else "unknown"
    if not chat_rate_limiter.allow(f"resume:{embed_token}:{ip}"):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Muitas requisicoes. Aguarde.")
    tutor = tutor_service.get_by_embed_token(db, embed_token)
    if not tutor or tutor.status != "active":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tutor indisponivel.")
    template_id = convo.demo_session_id(embed_token)
    if not db.get(ChatSession, template_id):
        return {"session_id": None, "messages": []}  # sem sessao-modelo para este tutor
    template_msgs = convo.recent_messages(db, template_id)
    if not template_msgs:
        return {"session_id": None, "messages": []}
    session = convo.clone_session(db, tutor.id, template_msgs)
    messages = [{"role": m.role, "content": m.content} for m in template_msgs]
    return {"session_id": session.id, "messages": messages}


def build_embed_payload(embed_token: str) -> dict:
    base = os.getenv("WIDGET_BASE_URL", "http://localhost:5173")
    embed_url = f"{base}/embed?token={embed_token}"
    snippet = (
        f'<iframe src="{embed_url}" width="400" height="600" '
        f'style="border:0" title="Magister"></iframe>'
    )
    return {"embed_token": embed_token, "embed_url": embed_url, "snippet": snippet}
