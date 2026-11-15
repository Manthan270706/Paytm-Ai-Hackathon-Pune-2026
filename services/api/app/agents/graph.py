from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    authenticate_session,
    classify_issue,
    collect_issue,
    communicate,
    evaluate_policy,
    execute_tool,
    investigate,
    load_merchant_context,
    prepare_evidence_summary,
    reconcile_deterministically,
    sanitize_input,
    update_case_timeline,
    verify_action,
    verify_resolution,
)
from app.agents.state import AgentState


def route_after_policy(state: AgentState) -> str:
    policy = state.get("policy_evaluation", {})
    if policy.get("decision") in {"DENY", "NO_ACTION"}:
        return "communicate"
    return "execute_tool"


def build_agent_graph(checkpointer: Any | None = None) -> Any:
    """Builds and compiles the OpsSaathi PRD §7.2 LangGraph workflow."""
    workflow = StateGraph(AgentState)

    # Register all nodes
    workflow.add_node("authenticate_session", authenticate_session)
    workflow.add_node("sanitize_input", sanitize_input)
    workflow.add_node("collect_issue", collect_issue)
    workflow.add_node("classify_issue", classify_issue)
    workflow.add_node("load_merchant_context", load_merchant_context)
    workflow.add_node("investigate", investigate)
    workflow.add_node("reconcile_deterministically", reconcile_deterministically)
    workflow.add_node("prepare_evidence_summary", prepare_evidence_summary)
    workflow.add_node("evaluate_policy", evaluate_policy)
    workflow.add_node("execute_tool", execute_tool)
    workflow.add_node("verify_action", verify_action)
    workflow.add_node("update_case_timeline", update_case_timeline)
    workflow.add_node("communicate", communicate)
    workflow.add_node("verify_resolution", verify_resolution)

    # Connect workflow edges
    workflow.add_edge(START, "authenticate_session")
    workflow.add_edge("authenticate_session", "sanitize_input")
    workflow.add_edge("sanitize_input", "collect_issue")
    workflow.add_edge("collect_issue", "classify_issue")
    workflow.add_edge("classify_issue", "load_merchant_context")
    workflow.add_edge("load_merchant_context", "investigate")
    workflow.add_edge("investigate", "reconcile_deterministically")
    workflow.add_edge("reconcile_deterministically", "prepare_evidence_summary")
    workflow.add_edge("prepare_evidence_summary", "evaluate_policy")

    # Policy decision branch
    workflow.add_conditional_edges(
        "evaluate_policy",
        route_after_policy,
        {
            "execute_tool": "execute_tool",
            "communicate": "communicate",
        },
    )

    workflow.add_edge("execute_tool", "verify_action")
    workflow.add_edge("verify_action", "update_case_timeline")
    workflow.add_edge("update_case_timeline", "communicate")
    workflow.add_edge("communicate", "verify_resolution")
    workflow.add_edge("verify_resolution", END)

    cp = checkpointer if checkpointer is not None else MemorySaver()
    return workflow.compile(checkpointer=cp)


# Pre-compiled default graph instance
agent_graph = build_agent_graph()
