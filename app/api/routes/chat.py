"""Rota de chat do widget: valida embed token/origem, aplica limites, faz SSE.

O cliente envia apenas embed_token + message (+ session_id). Identidade,
instrucoes, fontes e limites sao resolvidos no servidor (nunca confiar no front).
"""

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session
from sse_starlette.sse import EventSourceResponse

from app.agents.graph import graph
from app.api.deps import get_session
from app.config import get_settings
from app.core.logging import logger
from app.core.security import chat_rate_limiter
from app.schemas.chat import ChatRequest
from app.services import conversation_service as convo
from app.services import tutor_service

router = APIRouter(prefix="/api", tags=["chat"])
_settings = get_settings()

BUDGET_MSG = "Limite de uso desta conversa atingido. Inicie uma nova sessao."


def _origin_allowed(origin: str | None, allowed: list[str]) -> bool:
    if not allowed:
        return True  # sem restricao configurada (apenas dev)
    return origin in allowed


@router.post("/chat")
async def chat(body: ChatRequest, request: Request, db: Session = Depends(get_session)):
    ip = request.client.host if request.client else "unknown"
    # Rate limit por embed token + IP na rota cara antes de qualquer trabalho.
    if not chat_rate_limiter.allow(f"{body.embed_token}:{ip}"):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Muitas mensagens. Aguarde.")

    tutor = tutor_service.get_by_embed_token(db, body.embed_token)
    if not tutor or tutor.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tutor indisponivel.")
    if not _origin_allowed(request.headers.get("origin"), tutor.allowed_origins):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Origem nao permitida.")

    session = convo.get_or_create_session(db, tutor.id, body.session_id)

    # Orcamento de tokens por sessao: resposta graciosa, sem chamar o LLM.
    if convo.budget_exceeded(session):
        logger.warning("budget exceeded", extra={"event": {"session": session.id}})
        return EventSourceResponse(_stream_error("limit_reached", BUDGET_MSG))

    convo.add_message(db, session.id, "user", body.message)
    history = [
        {"role": m.role, "content": m.content}
        for m in convo.recent_messages(db, session.id)
        if not (m.role == "user" and m.content == body.message)
    ]
    state = {
        "tutor": {
            "system_instructions": tutor.system_instructions,
            "sources": tutor.sources,
            "title": tutor.title,
        },
        "user_message": body.message,
        "history": history,
        "rolling_summary": session.rolling_summary,
        "tokens_used": 0,
    }
    # graph.invoke e sincrono/CPU+IO; roda fora do event loop.
    result = await asyncio.to_thread(graph.invoke, state)

    answer = result.get("response", "")
    convo.add_message(db, session.id, "assistant", answer)
    convo.spend_tokens(db, session, result.get("tokens_used", 0))
    if result.get("rolling_summary") and result["rolling_summary"] != session.rolling_summary:
        convo.update_summary(db, session, result["rolling_summary"])

    return EventSourceResponse(_stream_text(answer, session.id))


async def _stream_text(text: str, session_id: str):
    # ponytail: entrega o texto ja gerado em blocos via SSE. Streaming token a token
    # direto do modelo fica como proximo passo (o transporte SSE ja esta pronto).
    # Cada frame carrega JSON no campo data: (o front le so o data: e faz JSON.parse).
    yield {"data": json.dumps({"type": "session", "session_id": str(session_id)})}
    for word in text.split(" "):
        yield {"data": json.dumps({"type": "token", "content": word + " "})}
        await asyncio.sleep(0)
    yield {"data": json.dumps({"type": "done"})}


async def _stream_error(code: str, message: str):
    yield {"data": json.dumps({"type": "error", "code": code, "message": message})}
