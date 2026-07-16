"""Rota publica de config do widget (sem JWT)."""

from app.schemas.tutor import TutorCreate
from app.services import tutor_service


def test_widget_config_active(client, db):
    tutor = tutor_service.create_tutor(db, TutorCreate(title="Bio"))
    resp = client.get(f"/api/embed/{tutor.embed_token}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Bio"
    assert "Bio" in body["greeting"]


def test_widget_config_inactive_404(client, db):
    tutor = tutor_service.create_tutor(db, TutorCreate(title="Bio"))
    tutor_service.set_status(db, tutor, "inactive")
    assert client.get(f"/api/embed/{tutor.embed_token}").status_code == 404


def test_widget_config_unknown_404(client):
    assert client.get("/api/embed/nao-existe").status_code == 404
