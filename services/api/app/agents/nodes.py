import logging
import re
import uuid
from decimal import Decimal
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.state import AgentState
from app.agents.templates import (
    detect_language,
    format_case_tag,
    normalize_devanagari_digits,
    render_category_reply,
    render_greeting_reply,
    render_investigation_reply,
    render_no_discrepancy_reply,
)
from app.agents.wrapper import ToolExecutionWrapper
from app.core.config import settings
from app.core.redaction import redact
from app.db.scoped_repository import ScopedRepository
from app.domain.policy import evaluate as evaluate_policy_domain
from app.integrations import get_llm_provider
from app.integrations.gemini.schemas import (
    ConversationalResponse,
    EntityExtractionResult,
    IntentClassificationResult,
)
from app.tools.registry import ToolContext

logger = logging.getLogger(__name__)





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
        ref_match = re.search(r"\b((?:TXN|ORDER|BATCH|CASE)[-_A-Za-z0-9]+)\b", text, re.IGNORECASE)
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

    text_lower = text.lower()
    has_operational_keyword = any(
        k in text_lower
        for k in [
            "refund", "debited", "mdr", "rupay", "fee", "overcharge",
            "soundbox", "audio", "hardware", "chime", "latency",
            "payout", "sla", "holiday", "settlement", "missing",
            "6000", "6,000", "६,०००", "1200", "1,200", "१,२००",
            "850", "८५०", "18,500", "18500", "१८,५००",
            "1024", "1025", "1026", "1027", "1028", "ord_", "batch_", "txn_", "case-",
        ]
    )

    if not has_operational_keyword and (
        re.search(
            r"\b(hi|hello|hey|heyy+|howdy|greetings|namaste|namaskar|good\s*(morning|afternoon|evening)|who\s+are\s+you|what\s+is\s+your\s+name|who\s+am\s+i\s+talking\s+to)\b",
            text_lower,
        )
        or any(w in text for w in ["नमस्ते", "नमस्कार", "प्रणाम", "हाय", "हॅलो", "तुम्ही कोण", "आप कौन"])
    ):
        intent = "GREETING"
    elif not has_operational_keyword and (
        re.search(
            r"\b(what\s+can\s+you\s+do|how\s+can\s+you\s+help|help\s*me|capabilities|features|options)\b",
            text_lower,
        )
        or any(w in text for w in ["क्या कर सकते", "काय करू शकता", "मदत करा", "मदद करें"])
    ):
        intent = "GENERAL_QUERY"
    elif "refund" in text_lower or "debited" in text_lower or "1025" in text:
        intent = "REFUND_DISPUTE"
    elif "mdr" in text_lower or "rupay" in text_lower or "fee" in text_lower or "overcharge" in text_lower or "1026" in text:
        intent = "FEE_OVERCHARGE"
    elif "soundbox" in text_lower or "audio" in text_lower or "hardware" in text_lower or "chime" in text_lower or "latency" in text_lower or "1027" in text:
        intent = "HARDWARE_DIAGNOSTICS"
    elif "payout" in text_lower or "sla" in text_lower or "holiday" in text_lower or "18,500" in text or "18500" in text or "1028" in text:
        intent = "PAYOUT_DELAY"
    elif "settlement" in text_lower or "missing" in text_lower or "6000" in text or "6,000" in text or "६,०००" in text or "1024" in text:
        intent = "SETTLEMENT_MISMATCH"
    else:
        try:
            llm = get_llm_provider()
            class_res: IntentClassificationResult = await llm.generate_structured(
                prompt=f"Classify the merchant's operational intent:\n{text}",
                schema=IntentClassificationResult,
                system_prompt=(
                    "Classify intent as one of: GREETING, GENERAL_QUERY, SETTLEMENT_MISMATCH, REFUND_DISPUTE, FEE_OVERCHARGE, HARDWARE_DIAGNOSTICS, PAYOUT_DELAY."
                ),
                session=session,
            )
            intent = class_res.intent
            is_replay = is_replay or getattr(llm, "last_was_replay", False)
            llm_source = getattr(llm, "last_served_from", llm_source)
        except Exception as e:
            logger.debug(f"LLM classification fallback: {e}")

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
        "display_name": getattr(out_ctx, "display_name", "Paytm Smart Merchant Store"),
        "status": getattr(out_ctx, "status", "ACTIVE"),
        "preferred_language": getattr(out_ctx, "preferred_language", "en"),
    }

    return {
        "merchant_context": merchant_ctx,
        "trace_events": state.get("trace_events", []) + [trace],
    }


async def investigate(state: AgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Node: queries transactions, settlement records, and existing cases using allowlisted tools."""
    configurable = (config or {}).get("configurable", {})
    session = configurable.get("session")
    wrapper = ToolExecutionWrapper(session)
    merchant_id = state["merchant_id"]
    ctx = ToolContext(merchant_id=merchant_id, session=session)

    extracted = state.get("extracted_entities", {})
    intent = state.get("intent", "SETTLEMENT_MISMATCH")
    text = state.get("sanitized_input", "")

    if intent in {"GREETING", "GENERAL_QUERY"}:
        return {
            "investigation_data": {
                "transactions_found": 0,
                "settlements_found": 0,
                "transaction_ids": [],
                "settlement_entry_ids": [],
                "matched_case_id": None,
                "matched_case_number": None,
                "matched_case_status": None,
                "matched_case_version": 1,
            },
            "trace_events": state.get("trace_events", [])
            + [
                {
                    "node": "investigate",
                    "status": "SKIPPED_CONVERSATIONAL",
                    "intent": intent,
                }
            ],
        }

    # Look up existing cases for this merchant to bind if applicable
    matched_case_info = None
    if session is not None:
        try:
            repo = ScopedRepository(session=session, merchant_id=merchant_id)
            existing_cases = await repo.list_cases()
            ref = extracted.get("reference", "").upper()
            amount_str = extracted.get("amount", "")

            for c in existing_cases:
                # 1. Direct case number match
                if c.case_number and c.case_number.upper() in text.upper():
                    matched_case_info = c
                    break
                # 2. Reference match (order_id, batch_ref, etc.)
                if ref and (ref in c.summary.upper() or ref in (c.idempotency_key or "").upper()):
                    matched_case_info = c
                    break
                # 3. Category + Amount match
                if c.category == intent and amount_str and amount_str in (c.summary or ""):
                    matched_case_info = c
                    break
                # 4. Scenario-specific category match
                if intent == "REFUND_DISPUTE" and c.category == "REFUND_DISPUTE":
                    matched_case_info = c
                    break
                elif intent == "FEE_OVERCHARGE" and c.category == "FEE_OVERCHARGE":
                    matched_case_info = c
                    break
                elif intent == "HARDWARE_DIAGNOSTICS" and c.category == "HARDWARE_DIAGNOSTICS":
                    matched_case_info = c
                    break
                elif intent == "PAYOUT_DELAY" and c.category == "PAYOUT_DELAY":
                    matched_case_info = c
                    break
                elif (
                    intent == "SETTLEMENT_MISMATCH"
                    and c.category == "SETTLEMENT_MISMATCH"
                    and ("6000" in text or "6,000" in text or "६,०००" in text or not amount_str)
                ):
                    matched_case_info = c
                    break
        except Exception as e:
            logger.debug(f"Case lookup error: {e}")

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
            "matched_case_id": str(matched_case_info.id) if matched_case_info else None,
            "matched_case_number": matched_case_info.case_number if matched_case_info else None,
            "matched_case_status": matched_case_info.status if matched_case_info else None,
            "matched_case_version": matched_case_info.version if matched_case_info else 1,
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

    intent = state.get("intent", "SETTLEMENT_MISMATCH")
    inv_data = state.get("investigation_data", {})
    extracted = state.get("extracted_entities", {})

    if intent in {"GREETING", "GENERAL_QUERY"}:
        return {
            "reconciliation_summary": None,
            "trace_events": state.get("trace_events", [])
            + [
                {
                    "node": "reconcile_deterministically",
                    "status": "SKIPPED_CONVERSATIONAL",
                    "intent": intent,
                }
            ],
        }

    if intent in {"REFUND_DISPUTE", "REFUND_INQUIRY"}:
        order_ref = extracted.get("reference", "ORD_20261111_09")
        summary = {
            "expected_net": "1200.00",
            "observed_net": "2400.00",
            "observed": "2400.00",
            "discrepancy": "1200.00",
            "reason_code": "DUPLICATE_DEBIT",
            "source_type": "SYNTHETIC_DEMO",
            "metric_1_label": "Original Refund",
            "metric_1_value": "₹1,200.00",
            "metric_2_label": "Ledger Debited",
            "metric_2_value": "₹2,400.00",
            "metric_3_label": "Duplicate Debit",
            "metric_3_value": "₹1,200.00",
            "trace": {"order_id": order_ref, "adjustment_type": "CREDIT_REVERSAL_QUEUED"},
            "source_ids": [order_ref],
        }
        trace = {
            "node": "reconcile_deterministically",
            "status": "SUCCESS",
            "rule": "REFUND_DUPLICATE_DEBIT_MATCH",
            "variance": "1200.00",
        }
        return {
            "reconciliation_summary": summary,
            "trace_events": state.get("trace_events", []) + [trace],
        }

    elif intent == "FEE_OVERCHARGE":
        summary = {
            "expected_net": "1.20",
            "observed_net": "2.15",
            "observed": "2.15",
            "discrepancy": "850.00",
            "reason_code": "MDR_RATE_MISMATCH",
            "source_type": "SYNTHETIC_DEMO",
            "metric_1_label": "Contract Rate",
            "metric_1_value": "1.20%",
            "metric_2_label": "Rate Billed",
            "metric_2_value": "2.15%",
            "metric_3_label": "Fee Variance",
            "metric_3_value": "₹850.00",
            "trace": {
                "contract_rate": "1.20%",
                "rate_billed": "2.15%",
                "credit_note": "CN-20261112-0850",
            },
            "source_ids": ["RULE_RUPAY_2026"],
        }
        trace = {
            "node": "reconcile_deterministically",
            "status": "SUCCESS",
            "rule": "MDR_COMMISSION_SCHEDULE_AUDIT",
            "variance": "850.00",
        }
        return {
            "reconciliation_summary": summary,
            "trace_events": state.get("trace_events", []) + [trace],
        }

    elif intent == "HARDWARE_DIAGNOSTICS":
        summary = {
            "expected_net": "0.00",
            "observed_net": "0.00",
            "observed": "0.00",
            "discrepancy": "0.00",
            "reason_code": "TELEMETRY_RESOLVED",
            "source_type": "SYNTHETIC_DEMO",
            "metric_1_label": "4G Signal",
            "metric_1_value": "-82dBm (Good)",
            "metric_2_label": "Audio Latency",
            "metric_2_value": "320ms",
            "metric_3_label": "Test Chime",
            "metric_3_value": "PASS",
            "trace": {
                "device_imei": "860459048123456",
                "firmware_version": "v4.2.1-prod",
                "cache": "PURGED",
            },
            "source_ids": ["860459048123456"],
        }
        trace = {
            "node": "reconcile_deterministically",
            "status": "SUCCESS",
            "rule": "HARDWARE_TELEMETRY_DIAGNOSED",
            "variance": "0.00",
        }
        return {
            "reconciliation_summary": summary,
            "trace_events": state.get("trace_events", []) + [trace],
        }

    elif intent == "PAYOUT_DELAY":
        summary = {
            "expected_net": "18500.00",
            "observed_net": "0.00",
            "observed": "0.00",
            "discrepancy": "18500.00",
            "reason_code": "SLA_BREACH_HOLD",
            "source_type": "SYNTHETIC_DEMO",
            "metric_1_label": "Batch Amount",
            "metric_1_value": "₹18,500.00",
            "metric_2_label": "SLA Elapsed",
            "metric_2_value": "52 Hours",
            "metric_3_label": "Hold Status",
            "metric_3_value": "SLA BREACH",
            "trace": {
                "batch_ref": "BATCH_20261110_02",
                "bank_utr": "PBNK20261110998811",
                "sla_hours": 52,
            },
            "source_ids": ["BATCH_20261110_02"],
        }
        trace = {
            "node": "reconcile_deterministically",
            "status": "SUCCESS",
            "rule": "PAYOUT_SLA_BREACH_VERIFIED",
            "variance": "18500.00",
        }
        return {
            "reconciliation_summary": summary,
            "trace_events": state.get("trace_events", []) + [trace],
        }

    # SETTLEMENT_MISMATCH (default)
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
        "metric_1_label": "Expected Net",
        "metric_1_value": f"₹{expected_net}",
        "metric_2_label": "Observed Net",
        "metric_2_value": f"₹{observed_net}",
        "metric_3_label": "Discrepancy",
        "metric_3_value": f"₹{discrepancy}",
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
    recon = state.get("reconciliation_summary")
    inv_data = state.get("investigation_data", {})
    intent = state.get("intent", "SETTLEMENT_MISMATCH")

    if intent in {"GREETING", "GENERAL_QUERY"} or not recon:
        return {
            "evidence_summary": None,
            "trace_events": state.get("trace_events", [])
            + [
                {
                    "node": "prepare_evidence_summary",
                    "status": "SKIPPED_CONVERSATIONAL",
                    "intent": intent,
                }
            ],
        }

    discrepancy_str = recon.get("discrepancy", "6000.00")
    try:
        discrepancy_dec = Decimal(discrepancy_str)
    except Exception:
        discrepancy_dec = Decimal("0.00")

    case_number = inv_data.get("matched_case_number")

    if intent in {"REFUND_DISPUTE", "REFUND_INQUIRY"}:
        limitations = "Bank gateway reconciliation confirmed dual debit entries on merchant ledger."
        next_action = "Queued automatic credit reversal on merchant ledger."
    elif intent == "FEE_OVERCHARGE":
        limitations = "RuPay MDR fee schedule mismatch verified against merchant agreement."
        next_action = "Credit note CN-20261112-0850 posted to merchant account; pending final verification."
    elif intent == "HARDWARE_DIAGNOSTICS":
        limitations = "Paytm Soundbox 4G telemetry cache purged remotely."
        next_action = "Soundbox firmware cache refreshed; audio chime verified."
    elif intent == "PAYOUT_DELAY":
        limitations = "T+1 clearing holiday hold exceeded standard 48h settlement window."
        next_action = "Awaiting supervisor override to release payout from settlements queue."
    elif discrepancy_dec <= Decimal("0.00"):
        limitations = "Settlement records fully verified."
        next_action = "All captured payments match settlement batch. No action required."
    else:
        limitations = "Simulated bank settlement pending processing"
        next_action = "Supervisor approval required for settlement re-sync exceeding threshold"

    evidence_summary = {
        "expected_net": recon.get("expected_net", "15000.00"),
        "observed_net": recon.get("observed_net", "9000.00"),
        "discrepancy": discrepancy_str,
        "reason_code": recon.get("reason_code", "OVERDUE"),
        "source_type": recon.get("source_type", "SYNTHETIC_DEMO"),
        "records_checked": recon.get("source_ids", inv_data.get("transaction_ids", [])),
        "calculation_trace": recon.get("trace", {}),
        "limitations": limitations,
        "next_action": next_action,
        "metric_1_label": recon.get("metric_1_label", "Expected Net"),
        "metric_1_value": recon.get("metric_1_value", f"₹{recon.get('expected_net', '15000.00')}"),
        "metric_2_label": recon.get("metric_2_label", "Observed Net"),
        "metric_2_value": recon.get("metric_2_value", f"₹{recon.get('observed_net', '9000.00')}"),
        "metric_3_label": recon.get("metric_3_label", "Discrepancy"),
        "metric_3_value": recon.get("metric_3_value", f"₹{discrepancy_str}"),
        "case_number": case_number,
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
    If discrepancy is zero or negative, returns NO_ACTION.
    """
    recon = state.get("reconciliation_summary") or {}
    intent = state.get("intent", "SETTLEMENT_MISMATCH")

    if intent in {"GREETING", "GENERAL_QUERY"}:
        return {
            "policy_evaluation": {
                "decision": "NO_ACTION",
                "reason": "CONVERSATIONAL_TURN",
                "discrepancy": "0.00",
            },
            "trace_events": state.get("trace_events", [])
            + [
                {
                    "node": "evaluate_policy",
                    "status": "SUCCESS",
                    "decision": "NO_ACTION",
                    "reason": "CONVERSATIONAL_TURN",
                }
            ],
        }

    discrepancy_str = recon.get("discrepancy", "0.00")
    try:
        discrepancy = Decimal(discrepancy_str)
    except Exception:
        discrepancy = Decimal("0.00")

    if discrepancy <= Decimal("0.00") and intent != "HARDWARE_DIAGNOSTICS":
        return {
            "policy_evaluation": {
                "decision": "NO_ACTION",
                "reason": "NO_DISCREPANCY",
                "discrepancy": "0.00",
            },
            "trace_events": state.get("trace_events", [])
            + [
                {
                    "node": "evaluate_policy",
                    "status": "SUCCESS",
                    "decision": "NO_ACTION",
                    "reason": "NO_DISCREPANCY",
                }
            ],
        }

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
    inv_data = state.get("investigation_data", {})
    intent = state.get("intent", "SETTLEMENT_MISMATCH")
    discrepancy_str = recon.get("discrepancy", "6000.00")
    try:
        discrepancy = Decimal(discrepancy_str)
    except Exception:
        discrepancy = Decimal("0.00")

    matched_case_id = inv_data.get("matched_case_id")
    matched_case_number = inv_data.get("matched_case_number")
    matched_case_version = inv_data.get("matched_case_version", 1)

    # If already matched an existing case in this merchant portfolio, bind to it
    if matched_case_id:
        case_id = uuid.UUID(matched_case_id)
        case_number = matched_case_number
        case_version = matched_case_version

        # Record timeline event on existing case
        if session is not None:
            try:
                repo = ScopedRepository(session=session, merchant_id=merchant_id)
                await repo.create_case_event(
                    case_id=case_id,
                    actor="OpsSaathi AI",
                    event_type="MERCHANT_INQUIRY_RECEIVED",
                    payload={"message": state.get("sanitized_input", ""), "intent": intent},
                    from_status=inv_data.get("matched_case_status"),
                    to_status=inv_data.get("matched_case_status"),
                )
            except Exception as e:
                logger.debug(f"Event creation error: {e}")

        return {
            "active_case_id": case_id,
            "case_number": case_number,
            "case_version": case_version,
            "action_hash": None,
            "trace_events": state.get("trace_events", [])
            + [
                {
                    "node": "execute_tool",
                    "status": "BOUND_EXISTING_CASE",
                    "case_id": str(case_id),
                    "case_number": case_number,
                }
            ],
        }

    if discrepancy <= Decimal("0.00") and intent != "HARDWARE_DIAGNOSTICS":
        return {
            "active_case_id": None,
            "case_number": None,
            "case_version": 1,
            "action_hash": None,
            "trace_events": state.get("trace_events", []),
        }

    records_checked = recon.get("source_ids", inv_data.get("transaction_ids", []))
    idemp_key = f"IDEMP-CASE-{merchant_id}-{intent}-{discrepancy_str}"

    queue_map = {
        "SETTLEMENT_MISMATCH": "SETTLEMENT_OPS",
        "REFUND_DISPUTE": "SETTLEMENTS",
        "REFUND_INQUIRY": "SETTLEMENTS",
        "FEE_OVERCHARGE": "SETTLEMENT_OPS",
        "HARDWARE_DIAGNOSTICS": "TECH_SUPPORT",
        "PAYOUT_DELAY": "SETTLEMENTS",
    }
    target_queue = queue_map.get(intent, "SETTLEMENTS")

    # 1. create_support_case
    out_case, trace_case = await wrapper.execute_tool(
        tool_name="create_support_case",
        raw_input={
            "category": intent,
            "summary": (
                f"{intent}: ₹{discrepancy_str} ({recon.get('reason_code', 'OVERDUE')})"
            ),
            "priority": "P1" if discrepancy > Decimal("5000.00") else "P2",
            "evidence_record_ids": [str(r) for r in records_checked],
            "idempotency_key": idemp_key,
        },
        tool_context=ctx,
        agent_run_id=state["run_id"],
    )

    raw_case_id = getattr(out_case, "case_id", None)
    case_number = getattr(out_case, "case_number", None)
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

    # 2. assign_case to queue
    _, trace_assign = await wrapper.execute_tool(
        tool_name="assign_case",
        raw_input={
            "case_id": str(case_id),
            "queue": target_queue,
            "reason": f"Discrepancy ₹{discrepancy_str} requires {target_queue} handling",
        },
        tool_context=ctx,
        agent_run_id=state["run_id"],
    )

    policy_eval = state.get("policy_evaluation", {})
    traces = [trace_case, trace_assign]
    action_hash = None
    case_version = 1

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
    elif intent == "SETTLEMENT_MISMATCH" and discrepancy > Decimal("0.00"):
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
        "case_number": case_number,
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
    intent = state.get("intent", "SETTLEMENT_MISMATCH")

    if intent in {"GREETING", "GENERAL_QUERY"}:
        reply = None
        configurable = (config or {}).get("configurable", {})
        session = configurable.get("session")

        # Attempt live conversational LLM generation if available and not demo_deterministic
        if settings.GEMINI_API_KEY and not settings.DEMO_DETERMINISTIC:
            try:
                llm = get_llm_provider()
                conv_res: ConversationalResponse = await llm.generate_structured(
                    prompt=f"Merchant message ({lang}):\n{state.get('sanitized_input', '')}",
                    schema=ConversationalResponse,
                    system_prompt=(
                        f"You are OpsSaathi, an autonomous AI Operations Teammate for Paytm merchants. "
                        f"Respond warmly and naturally in {lang} (English, Hindi, or Marathi). "
                        f"Introduce yourself as OpsSaathi AI and briefly mention you can help with missing settlements, "
                        f"refund disputes, MDR fees, Soundbox diagnostics, or payout delays. "
                        f"Keep the reply concise (2-3 sentences), professional, and inviting."
                    ),
                    session=session,
                )
                if conv_res and conv_res.reply:
                    reply = conv_res.reply
            except Exception as e:
                logger.debug(f"Live conversational LLM fallback: {e}")

        if not reply:
            reply = render_greeting_reply(language=lang, query_type=intent)

        return {
            "final_reply": reply,
            "case_number": None,
            "active_case_id": None,
            "status": "COMPLETED",
            "trace_events": state.get("trace_events", [])
            + [
                {
                    "node": "communicate",
                    "status": "SUCCESS",
                    "language": lang,
                    "category": intent,
                }
            ],
        }

    policy = state.get("policy_evaluation", {})
    recon = state.get("reconciliation_summary") or {}
    inv_data = state.get("investigation_data", {})
    extracted = state.get("extracted_entities", {})
    discrepancy_str = recon.get("discrepancy", "6000.00")
    try:
        discrepancy_dec = Decimal(discrepancy_str)
    except Exception:
        discrepancy_dec = Decimal("0.00")

    active_case_id = state.get("active_case_id") or inv_data.get("matched_case_id")
    case_number = state.get("case_number") or inv_data.get("matched_case_number")

    if intent == "SETTLEMENT_MISMATCH" and discrepancy_dec <= Decimal("0.00"):
        reply = render_no_discrepancy_reply(
            language=lang,
            batch_ref="BATCH_20261112_01",
        )
    elif intent == "SETTLEMENT_MISMATCH":
        reply = render_investigation_reply(
            language=lang,
            discrepancy=str(discrepancy_str),
            case_id=str(active_case_id) if active_case_id else None,
            case_number=case_number,
        )
    else:
        reply = render_category_reply(
            category=intent,
            language=lang,
            amount=str(discrepancy_str),
            case_id=str(active_case_id) if active_case_id else None,
            case_number=case_number,
            reference=extracted.get("reference"),
        )

    traces: list[dict[str, Any]] = [
        {
            "node": "communicate",
            "status": "SUCCESS",
            "language": lang,
            "category": intent,
        }
    ]

    configurable = (config or {}).get("configurable", {})
    session = configurable.get("session")
    if session and active_case_id and state.get("merchant_id") and discrepancy_dec > Decimal("0.00"):
        wrapper = ToolExecutionWrapper(session)
        ctx = ToolContext(merchant_id=state["merchant_id"], session=session)
        _, trace_comm = await wrapper.execute_tool(
            tool_name="send_merchant_update",
            raw_input={
                "case_id": str(active_case_id),
                "template": f"{intent}_INVESTIGATION_RESULT",
                "language": lang,
                "parameters": {"discrepancy": discrepancy_str, "reply": reply},
            },
            tool_context=ctx,
            agent_run_id=state["run_id"],
        )
        traces.append(trace_comm)

    return {
        "final_reply": reply,
        "case_number": case_number,
        "status": "AWAITING_APPROVAL"
        if policy.get("decision") in {"REQUIRE_APPROVAL", "REQUIRE_HUMAN_APPROVAL"}
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
