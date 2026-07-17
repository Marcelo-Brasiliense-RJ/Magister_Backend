import pytest

from app.core import llm


def test_failover_to_next_provider(monkeypatch):
    calls = []

    def fake_call(provider, model, messages, max_output_tokens):
        calls.append(provider["name"])
        if provider["name"] == "groq":
            exc = RuntimeError("rate limited")
            exc.status_code = 429  # provedor primario satura
            raise exc
        return "ok do fallback", 12

    monkeypatch.setattr(llm, "_call", fake_call)
    text, tokens = llm.complete([{"role": "user", "content": "oi"}])
    assert text == "ok do fallback"
    assert tokens == 12
    assert calls == ["groq", "openrouter"]  # tentou o barato primeiro


def test_all_providers_fail_raises(monkeypatch):
    def always_fail(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(llm, "_call", always_fail)
    with pytest.raises(llm.LLMError):
        llm.complete([{"role": "user", "content": "oi"}])


def test_task_model_override(monkeypatch):
    seen = {}

    def fake_call(provider, model, messages, max_output_tokens):
        seen["model"] = model
        return "x", 1

    monkeypatch.setattr(llm, "_call", fake_call)
    monkeypatch.setattr(llm._settings, "llm_task_models", {"summarize": "modelo-barato"})
    llm.complete([{"role": "user", "content": "oi"}], task="summarize")
    assert seen["model"] == "modelo-barato"


def test_per_provider_task_model_survives_failover(monkeypatch):
    # O id do modelo forte difere entre provedores; no failover cada um deve usar o seu.
    seen = []

    def fake_call(provider, model, messages, max_output_tokens):
        seen.append((provider["name"], model))
        if provider["name"] == "groq":
            raise RuntimeError("down")  # forca cair no fallback
        return "x", 1

    providers = [
        {"name": "groq", "base_url": "http://g", "api_key": "k",
         "model": "8b-groq", "task_models": {"persona": "70b-groq"}, "priority": 1},
        {"name": "openrouter", "base_url": "http://o", "api_key": "k",
         "model": "8b-or", "task_models": {"persona": "70b-or"}, "priority": 2},
    ]
    monkeypatch.setattr(llm._settings, "llm_providers", providers)
    monkeypatch.setattr(llm, "_call", fake_call)
    llm.complete([{"role": "user", "content": "oi"}], task="persona")
    assert seen == [("groq", "70b-groq"), ("openrouter", "70b-or")]
