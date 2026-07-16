from app.schemas.tutor import TutorCreate, TutorUpdate
from app.services import tutor_service


def test_create_generates_embed_token(db):
    tutor = tutor_service.create_tutor(db, TutorCreate(title="Bio", sources=["https://x.dev"]))
    assert tutor.id is not None
    assert tutor.embed_token  # nasce no servidor
    assert tutor.status == "active"
    assert tutor.sources == ["https://x.dev"]


def test_get_by_embed_token(db):
    created = tutor_service.create_tutor(db, TutorCreate(title="Mat"))
    found = tutor_service.get_by_embed_token(db, created.embed_token)
    assert found is not None and found.id == created.id


def test_update_and_status(db):
    tutor = tutor_service.create_tutor(db, TutorCreate(title="Old"))
    updated = tutor_service.update_tutor(db, tutor, TutorUpdate(title="New"))
    assert updated.title == "New"
    off = tutor_service.set_status(db, updated, "inactive")
    assert off.status == "inactive"
