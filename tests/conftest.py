"""Fixtures de teste. Configura env ANTES de importar a app (settings cacheado)."""

import os
import tempfile

import bcrypt

# Segredos/config de teste (nunca reais). Definidos antes de qualquer import da app.
_DB = os.path.join(tempfile.gettempdir(), "magister_test.db")
os.environ.update(
    {
        "APP_ENV": "test",
        "JWT_SECRET": "test-secret",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD_HASH": bcrypt.hashpw(b"secret", bcrypt.gensalt()).decode(),
        "DATABASE_URL": f"sqlite:///{_DB}",
        "CHAT_RATE_LIMIT_PER_MIN": "20",
        "MAX_TOKENS_PER_SESSION": "1000",
        "LLM_PROVIDERS": (
            '[{"name":"groq","base_url":"http://groq","api_key":"k1","model":"m-groq","priority":1},'
            '{"name":"openrouter","base_url":"http://or","api_key":"k2","model":"m-or","priority":2}]'
        ),
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402

from app.database import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_db():
    # Isolamento: recria o schema a cada teste.
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield


@pytest.fixture
def db():
    with Session(engine) as session:
        yield session


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_token(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "secret"})
    return resp.json()["access_token"]
