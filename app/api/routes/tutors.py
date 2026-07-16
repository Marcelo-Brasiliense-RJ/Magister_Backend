"""CRUD de tutores (protegido por JWT admin) + status + snippet de embed."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.api.deps import get_session, require_admin
from app.api.routes.embed import build_embed_payload
from app.schemas.tutor import StatusUpdate, TutorCreate, TutorRead, TutorUpdate
from app.services import tutor_service

router = APIRouter(prefix="/api/tutors", tags=["tutors"], dependencies=[Depends(require_admin)])


def _get_or_404(db: Session, tutor_id: int):
    tutor = tutor_service.get_tutor(db, tutor_id)
    if not tutor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tutor nao encontrado.")
    return tutor


@router.post("", response_model=TutorRead, status_code=201)
def create(body: TutorCreate, db: Session = Depends(get_session)) -> TutorRead:
    return tutor_service.create_tutor(db, body)


@router.get("", response_model=list[TutorRead])
def list_all(db: Session = Depends(get_session)) -> list[TutorRead]:
    return tutor_service.list_tutors(db)


@router.get("/{tutor_id}", response_model=TutorRead)
def get_one(tutor_id: int, db: Session = Depends(get_session)) -> TutorRead:
    return _get_or_404(db, tutor_id)


@router.put("/{tutor_id}", response_model=TutorRead)
def update(tutor_id: int, body: TutorUpdate, db: Session = Depends(get_session)) -> TutorRead:
    return tutor_service.update_tutor(db, _get_or_404(db, tutor_id), body)


@router.patch("/{tutor_id}/status", response_model=TutorRead)
def patch_status(
    tutor_id: int, body: StatusUpdate, db: Session = Depends(get_session)
) -> TutorRead:
    if body.status not in ("active", "inactive"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "status invalido.")
    return tutor_service.set_status(db, _get_or_404(db, tutor_id), body.status)


@router.get("/{tutor_id}/embed")
def embed(tutor_id: int, db: Session = Depends(get_session)) -> dict:
    return build_embed_payload(_get_or_404(db, tutor_id).embed_token)
