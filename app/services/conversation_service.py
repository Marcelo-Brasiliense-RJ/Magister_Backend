"""Memoria de sessao: janela de N mensagens + resumo rolante + orcamento."""

import uuid

from sqlmodel import Session, desc, select

from app.config import get_settings
from app.models.conversation import ChatSession, Message

_settings = get_settings()


def get_or_create_session(db: Session, tutor_id: int, session_id: str | None) -> ChatSession:
    if session_id:
        existing = db.get(ChatSession, session_id)
        if existing and existing.tutor_id == tutor_id:
            return existing
    session = ChatSession(id=str(uuid.uuid4()), tutor_id=tutor_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def add_message(db: Session, session_id: str, role: str, content: str) -> Message:
    msg = Message(session_id=session_id, role=role, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def recent_messages(db: Session, session_id: str) -> list[Message]:
    """Ultimas HISTORY_WINDOW mensagens em ordem cronologica."""
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(desc(Message.created_at))
        .limit(_settings.history_window)
    )
    rows = list(db.exec(stmt).all())
    return list(reversed(rows))


def count_messages(db: Session, session_id: str) -> int:
    return len(list(db.exec(select(Message.id).where(Message.session_id == session_id)).all()))


def spend_tokens(db: Session, session: ChatSession, tokens: int) -> None:
    session.token_spent += tokens
    db.add(session)
    db.commit()


def budget_exceeded(session: ChatSession) -> bool:
    return session.token_spent >= _settings.max_tokens_per_session


def update_summary(db: Session, session: ChatSession, summary: str) -> None:
    session.rolling_summary = summary
    db.add(session)
    db.commit()
