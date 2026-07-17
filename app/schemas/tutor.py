"""DTOs de tutor. Entrada do cliente nunca inclui embed_token/timestamps."""

from datetime import datetime

from pydantic import BaseModel


class TutorCreate(BaseModel):
    title: str
    description: str = ""
    system_instructions: str = ""
    sources: list[str] = []
    allowed_origins: list[str] = []
    fallback_enabled: bool = True


class TutorUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    system_instructions: str | None = None
    sources: list[str] | None = None
    allowed_origins: list[str] | None = None
    # is_fallback nao entra aqui: definido no seed, nao editavel pela API.
    fallback_enabled: bool | None = None


class StatusUpdate(BaseModel):
    status: str  # active | inactive


class TutorRead(BaseModel):
    id: int
    title: str
    description: str
    status: str
    system_instructions: str
    sources: list[str]
    allowed_origins: list[str]
    is_fallback: bool
    fallback_enabled: bool
    embed_token: str
    created_at: datetime
    updated_at: datetime
