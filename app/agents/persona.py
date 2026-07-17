"""No de persona: gera a resposta na voz do tutor e o no de compactacao."""

from app.agents.prompts import build_system_prompt
from app.agents.tools import summarize
from app.config import get_settings
from app.core import llm
from app.core.logging import logger

_settings = get_settings()


def compaction(state: dict) -> dict:
    """Resumo rolante: dobra os turnos antigos no summary quando a janela enche."""
    history = state.get("history", [])
    if len(history) < _settings.history_window:
        return {}
    half = len(history) // 2
    old, recent = history[:half], history[half:]
    convo = "\n".join(f"{m['role']}: {m['content']}" for m in old)
    prev = state.get("rolling_summary", "")
    text = (prev + "\n" + convo).strip()
    new_summary = summarize(text, "resuma a conversa preservando fatos e decisoes")
    return {"rolling_summary": new_summary, "history": recent}


def persona(state: dict) -> dict:
    tutor = state.get("tutor", {})
    system = build_system_prompt(
        tutor.get("system_instructions", ""),
        state.get("compiled_context", ""),
        state.get("rolling_summary", ""),
        # So instrui a emitir o marcador quando ha escalada possivel (tutor
        # tematico com fallback ligado). Senao o tutor responde por conta propria.
        escalation=bool(state.get("escalation_enabled")),
    )
    messages = [{"role": "system", "content": system}]
    messages += state.get("history", [])
    messages.append({"role": "user", "content": state.get("user_message", "")})
    text, tokens = llm.complete(messages, task="persona")
    return {"response": text, "tokens_used": state.get("tokens_used", 0) + tokens}


def reitor(state: dict) -> dict:
    """No de fallback: o Reitor responde a mesma pergunta sem fontes. Terminal (nao escala)."""
    fallback = state.get("fallback", {})
    system = build_system_prompt(
        fallback.get("system_instructions", ""),
        "",  # o Reitor nao usa fontes
        state.get("rolling_summary", ""),
    )
    messages = [{"role": "system", "content": system}]
    messages += state.get("history", [])
    messages.append({"role": "user", "content": state.get("user_message", "")})
    text, tokens = llm.complete(messages, task="persona")
    logger.info(
        "escalation",
        extra={
            "event": {
                "event": "escalation",
                "from_tutor": state.get("tutor", {}).get("title"),
                "to_tutor": fallback.get("title"),
                "session_id": state.get("session_id"),
            }
        },
    )
    return {"response": text, "tokens_used": state.get("tokens_used", 0) + tokens}
