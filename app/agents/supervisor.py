"""No supervisor: roteia o fluxo (precisa de conhecimento? finalizar?)."""


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
