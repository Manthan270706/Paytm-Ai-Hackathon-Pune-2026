import asyncio
import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.v1.schemas import AgentMessageRequest, AgentMessageResponse
from app.core.response import success_response

router = APIRouter()


@router.post("/agent/messages", summary="Start or resume LangGraph agent execution")
async def send_agent_message(req: AgentMessageRequest) -> dict:
    conversation_id = req.conversation_id or uuid.uuid4()
    run_id = uuid.uuid4()
    return success_response(
        data=AgentMessageResponse(
            conversation_id=conversation_id,
            run_id=run_id,
            reply=(
                "I investigated your settlement records. We found a ₹6,000 payment that was "
                "successfully captured but is missing from Batch #20261112_01. I have raised "
                "Support Case #1024 and requested a settlement re-sync, currently awaiting "
                "manager approval."
            ),
            language=req.language,
            intent="SETTLEMENT_MISMATCH",
            active_case_id=uuid.uuid4(),
            evidence_summary={
                "expected_net": "15000.00",
                "observed_net": "9000.00",
                "discrepancy": "6000.00",
                "reason_code": "OVERDUE",
                "source_type": "SYNTHETIC_DEMO",
            },
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )


@router.get("/agent/runs/{run_id}/events", summary="SSE stream of live node/tool trace")
async def stream_agent_events(run_id: uuid.UUID) -> StreamingResponse:
    async def event_generator() -> AsyncGenerator[str, None]:
        events = [
            {"node": "intake", "status": "completed", "latency": 0.05},
            {
                "node": "find_transactions",
                "tool": "find_transactions",
                "status": "completed",
                "latency": 0.12,
            },
            {
                "node": "calculate_discrepancy",
                "tool": "calculate_discrepancy",
                "status": "completed",
                "latency": 0.08,
            },
            {"node": "evaluate_policy", "status": "REQUIRE_HUMAN_APPROVAL", "latency": 0.04},
        ]
        for event in events:
            yield f"data: {json.dumps(event)}\n\n"
            await asyncio.sleep(0.01)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
