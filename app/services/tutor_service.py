"""Regras de negocio de tutores. Embed token e derivados nascem no servidor."""

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.core.security import generate_embed_token
from app.models.tutor import Tutor
from app.schemas.tutor import TutorCreate, TutorUpdate


def create_tutor(db: Session, data: TutorCreate) -> Tutor:
    tutor = Tutor(
        title=data.title,
        description=data.description,
        system_instructions=data.system_instructions,
        sources=data.sources,
        allowed_origins=data.allowed_origins,
        fallback_enabled=data.fallback_enabled,
        embed_token=generate_embed_token(),
    )
    db.add(tutor)
    db.commit()
    db.refresh(tutor)
    return tutor


def list_tutors(db: Session) -> list[Tutor]:
    return list(db.exec(select(Tutor)).all())


def get_tutor(db: Session, tutor_id: int) -> Tutor | None:
    return db.get(Tutor, tutor_id)


def get_by_embed_token(db: Session, token: str) -> Tutor | None:
    return db.exec(select(Tutor).where(Tutor.embed_token == token)).first()


def get_fallback_tutor(db: Session) -> Tutor | None:
    """O Reitor (is_fallback=True). No maximo um; retorna o primeiro ativo."""
    return db.exec(
        select(Tutor).where(Tutor.is_fallback.is_(True), Tutor.status == "active")
    ).first()


def update_tutor(db: Session, tutor: Tutor, data: TutorUpdate) -> Tutor:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tutor, field, value)
    tutor.updated_at = datetime.now(timezone.utc)
    db.add(tutor)
    db.commit()
    db.refresh(tutor)
    return tutor


def set_status(db: Session, tutor: Tutor, status: str) -> Tutor:
    tutor.status = status
    tutor.updated_at = datetime.now(timezone.utc)
    db.add(tutor)
    db.commit()
    db.refresh(tutor)
    return tutor
