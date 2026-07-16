"""Sessao de conversa e mensagens. Memoria = janela + resumo rolante."""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ChatSession(SQLModel, table=True):
    id: str = Field(primary_key=True)  # uuid gerado pelo servico
    tutor_id: int = Field(index=True, foreign_key="tutor.id")
    rolling_summary: str = ""  # resumo dos turnos antigos (summary buffer)
    token_spent: int = 0  # orcamento de tokens por sessao
    created_at: datetime = Field(default_factory=_now)


class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(index=True, foreign_key="chatsession.id")
    role: str  # user | assistant
    content: str
    created_at: datetime = Field(default_factory=_now)
