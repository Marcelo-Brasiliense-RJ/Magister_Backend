"""Escalada ao Reitor no grafo, com LLM mockado (sem rede).

O mock discrimina pelo system prompt: a persona do tutor tematico recebe a
instrucao com o marcador, entao "so sabe escalar" (retorna o marcador); o Reitor
nao recebe instrucao, entao responde normal.
"""

import json

import pytest
from sqlmodel import select

from app.agents import persona
from app.agents.guardrail import HONEST_FALLBACK
from app.agents.prompts import ESCALATION_MARKER
from app.core import llm
from app.models.tutor import Tutor
from app.schemas.tutor import TutorCreate
from app.services import tutor_service


def _parse_sse(text: str) -> list[dict]:
    return [
        json.loads(line[len("data:"):].strip())
        for line in text.splitlines()
        if line.startswith("data:")
    ]


def _answer(resp) -> str:
    events = _parse_sse(resp.text)
    return "".join(e["content"] for e in events if e["type"] == "token")


@pytest.fixture
def escalating_llm(monkeypatch):
    """Persona tematica escala (marcador); Reitor responde normal."""
    calls = []

    def fake_complete(messages, task="persona", max_output_tokens=None):
        calls.append(task)
        system = messages[0]["content"]
        if ESCALATION_MARKER in system:  # tutor tematico instruido a escalar
            return ESCALATION_MARKER, 5
        return "RESPOSTA DO REITOR", 8

    monkeypatch.setattr(llm, "complete", fake_complete)
    monkeypatch.setattr(persona.llm, "complete", fake_complete)
    return calls


@pytest.fixture
def always_marker_llm(monkeypatch):
    """Qualquer persona (inclusive o Reitor) emite o marcador."""
    calls = []

    def fake_complete(messages, task="persona", max_output_tokens=None):
        calls.append(task)
        return ESCALATION_MARKER, 5

    monkeypatch.setattr(llm, "complete", fake_complete)
    monkeypatch.setattr(persona.llm, "complete", fake_complete)
    return calls


def _make_fallback(db) -> Tutor:
    # is_fallback nao vem por create_tutor (nao editavel pela API); insere direto.
    fb = Tutor(
        title="Reitor",
        system_instructions="Sou o Reitor, fallback da plataforma.",
        embed_token="tok-reitor",
        is_fallback=True,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


def test_escalates_when_marker_and_fallback(client, db, escalating_llm):
    _make_fallback(db)
    thematic = tutor_service.create_tutor(db, TutorCreate(title="Matriculas"))
    resp = client.post("/api/chat", json={"embed_token": thematic.embed_token, "message": "algo"})
    assert resp.status_code == 200
    answer = _answer(resp)
    assert escalating_llm == ["persona", "persona"]  # persona tematica + no reitor
    assert "RESPOSTA DO REITOR" in answer
    assert ESCALATION_MARKER not in answer


def test_no_escalation_when_fallback_disabled(client, db, escalating_llm):
    _make_fallback(db)
    thematic = tutor_service.create_tutor(
        db, TutorCreate(title="Matriculas", fallback_enabled=False)
    )
    resp = client.post("/api/chat", json={"embed_token": thematic.embed_token, "message": "algo"})
    assert resp.status_code == 200
    answer = _answer(resp)
    assert escalating_llm == ["persona"]  # sem no reitor
    assert ESCALATION_MARKER not in answer  # sem instrucao, o tutor nao emite marcador


def test_reitor_is_terminal_and_marker_never_leaks(client, db, always_marker_llm):
    # Ate o Reitor emitindo o marcador: a aresta reitor->guardrail_output nao reescala
    # e o guardrail troca o marcador residual por texto honesto.
    _make_fallback(db)
    thematic = tutor_service.create_tutor(db, TutorCreate(title="Matriculas"))
    resp = client.post("/api/chat", json={"embed_token": thematic.embed_token, "message": "algo"})
    assert resp.status_code == 200
    answer = _answer(resp)
    assert always_marker_llm == ["persona", "persona"]  # exatamente 2: sem loop no reitor
    assert ESCALATION_MARKER not in answer
    assert HONEST_FALLBACK in answer


def test_marker_never_leaks_without_fallback(client, db, escalating_llm):
    # Tutor tematico com fallback ligado, mas nenhum tutor is_fallback cadastrado.
    # O seed cria o Reitor no startup; remove-o para simular a ausencia de fallback.
    for t in db.exec(select(Tutor).where(Tutor.is_fallback.is_(True))).all():
        db.delete(t)
    db.commit()
    thematic = tutor_service.create_tutor(db, TutorCreate(title="Matriculas"))
    resp = client.post("/api/chat", json={"embed_token": thematic.embed_token, "message": "algo"})
    assert resp.status_code == 200
    answer = _answer(resp)
    assert escalating_llm == ["persona"]  # sem no reitor (nao ha fallback)
    assert ESCALATION_MARKER not in answer
    assert HONEST_FALLBACK in answer
