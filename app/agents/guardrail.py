"""Nos de guardrail: valida entrada (anti prompt-injection) e saida."""

import re

# Padroes de prompt-injection na entrada. Deteccao barata antes de gastar LLM.
_INJECTION_PATTERNS = [
    r"ignore.*(instru|regras|prompt)",
    r"esque[cç]a.*(instru|regras)",
    r"(system|sistema)\s*prompt",
    r"modo\s+desenvolvedor",
    r"developer\s+mode",
    r"sem\s+restri[cç]",
    r"(revele|mostre|repita|imprima).*(prompt|regras|instru|token|chave)",
    r"you\s+are\s+now",
    r"voc[eê]\s+agora\s+[eé]",
    r"jailbreak",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

REFUSAL = "Desculpe, so posso ajudar com o tema configurado para este tutor."


def guardrail_input(state: dict) -> dict:
    if _INJECTION_RE.search(state.get("user_message", "")):
        return {"safety": {"blocked": True, "reason": "injection"}, "response": REFUSAL}
    return {"safety": {"blocked": False}}


def guardrail_output(state: dict) -> dict:
    text = state.get("response", "")
    # Trava vazamento do bloco de seguranca caso o modelo tente reproduzi-lo.
    if "REGRAS DE SEGURANCA" in text:
        return {"response": REFUSAL}
    return {}
