"""Router de LLM por custo: Groq -> OpenRouter, failover e rotacao de chaves.

Provedores vem de settings.llm_providers (JSON no .env), ordenados por
`priority` (menor = mais barato/primeiro). Modelo por tarefa via
settings.llm_task_models (ex.: guardrail barato, persona mais forte).
"""

from itertools import count

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.core.logging import logger

_settings = get_settings()
# Contadores de rotacao de chave por provedor (round-robin).
_key_cursor: dict[str, count] = {}


class LLMError(RuntimeError):
    """Todos os provedores falharam."""


def _providers() -> list[dict]:
    return sorted(_settings.llm_providers, key=lambda p: p.get("priority", 99))


def _pick_key(provider: dict) -> str:
    # api_key pode ter varias chaves separadas por virgula (diluir free tier).
    keys = [k.strip() for k in str(provider.get("api_key", "")).split(",") if k.strip()]
    if not keys:
        return ""
    cursor = _key_cursor.setdefault(provider["name"], count())
    return keys[next(cursor) % len(keys)]


def _to_lc_messages(messages: list[dict]):
    role_map = {"system": SystemMessage, "user": HumanMessage, "assistant": AIMessage}
    return [role_map.get(m["role"], HumanMessage)(content=m["content"]) for m in messages]


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _call(
    provider: dict, model: str, messages: list[dict], max_output_tokens: int
) -> tuple[str, int]:
    """Chama um provedor unico. Ponto de injecao para mock nos testes."""
    client = ChatOpenAI(
        model=model,
        base_url=provider["base_url"],
        api_key=_pick_key(provider) or "missing",
        max_tokens=max_output_tokens,
        temperature=0.3,
    )
    resp = client.invoke(_to_lc_messages(messages))
    text = resp.content if isinstance(resp.content, str) else str(resp.content)
    usage = getattr(resp, "usage_metadata", None) or {}
    tokens = usage.get("total_tokens") or _estimate_tokens(text)
    return text, tokens


def complete(
    messages: list[dict], task: str = "persona", max_output_tokens: int | None = None
) -> tuple[str, int]:
    """Retorna (texto, tokens_usados) tentando provedores em ordem de custo."""
    providers = _providers()
    if not providers:
        raise LLMError("Nenhum provedor de LLM configurado (LLM_PROVIDERS).")
    max_out = max_output_tokens or _settings.max_output_tokens
    last_error: Exception | None = None
    for provider in providers:
        # Modelo por tarefa: override do provedor primeiro (ids diferem entre
        # provedores, ex.: 70B no Groq vs OpenRouter), depois mapa global, senao
        # o modelo padrao do provedor. Mantem o failover funcionando por tarefa.
        model = (
            provider.get("task_models", {}).get(task)
            or _settings.llm_task_models.get(task)
            or provider["model"]
        )
        try:
            text, tokens = _call(provider, model, messages, max_out)
            logger.info(
                "llm ok",
                extra={
                    "event": {
                        "provider": provider["name"],
                        "model": model,
                        "task": task,
                        "tokens": tokens,
                    }
                },
            )
            return text, tokens
        except Exception as exc:  # noqa: BLE001 - failover proposital
            last_error = exc
            status = getattr(exc, "status_code", None)
            logger.warning(
                "llm failover",
                extra={
                    "event": {
                        "provider": provider["name"],
                        "task": task,
                        "status": status,
                        "error": str(exc),
                    }
                },
            )
            continue
    raise LLMError("Todos os provedores de LLM falharam.") from last_error
