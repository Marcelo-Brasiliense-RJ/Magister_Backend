"""Nos de guardrail: valida entrada (anti prompt-injection) e saida."""

import re

from app.agents.prompts import ESCALATION_MARKER

# Fallback textual honesto quando o marcador aparece sem Reitor para assumir.
HONEST_FALLBACK = (
    "Nao tenho essa informacao confirmada. Recomendo procurar a secretaria "
    "academica ou o setor responsavel."
)

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
    # Chokepoint unico: o marcador de escalada nunca pode vazar ao usuario (sem
    # Reitor disponivel, vira "nao sei" honesto). Cobre todos os caminhos do grafo.
    if ESCALATION_MARKER in text:
        return {"response": HONEST_FALLBACK}
    return {}
