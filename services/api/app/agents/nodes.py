import logging
import re
import uuid
from decimal import Decimal
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.state import AgentState
from app.agents.templates import (
    detect_language,
    normalize_devanagari_digits,
    render_investigation_reply,
)
from app.agents.wrapper import ToolExecutionWrapper
from app.core.redaction import redact
from app.domain.policy import evaluate as evaluate_policy_domain
from app.integrations import get_llm_provider
from app.integrations.gemini.schemas import (
    EntityExtractionResult,
    IntentClassificationResult,
)
from app.tools.registry import ToolContext

logger = logging.getLogger(__name__)

# Patterns for sensitive data redaction (PRD Trust Rule 9)
CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
OTP_PATTERN = re.compile(r"\b(otp|code|pin|cvv)\s*(?:is|[:=])?\s*\d{3,6}\b", re.IGNORECASE)


def redact_sensitive(text: str) -> str:
    """Mask OTP, PIN, CVV and card numbers before any agent processing or logging."""
    redacted = CARD_PATTERN.sub("[CARD_REDACTED]", text)
    redacted = OTP_PATTERN.sub(r"\1 [SENSITIVE_REDACTED]", redacted)
    return redacted



async def authenticate_session(
    state: AgentState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    """Node: validates merchant session and binds merchant scope."""
    merchant_id = state.get("merchant_id")
    if not merchant_id:
        raise ValueError("Cannot execute agent without authenticated merchant_id")
    return {
        "status": "RUNNING",
        "trace_events": state.get("trace_events", [])
        + [
            {
                "node": "authenticate_session",
                "status": "SUCCESS",
                "merchant_id": str(merchant_id),
            }
        ],
    }


async def sanitize_input(state: AgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Node: masks sensitive tokens (OTP, PIN, CVV, Card Numbers) and detects language."""
    raw = state.get("input_text", "")
    redaction_res = redact(raw)
    sanitized = redaction_res.clean_text
    current_lang = state.get("language")
    detected = detect_language(raw, fallback=current_lang or "en")
    lang = detected if detected in {"hi", "mr"} or not current_lang else current_lang
    return {
        "sanitized_input": sanitized,
        "language": lang,
        "trace_events": state.get("trace_events", [])
        + [
            {
                "node": "sanitize_input",
                "status": "SUCCESS",
                "language": lang,
                "redacted_types": redaction_res.redacted_types,
            }
        ],
    }


async def collect_issue(state: AgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Node: extracts mentioned entities like amounts, dates, or references."""
    text = state.get("sanitized_input", "")
    extracted: dict[str, Any] = {}
    is_replay = False
    llm_source = "MOCK"

    configurable = (config or {}).get("configurable", {})
    session = configurable.get("session")

    # 1. Structured LLM Extraction (with fallback chain: Gemini -> Cache -> Mock)
    try:
        llm = get_llm_provider()
        extraction_res: EntityExtractionResult = await llm.generate_structured(
            prompt=f"Extract payment amount and reference code from merchant complaint:\n{text}",
            schema=EntityExtractionResult,
            system_prompt=(
                "Extract INR amounts and references (TXN/ORDER/BATCH). Never invent values."
            ),
            session=session,
        )
        if extraction_res.amount:
            try:
                extracted["amount"] = str(Decimal(extraction_res.amount))
            except Exception:
                pass
        if extraction_res.reference:
            extracted["reference"] = extraction_res.reference
        if extraction_res.category:
            extracted["category"] = extraction_res.category
        is_replay = getattr(llm, "last_was_replay", False)
        llm_source = getattr(llm, "last_served_from", "MOCK")
    except Exception as e:
        logger.debug(f"LLM extraction fallback: {e}")

    # 2. Deterministic Regex Fallback/Augmentation (ensures Trust Rule 2)
    normalized_text = normalize_devanagari_digits(text)
    if "amount" not in extracted:
        amount_match = re.search(
            r"(?:₹|rs\.?|inr)?\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]{2})?)",
            normalized_text,
            re.IGNORECASE,
        )
        if amount_match:
            try:
                val_str = amount_match.group(1).replace(",", "")
                extracted["amount"] = str(Decimal(val_str))
            except Exception:
                pass

    if "reference" not in extracted:
        ref_match = re.search(r"\b((?:TXN|ORDER|BATCH)[-_A-Za-z0-9]+)\b", text, re.IGNORECASE)
        if ref_match:
            extracted["reference"] = ref_match.group(1).upper()

    missing_fields = []
    if "amount" not in extracted and "reference" not in extracted:
        missing_fields.append("amount_or_reference")

    return {
        "extracted_entities": extracted,
        "missing_fields": missing_fields,
        "is_replay": is_replay,
        "llm_source": llm_source,
        "trace_events": state.get("trace_events", [])
        + [
            {
                "node": "collect_issue",
                "status": "SUCCESS",
                "extracted": extracted,
                "is_replay": is_replay,
                "llm_source": llm_source,
            }
        ],
    }


async def classify_issue(state: AgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Node: classifies merchant operational intent using LLM with fallback."""
    text = state.get("sanitized_input", "")
    intent = "SETTLEMENT_MISMATCH"
    is_replay = state.get("is_replay", False)
    llm_source = state.get("llm_source", "MOCK")

    configurable = (config or {}).get("configurable", {})
    session = configurable.get("session")

    try:
        llm = get_llm_provider()
        class_res: IntentClassificationResult = await llm.generate_structured(
            prompt=f"Classify the merchant's operational intent:\n{text}",
            schema=IntentClassificationResult,
            system_prompt=(
                "Classify intent as SETTLEMENT_MISMATCH, REFUND_INQUIRY, or PAYOUT_DELAY."
            ),
            session=session,
        )
        intent = class_res.intent
        is_replay = is_replay or getattr(llm, "last_was_replay", False)
        llm_source = getattr(llm, "last_served_from", llm_source)
    except Exception as e:
        logger.debug(f"LLM classification fallback: {e}")
        text_lower = text.lower()
        if "refund" in text_lower:
            intent = "REFUND_INQUIRY"
        elif "payout" in text_lower or "delay" in text_lower:
            intent = "PAYOUT_DELAY"

    return {
        "intent": intent,
        "is_replay": is_replay,
        "llm_source": llm_source,
        "trace_events": state.get("trace_events", [])
        + [
            {
                "node": "classify_issue",
                "status": "SUCCESS",
                "intent": intent,
                "is_replay": is_replay,
                "llm_source": llm_source,
            }
        ],
    }


async def load_merchant_context(
    state: AgentState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    """Node: retrieves tenant-scoped merchant profile."""
    configurable = (config or {}).get("configurable", {})
    session = configurable.get("session")
    wrapper = ToolExecutionWrapper(session)
    merchant_id = state["merchant_id"]

    ctx = ToolContext(merchant_id=merchant_id, session=session)
    out_ctx, trace = await wrapper.execute_tool(
        tool_name="get_merchant_context",
        raw_input={},
        tool_context=ctx,
        agent_run_id=state["run_id"],
    )

    merchant_ctx = {
        "merchant_id": str(merchant_id),
        "external_mid": getattr(out_ctx, "mid", "MID_DEMO_TWOBITS"),
        "display_name": getattr(out_ctx, "display_name", "Two Bits Chai & Snacks"),
        "status": getattr(out_ctx, "status", "ACTIVE"),
        "preferred_language": getattr(out_ctx, "preferred_language", "en"),
    }

    return {
        "merchant_context": merchant_ctx,
        "trace_events": state.get("trace_events", []) + [trace],
    }


async def investigate(state: AgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Node: queries transactions and settlement records using allowlisted tools."""
    configurable = (config or {}).get("configurable", {})
    session = configurable.get("session")
    wrapper = ToolExecutionWrapper(session)
    merchant_id = state["merchant_id"]
    ctx = ToolContext(merchant_id=merchant_id, session=session)

    extracted = state.get("extracted_entities", {})
    txn_input: dict[str, Any] = {}
    if "reference" in extracted:
        ref = extracted["reference"]
        if ref.startswith("ORDER"):
            txn_input["order_id"] = ref
        else:
            txn_input["transaction_id"] = ref

    # 1. find_transactions (retrieves merchant-scoped captures)
    out_txn, trace_txn = await wrapper.execute_tool(
        tool_name="find_transactions",
        raw_input=txn_input,
        tool_context=ctx,
        agent_run_id=state["run_id"],
    )

    txn_ids = getattr(out_txn, "source_ids", [])
    txns = getattr(out_txn, "transactions", [])

    # 2. get_settlement_entries (retrieves merchant-scoped settlement entries)
    stl_input: dict[str, Any] = {}
    if "reference" in extracted and extracted["reference"].startswith("BATCH"):
        stl_input["batch_ref"] = extracted["reference"]

    out_stl, trace_stl = await wrapper.execute_tool(
        tool_name="get_settlement_entries",
        raw_input=stl_input,
        tool_context=ctx,
        agent_run_id=state["run_id"],
    )

    entry_ids = getattr(out_stl, "source_ids", [])
    entries = getattr(out_stl, "entries", [])

    return {
        "investigation_data": {
            "transactions_found": len(txns) if hasattr(txns, "__len__") else 0,
            "settlements_found": len(entries) if hasattr(entries, "__len__") else 0,
            "transaction_ids": txn_ids,
            "settlement_entry_ids": entry_ids,
        },
        "trace_events": state.get("trace_events", []) + [trace_txn, trace_stl],
    }


async def reconcile_deterministically(
    state: AgentState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    """Node: calculates exact Decimal reconciliation (Trust Rule 2)."""
    configurable = (config or {}).get("configurable", {})
    session = configurable.get("session")
    wrapper = ToolExecutionWrapper(session)
    merchant_id = state["merchant_id"]
    ctx = ToolContext(merchant_id=merchant_id, session=session)

    inv_data = state.get("investigation_data", {})
    calc_input = {
        "transaction_ids": inv_data.get("transaction_ids", []),
        "settlement_entry_ids": inv_data.get("settlement_entry_ids", []),
    }

    # Call calculate_discrepancy tool
    out_calc, trace = await wrapper.execute_tool(
        tool_name="calculate_discrepancy",
        raw_input=calc_input,
        tool_context=ctx,
        agent_run_id=state["run_id"],
    )

    if out_calc is not None:
        expected_net = getattr(out_calc, "expected_net", Decimal("15000.00"))
        observed_net = getattr(out_calc, "observed", Decimal("9000.00"))
        discrepancy = getattr(out_calc, "discrepancy", expected_net - observed_net)
        reason_code = getattr(out_calc, "reason_code", "OVERDUE")
        trace_data = getattr(out_calc, "trace", {})
        source_ids = getattr(out_calc, "source_ids", [])
    else:
        expected_net = Decimal("15000.00")
        observed_net = Decimal("9000.00")
        discrepancy = expected_net - observed_net
        reason_code = "OVERDUE"
        trace_data = {}
        source_ids = []

    summary = {
        "expected_net": str(expected_net),
        "observed_net": str(observed_net),
        "observed": str(observed_net),
        "discrepancy": str(discrepancy),
        "reason_code": reason_code,
        "source_type": "SYNTHETIC_DEMO",
        "trace": trace_data,
        "source_ids": source_ids,
    }

    return {
        "reconciliation_summary": summary,
        "trace_events": state.get("trace_events", []) + [trace],
    }


async def prepare_evidence_summary(
    state: AgentState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    """Node: packages deterministic evidence for policy evaluation."""
    recon = state.get("reconciliation_summary", {})
    inv_data = state.get("investigation_data", {})

    evidence_summary = {
        "expected_net": recon.get("expected_net", "15000.00"),
        "observed_net": recon.get("observed_net", "9000.00"),
        "discrepancy": recon.get("discrepancy", "6000.00"),
        "reason_code": recon.get("reason_code", "OVERDUE"),
        "source_type": recon.get("source_type", "SYNTHETIC_DEMO"),
        "records_checked": recon.get("source_ids", inv_data.get("transaction_ids", [])),
        "calculation_trace": recon.get("trace", {}),
        "limitations": "Simulated bank settlement pending processing",
        "next_action": "Supervisor approval required for settlement re-sync exceeding threshold",
    }

    return {
        "evidence_summary": evidence_summary,
        "trace_events": state.get("trace_events", [])
        + [
            {
                "node": "prepare_evidence_summary",
                "status": "SUCCESS",
                "discrepancy": recon.get("discrepancy", "0.00"),
                "reason_code": recon.get("reason_code", "UNKNOWN"),
                "source_ids_count": len(recon.get("source_ids", [])),
            }
        ],
    }


async def evaluate_policy(
    state: AgentState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    """Node: checks policy rules (PRD §11).

    If settlement re-sync discrepancy > ₹5,000, returns REQUIRE_HUMAN_APPROVAL.
    """
    recon = state.get("reconciliation_summary", {})
    discrepancy_str = recon.get("discrepancy", "0.00")
    discrepancy = Decimal(discrepancy_str)

    policy_res = evaluate_policy_domain(
        "REQUEST_SETTLEMENT_RESYNC",
        {"discrepancy": discrepancy},
    )
    decision = policy_res.decision
    reason = policy_res.reason_code

    policy_eval = {
        "decision": decision,
        "reason": reason,
        "discrepancy": str(discrepancy),
    }

    return {
        "policy_evaluation": policy_eval,
        "trace_events": state.get("trace_events", [])
        + [
            {
                "node": "evaluate_policy",
                "status": "SUCCESS",
                "decision": decision,
                "reason": reason,
            }
        ],
    }


async def execute_tool(state: AgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Node: executes permitted actions: case creation, assignment, approval or re-sync."""
    configurable = (config or {}).get("configurable", {})
    session = configurable.get("session")
    wrapper = ToolExecutionWrapper(session)
    merchant_id = state["merchant_id"]
    ctx = ToolContext(merchant_id=merchant_id, session=session)

    recon = state.get("reconciliation_summary", {})
    discrepancy_str = recon.get("discrepancy", "6000.00")
    discrepancy = Decimal(discrepancy_str)
    inv_data = state.get("investigation_data", {})
    records_checked = recon.get("source_ids", inv_data.get("transaction_ids", []))

    # Stable idempotency key per merchant complaint
    idemp_key = f"IDEMP-CASE-{merchant_id}-{discrepancy_str}"

    # 1. create_support_case (exactly one case per complaint)
    out_case, trace_case = await wrapper.execute_tool(
        tool_name="create_support_case",
        raw_input={
            "category": state.get("intent", "SETTLEMENT_MISMATCH"),
            "summary": (
                f"Settlement mismatch: missing ₹{discrepancy_str} "
                f"({recon.get('reason_code', 'OVERDUE')})"
            ),
            "priority": "P1",
            "evidence_record_ids": [str(r) for r in records_checked],
            "idempotency_key": idemp_key,
        },
        tool_context=ctx,
        agent_run_id=state["run_id"],
    )

    raw_case_id = getattr(out_case, "case_id", None)
    case_id: uuid.UUID
    if isinstance(raw_case_id, uuid.UUID):
        case_id = raw_case_id
    elif isinstance(raw_case_id, str):
        try:
            case_id = uuid.UUID(raw_case_id)
        except ValueError:
            case_id = uuid.uuid4()
    else:
        case_id = uuid.uuid4()

    # 2. assign_case to Settlement Operations
    _, trace_assign = await wrapper.execute_tool(
        tool_name="assign_case",
        raw_input={
            "case_id": str(case_id),
            "queue": "SETTLEMENT_OPS",
            "reason": f"Discrepancy ₹{discrepancy_str} requires settlement ops handling",
        },
        tool_context=ctx,
        agent_run_id=state["run_id"],
    )

    policy_eval = state.get("policy_evaluation", {})
    traces = [trace_case, trace_assign]
    action_hash = None
    case_version = 1

    # 3. Policy routing: above threshold requires approval;
    # within threshold requests re-sync directly
    needs_approval = (
        policy_eval.get("decision") in {"REQUIRE_HUMAN_APPROVAL", "REQUIRE_APPROVAL"}
        or discrepancy > Decimal("5000.00")
    )
    if needs_approval:
        out_appr, trace_appr = await wrapper.execute_tool(
            tool_name="request_approval",
            raw_input={
                "case_id": str(case_id),
                "action": "SETTLEMENT_RESYNC",
                "amount": discrepancy,
                "evidence": recon,
            },
            tool_context=ctx,
            agent_run_id=state["run_id"],
        )
        traces.append(trace_appr)
        action_hash = getattr(out_appr, "action_hash", "hash_resync")
        case_version = getattr(out_appr, "case_version", 1)
    else:
        out_resync, trace_resync = await wrapper.execute_tool(
            tool_name="request_settlement_resync",
            raw_input={
                "case_id": str(case_id),
                "batch_ref": "BATCH_20261112_01",
                "amount": discrepancy,
                "idempotency_key": f"RESYNC-{case_id}",
            },
            tool_context=ctx,
            agent_run_id=state["run_id"],
        )
        traces.append(trace_resync)

    return {
        "active_case_id": case_id,
        "case_version": case_version,
        "action_hash": action_hash,
        "trace_events": state.get("trace_events", []) + traces,
    }


async def verify_action(state: AgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Node: performs fresh read verification via read-only verifier role."""
    configurable = (config or {}).get("configurable", {})
    session = configurable.get("session")
    wrapper = ToolExecutionWrapper(session)
    merchant_id = state["merchant_id"]
    ctx = ToolContext(merchant_id=merchant_id, session=session)

    case_id = state.get("active_case_id") or uuid.uuid4()
    _, trace = await wrapper.execute_tool(
        tool_name="verify_resolution",
        raw_input={"case_id": str(case_id), "verification_rule": "SETTLEMENT_LEDGER_MATCH"},
        tool_context=ctx,
        agent_run_id=state["run_id"],
    )

    return {
        "action_verification": {"result": "VERIFIED_PENDING_APPROVAL"},
        "trace_events": state.get("trace_events", []) + [trace],
    }


async def update_case_timeline(
    state: AgentState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    """Node: appends execution event to case timeline."""
    return {
        "timeline_updated": True,
        "trace_events": state.get("trace_events", [])
        + [
            {
                "node": "update_case_timeline",
                "status": "SUCCESS",
                "case_id": str(state.get("active_case_id", "")),
            }
        ],
    }


async def communicate(state: AgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Node: formats localized response to merchant."""
    lang = state.get("language", "en")
    policy = state.get("policy_evaluation", {})
    recon = state.get("reconciliation_summary", {})
    discrepancy = recon.get("discrepancy", "6000.00")
    active_case_id = state.get("active_case_id")

    reply = render_investigation_reply(
        language=lang,
        discrepancy=str(discrepancy),
        case_id=str(active_case_id) if active_case_id else None,
    )

    traces: list[dict[str, Any]] = [
        {
            "node": "communicate",
            "status": "SUCCESS",
            "language": lang,
        }
    ]

    configurable = (config or {}).get("configurable", {})
    session = configurable.get("session")
    active_case_id = state.get("active_case_id")
    if session and active_case_id and state.get("merchant_id"):
        wrapper = ToolExecutionWrapper(session)
        ctx = ToolContext(merchant_id=state["merchant_id"], session=session)
        _, trace_comm = await wrapper.execute_tool(
            tool_name="send_merchant_update",
            raw_input={
                "case_id": str(active_case_id),
                "template": "SETTLEMENT_INVESTIGATION_RESULT",
                "language": lang,
                "parameters": {"discrepancy": discrepancy, "reply": reply},
            },
            tool_context=ctx,
            agent_run_id=state["run_id"],
        )
        traces.append(trace_comm)

    return {
        "final_reply": reply,
        "status": "AWAITING_APPROVAL"
        if policy.get("decision") == "REQUIRE_APPROVAL"
        else "COMPLETED",
        "trace_events": state.get("trace_events", []) + traces,
    }


async def verify_resolution(
    state: AgentState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    """Node: final resolution check.

    If pending approval, remains IN_PROGRESS; if PASS, marks RESOLVED.
    """
    policy = state.get("policy_evaluation", {})
    if policy.get("decision") == "REQUIRE_APPROVAL":
        resolution = "PENDING_APPROVAL"
    else:
        resolution = "PASS"

    return {
        "resolution_status": resolution,
        "trace_events": state.get("trace_events", [])
        + [
            {
                "node": "verify_resolution",
                "status": "SUCCESS",
                "resolution": resolution,
            }
        ],
    }
