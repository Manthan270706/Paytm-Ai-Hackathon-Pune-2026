import uuid
from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """LangGraph agent execution state for OpsSaathi AI."""

    # Session & Identity
    conversation_id: uuid.UUID
    run_id: uuid.UUID
    merchant_id: uuid.UUID
    user_id: uuid.UUID | None
    language: str

    # Merchant input & sanitization
    input_text: str
    sanitized_input: str
    extracted_entities: dict[str, Any]
    intent: str

    # Investigation & Reconciliation
    merchant_context: dict[str, Any]
    investigation_data: dict[str, Any]
    reconciliation_summary: dict[str, Any]

    # Policy evaluation: {"decision": "ALLOW"|"REQUIRE_APPROVAL"|"DENY", "reason": str}
    policy_evaluation: dict[str, Any]
    active_case_id: uuid.UUID | None
    case_version: int | None
    action_hash: str | None

    # Tool Execution
    tool_name: str | None
    tool_input: dict[str, Any] | None
    tool_output: dict[str, Any] | None
    action_verification: dict[str, Any] | None
    timeline_updated: bool

    # Communication & Resolution
    final_reply: str
    resolution_status: str  # "PASS" | "FAIL" | "PENDING"
    trace_events: list[dict[str, Any]]
    error: str | None
    status: str  # "RUNNING" | "COMPLETED" | "AWAITING_APPROVAL" | "FAILED"
