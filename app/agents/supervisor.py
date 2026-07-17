"""No supervisor: roteia o fluxo (precisa de conhecimento? finalizar? escalar?)."""

from app.agents.prompts import ESCALATION_MARKER


def supervisor(state: dict) -> dict:
    # ponytail: heuristica barata evita chamada de LLM so para rotear.
    # Busca conhecimento quando o tutor tem fontes e a mensagem nao e trivial.
    tutor = state.get("tutor", {})
    has_sources = bool(tutor.get("sources"))
    message = state.get("user_message", "")
    needs = has_sources and len(message.strip()) > 3
    return {"needs_knowledge": needs}


def route_after_input(state: dict) -> str:
    return "end" if state.get("safety", {}).get("blocked") else "supervisor"


def route_after_supervisor(state: dict) -> str:
    return "knowledge" if state.get("needs_knowledge") else "compaction"


def route_after_persona(state: dict) -> str:
    # Escala ao Reitor so quando o tutor sinalizou (marcador), tem fallback ligado
    # e existe um tutor is_fallback. Senao segue para o guardrail (que sanitiza o
    # marcador residual). O Reitor nunca passa por aqui (guardrail_output direto).
    escalate = (
        ESCALATION_MARKER in state.get("response", "")
        and state.get("escalation_enabled")
        and state.get("fallback")
    )
    return "reitor" if escalate else "guardrail_output"
