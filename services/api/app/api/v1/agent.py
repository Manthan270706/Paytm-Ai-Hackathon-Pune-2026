import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runner import run_agent_turn
from app.api.v1.schemas import AgentMessageRequest, AgentMessageResponse
from app.core.dependencies import AuthContext, get_auth_context
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.response import success_response
from app.db.models import AgentRun, Conversation, ToolExecution
from app.db.seed import MERCHANT_ID
from app.db.session import get_db_session

router = APIRouter()


@router.post("/agent/messages", summary="Start or resume LangGraph agent execution")
async def send_agent_message(
    req: AgentMessageRequest,
    auth: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    merchant_id = auth.active_merchant_id or MERCHANT_ID
    agent_run, result_state = await run_agent_turn(
        merchant_id=merchant_id,
        message=req.message,
        session=session,
        conversation_id=req.conversation_id,
        language=req.language,
        user_id=auth.user_id,
    )

    conv_id = result_state.get("conversation_id", req.conversation_id or uuid.uuid4())
    active_case_id = result_state.get("active_case_id")
    reply = result_state.get("final_reply", "I have investigated your request.")
    intent = result_state.get("intent", "SETTLEMENT_MISMATCH")
    recon_summary = result_state.get("reconciliation_summary")

    return success_response(
        data=AgentMessageResponse(
            conversation_id=conv_id,
            run_id=agent_run.id,
            reply=reply,
            language=result_state.get("language", req.language),
            intent=intent,
            active_case_id=active_case_id,
            evidence_summary=recon_summary,
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )


@router.get("/agent/runs/{run_id}/events", summary="SSE stream of live node/tool trace")
async def stream_agent_events(
    run_id: uuid.UUID,
    auth: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    # 1. Tenant-scoped IDOR verification
    query = (
        select(AgentRun, Conversation.merchant_id)
        .join(Conversation, AgentRun.conversation_id == Conversation.id)
        .where(AgentRun.id == run_id)
    )
    res = await session.execute(query)
    row = res.first()
    if not row:
        raise NotFoundError(f"Agent run {run_id} not found")

    run_obj, run_merchant_id = row[0], row[1]
    is_cross_merchant = (
        auth.role == "MERCHANT"
        and auth.active_merchant_id
        and run_merchant_id != auth.active_merchant_id
    )
    if is_cross_merchant:
        raise ForbiddenError("Access to foreign merchant agent run is denied")

    # 2. Fetch recorded tool executions
    exec_query = (
        select(ToolExecution)
        .where(ToolExecution.agent_run_id == run_id)
        .order_by(ToolExecution.created_at.asc())
    )
    exec_res = await session.execute(exec_query)
    executions = exec_res.scalars().all()

    async def event_generator() -> AsyncGenerator[str, None]:
        for te in executions:
            event_payload = {
                "id": str(te.id),
                "run_id": str(run_id),
                "node": te.tool,
                "tool": te.tool,
                "status": te.status,
                "latency": te.latency,
                "input_hash": te.input_hash,
                "output_ref": te.output_ref,
                "timestamp": te.created_at.isoformat() if te.created_at else None,
            }
            yield f"data: {json.dumps(event_payload, default=str)}\n\n"

        # Terminal event
        terminal_payload = {
            "type": "COMPLETED",
            "run_id": str(run_id),
            "status": run_obj.status,
        }
        yield f"data: {json.dumps(terminal_payload, default=str)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
