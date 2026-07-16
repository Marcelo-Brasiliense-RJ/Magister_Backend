"""DTOs de tutor. Entrada do cliente nunca inclui embed_token/timestamps."""

from datetime import datetime

from pydantic import BaseModel


class TutorCreate(BaseModel):
    title: str
    system_instructions: str = ""
    sources: list[str] = []
    allowed_origins: list[str] = []


class TutorUpdate(BaseModel):
    title: str | None = None
    system_instructions: str | None = None
    sources: list[str] | None = None
    allowed_origins: list[str] | None = None


class StatusUpdate(BaseModel):
    status: str  # active | inactive


class TutorRead(BaseModel):
    id: int
    title: str
    status: str
    system_instructions: str
    sources: list[str]
    allowed_origins: list[str]
    embed_token: str
    created_at: datetime
    updated_at: datetime
