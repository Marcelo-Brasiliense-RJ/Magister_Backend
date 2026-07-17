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


def test_resume_clones_template_into_new_session(client):
    # Conversa-modelo semeada no startup (seed_demo_session) para o token de matriculas.
    resp = client.post("/api/embed/tkn_9f2a7c41e0b3/session")
    assert resp.status_code == 200
    body = resp.json()
    # session_id e um uuid mintado, nunca o template reservado "demo-*".
    assert body["session_id"] and not body["session_id"].startswith("demo-")
    assert len(body["messages"]) == 4
    assert body["messages"][0]["role"] == "user"
    assert body["messages"][-1]["role"] == "assistant"


def test_resume_two_calls_return_distinct_sessions(client):
    a = client.post("/api/embed/tkn_9f2a7c41e0b3/session").json()["session_id"]
    b = client.post("/api/embed/tkn_9f2a7c41e0b3/session").json()["session_id"]
    assert a and b and a != b  # cada visitante recebe sua sessao isolada


def test_resume_session_none_when_no_demo(client, db):
    tutor = tutor_service.create_tutor(db, TutorCreate(title="Bio"))
    resp = client.post(f"/api/embed/{tutor.embed_token}/session")
    assert resp.status_code == 200
    assert resp.json() == {"session_id": None, "messages": []}
