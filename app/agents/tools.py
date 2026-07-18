"""Tools de conhecimento (whitelist). Sem vector DB: busca/resumo agentico.

Whitelist explicita: apenas list_sources, fetch_source, summarize. Nenhuma
tool executa comando de sistema, SQL dinamico ou acesso a outra sessao/tutor.
"""

import re

import httpx

from app.config import get_settings
from app.core import llm
from app.core.logging import logger
from app.core.security import SSRFError, assert_safe_url

_settings = get_settings()
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
# UA descritivo: sem ele, sites com politica de User-Agent (ex.: Wikipedia) respondem 403.
_USER_AGENT = "Magister/1.0 (+https://github.com/magister; tutor educacional)"


def list_sources(sources: list[str]) -> list[str]:
    """Lista as URLs de fonte configuradas para o tutor."""
    return list(sources or [])


def fetch_source(url: str) -> str:
    """Busca o conteudo textual de uma URL com SSRF guard e limite de tamanho."""
    assert_safe_url(url)  # bloqueia esquema invalido e IPs internos/metadata
    try:
        timeout = _settings.fetch_timeout_seconds
        headers = {"User-Agent": _USER_AGENT}
        with httpx.Client(timeout=timeout, follow_redirects=False, headers=headers) as client:
            with client.stream("GET", url) as resp:
                resp.raise_for_status()
                chunks: list[bytes] = []
                total = 0
                for chunk in resp.iter_bytes():
                    total += len(chunk)
                    if total > _settings.fetch_max_bytes:
                        break  # trunca respostas grandes
                    chunks.append(chunk)
    except SSRFError:
        raise
    except Exception as exc:  # noqa: BLE001 - falha de rede vira log + fonte vazia
        logger.warning("fetch_source falhou", extra={"event": {"url": url, "error": str(exc)}})
        return ""
    raw = b"".join(chunks).decode("utf-8", errors="ignore")
    text = _WS_RE.sub(" ", _TAG_RE.sub(" ", raw)).strip()
    return text[: _settings.fetch_max_bytes]


def summarize(text: str, query: str) -> str:
    """Resume o texto de uma fonte focado na pergunta do usuario (LLM barato)."""
    if not text:
        return ""
    system = "Resuma o texto abaixo focando na pergunta. Seja conciso e factual."
    prompt = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Pergunta: {query}\n\nTexto:\n{text[:6000]}"},
    ]
    summary, _ = llm.complete(prompt, task="summarize", max_output_tokens=300)
    return summary


# Whitelist: unico ponto que expoe tools ao agente.
TOOLS = {"list_sources": list_sources, "fetch_source": fetch_source, "summarize": summarize}
