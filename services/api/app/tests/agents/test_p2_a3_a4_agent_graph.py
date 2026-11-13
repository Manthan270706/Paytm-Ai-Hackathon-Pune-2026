import uuid

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.agents.nodes import detect_language, redact_sensitive
from app.agents.wrapper import ToolExecutionWrapper, attempt_pydantic_repair
from app.main import app
from app.tools.registry import ToolContext

client = TestClient(app)


def test_redact_sensitive_masks_tokens() -> None:
    # 16-digit card number and OTP
    sample = "My card is 4111 2222 3333 4444 and my otp is 123456"
    redacted = redact_sensitive(sample)
    assert "4111" not in redacted
    assert "123456" not in redacted
    assert "[CARD_REDACTED]" in redacted
    assert "[SENSITIVE_REDACTED]" in redacted


def test_detect_language() -> None:
    assert detect_language("Check my settlement") == "en"
    assert detect_language("मेरा सेटलमेंट कहां है?") == "hi"
    assert detect_language("माझे पैसे मिळाले नाही") == "mr"


def test_pydantic_repair_retry() -> None:
    class DummyInput(BaseModel):
        required_text: str
        count: int = 1

    # Malformed keys: casing and alias
    raw_bad = {"REQUIRED-TEXT": "hello"}
    repaired = attempt_pydantic_repair(raw_bad, DummyInput)
    validated = DummyInput.model_validate(repaired)
    assert validated.required_text == "hello"
    assert validated.count == 1


@pytest.mark.asyncio
async def test_wrapper_rejects_unlisted_tool() -> None:
    wrapper = ToolExecutionWrapper()
    ctx = ToolContext(merchant_id=uuid.uuid4(), session=None)  # type: ignore[arg-type]
    with pytest.raises(ValueError) as excinfo:
        await wrapper.execute_tool(
            tool_name="unauthorized_transfer_funds",
            raw_input={},
            tool_context=ctx,
            agent_run_id=uuid.uuid4(),
        )
    assert "not in the allowlisted tool registry" in str(excinfo.value)


@pytest.mark.asyncio
async def test_agent_graph_execution_and_tool_traces() -> None:
    # Test via POST /api/v1/agent/messages
    msg_res = client.post(
        "/api/v1/agent/messages",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
        json={
            "message": "My ₹6,000 payment from yesterday is missing from settlement",
            "language": "en",
        },
    )
    assert msg_res.status_code == 200
    data = msg_res.json()
    assert data["ok"] is True
    assert data["meta"]["source_type"] == "SYNTHETIC_DEMO"

    agent_data = data["data"]
    run_id = agent_data["run_id"]
    assert "conversation_id" in agent_data
    reply = agent_data["reply"]

    assert "6000" in reply or "₹6,000" in reply or "investigated" in reply
    assert agent_data["intent"] == "SETTLEMENT_MISMATCH"
    assert agent_data["evidence_summary"]["discrepancy"] == "6000.00"
    assert agent_data["evidence_summary"]["reason_code"] == "OVERDUE"

    # Now verify SSE trace endpoint GET /api/v1/agent/runs/{run_id}/events
    sse_res = client.get(
        f"/api/v1/agent/runs/{run_id}/events",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
    )
    assert sse_res.status_code == 200
    assert "text/event-stream" in sse_res.headers["content-type"]

    events_text = sse_res.text
    assert "data:" in events_text
    assert "calculate_discrepancy" in events_text or "find_transactions" in events_text
    assert "COMPLETED" in events_text


def test_sse_trace_cross_merchant_forbidden() -> None:
    # 1. Create a run for merchant-1
    msg_res = client.post(
        "/api/v1/agent/messages",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
        json={"message": "Status check", "language": "en"},
    )
    assert msg_res.status_code == 200
    run_id = msg_res.json()["data"]["run_id"]

    # 2. Foreign merchant attempts to read the SSE stream
    foreign_res = client.get(
        f"/api/v1/agent/runs/{run_id}/events",
        headers={"Authorization": "Bearer demo-token-merchant-2"},
    )
    assert foreign_res.status_code == 403
    assert foreign_res.json()["error"]["code"] == "FORBIDDEN"


def test_sse_trace_not_found() -> None:
    non_existent = uuid.uuid4()
    res = client.get(
        f"/api/v1/agent/runs/{non_existent}/events",
        headers={"Authorization": "Bearer demo-token-merchant-1"},
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"
