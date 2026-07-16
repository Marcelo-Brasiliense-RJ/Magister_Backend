"""Modelo do tutor de IA (persona, instrucoes, fontes, embed token)."""

from datetime import datetime, timezone

from sqlmodel import JSON, Column, Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Tutor(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    status: str = Field(default="active")  # active | inactive
    system_instructions: str = ""
    # Fontes de conhecimento: lista de URLs (sem vector DB).
    sources: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    embed_token: str = Field(index=True, unique=True)
    # Origens permitidas para o widget; vazio = qualquer (apenas dev).
    allowed_origins: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
