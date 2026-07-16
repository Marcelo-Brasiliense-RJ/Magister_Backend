"""StateGraph LangGraph: Supervisor + Knowledge + Persona + Guardrail + compactacao.

Fluxo: guardrail_input -> supervisor -> [knowledge?] -> compaction -> persona
-> guardrail_output. Arestas condicionais decidem bloqueio e busca de contexto.
"""

from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agents.guardrail import guardrail_input, guardrail_output
from app.agents.knowledge import knowledge
from app.agents.persona import compaction, persona
from app.agents.supervisor import route_after_input, route_after_supervisor, supervisor


class AgentState(TypedDict, total=False):
    tutor: dict
    user_message: str
    history: list[dict]
    rolling_summary: str
    compiled_context: str
    needs_knowledge: bool
    response: str
    tokens_used: int
    safety: dict


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("guardrail_input", guardrail_input)
    g.add_node("supervisor", supervisor)
    g.add_node("knowledge", knowledge)
    g.add_node("compaction", compaction)
    g.add_node("persona", persona)
    g.add_node("guardrail_output", guardrail_output)

    g.set_entry_point("guardrail_input")
    g.add_conditional_edges(
        "guardrail_input", route_after_input, {"end": END, "supervisor": "supervisor"}
    )
    g.add_conditional_edges(
        "supervisor", route_after_supervisor, {"knowledge": "knowledge", "compaction": "compaction"}
    )
    g.add_edge("knowledge", "compaction")
    g.add_edge("compaction", "persona")
    g.add_edge("persona", "guardrail_output")
    g.add_edge("guardrail_output", END)
    return g.compile()


graph = build_graph()
