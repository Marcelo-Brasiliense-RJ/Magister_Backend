"""No de conhecimento: usa as tools (whitelist) sobre as fontes do tutor."""

from app.agents.tools import fetch_source, list_sources, summarize
from app.config import get_settings
from app.core.security import SSRFError

_settings = get_settings()
_MAX_SOURCES = 3  # limita custo/tempo por turno


def knowledge(state: dict) -> dict:
    tutor = state.get("tutor", {})
    query = state.get("user_message", "")
    sources = list_sources(tutor.get("sources", []))[:_MAX_SOURCES]
    parts: list[str] = []
    for url in sources:
        try:
            content = fetch_source(url)
        except SSRFError:
            continue  # fonte interna bloqueada; ignora e segue
        if content:
            parts.append(f"Fonte {url}:\n{summarize(content, query)}")
    return {"compiled_context": "\n\n".join(parts)}
