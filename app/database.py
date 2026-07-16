"""Engine e sessao SQLite via SQLModel."""

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

_settings = get_settings()
# check_same_thread=False: SQLite acessado por varias threads do FastAPI/testes.
engine = create_engine(
    _settings.database_url,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    # Import tardio garante que os modelos estejam registrados no metadata.
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
