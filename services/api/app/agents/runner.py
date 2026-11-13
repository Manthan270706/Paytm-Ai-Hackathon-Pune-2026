import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import agent_graph
from app.agents.nodes import redact_sensitive
from app.agents.state import AgentState
from app.db.models import AgentRun, Conversation, Message

logger = logging.getLogger(__name__)


async def run_agent_turn(
    merchant_id: uuid.UUID,
    message: str,
    session: AsyncSession,
    conversation_id: uuid.UUID | None = None,
    language: str = "en",
    user_id: uuid.UUID | None = None,
) -> tuple[AgentRun, dict[str, Any]]:
    """Executes a single conversational agent turn using the LangGraph workflow.

    Persists conversation messages, agent run, and tool traces in PostgreSQL.
    """
    # 1. Lookup or create conversation
    conv: Conversation | None = None
    if conversation_id:
        res = await session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.merchant_id == merchant_id,
            )
        )
        conv = res.scalars().first()

    if not conv:
        conv = Conversation(
            id=conversation_id or uuid.uuid4(),
            merchant_id=merchant_id,
            channel="CHAT",
            language=language,
            created_at=datetime.now(UTC),
        )
        session.add(conv)
        await session.flush()

    # 2. Record user message (redacting sensitive PIN/OTP before DB insertion)
    sanitized_text = redact_sensitive(message)
    user_msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv.id,
        role="USER",
        content=sanitized_text,
        language=language,
        created_at=datetime.now(UTC),
    )
    session.add(user_msg)

    # 3. Create AgentRun record
    run_id = uuid.uuid4()
    trace_id = f"trace_{run_id.hex[:12]}"
    agent_run = AgentRun(
        id=run_id,
        conversation_id=conv.id,
        case_id=conv.active_case_id,
        provider="gemini",
        model="gemini-1.5-flash",
        status="RUNNING",
        trace_id=trace_id,
        created_at=datetime.now(UTC),
    )
    session.add(agent_run)
    await session.flush()

    # 4. Assemble initial agent state
    initial_state: AgentState = {
        "conversation_id": conv.id,
        "run_id": run_id,
        "merchant_id": merchant_id,
        "user_id": user_id,
        "language": language,
        "input_text": message,
        "trace_events": [],
    }

    # 5. Execute LangGraph workflow with dependency injection
    config = {
        "configurable": {
            "thread_id": str(conv.id),
            "session": session,
        }
    }

    result_state = await agent_graph.ainvoke(initial_state, config=config)

    # 6. Update AgentRun status and active case
    final_status = result_state.get("status", "COMPLETED")
    agent_run.status = final_status

    raw_case_id = result_state.get("active_case_id")
    if raw_case_id:
        if isinstance(raw_case_id, str):
            try:
                active_case_id = uuid.UUID(raw_case_id)
            except ValueError:
                active_case_id = None
        else:
            active_case_id = raw_case_id

        if active_case_id:
            agent_run.case_id = active_case_id
            conv.active_case_id = active_case_id

    # 7. Record assistant response message and persist detected language on conversation
    detected_lang = result_state.get("language", language)
    conv.language = detected_lang
    user_msg.language = detected_lang

    reply_text = result_state.get("final_reply", "I have investigated your settlement records.")
    assistant_msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv.id,
        role="ASSISTANT",
        content=reply_text,
        language=detected_lang,
        created_at=datetime.now(UTC),
    )
    session.add(assistant_msg)
    await session.commit()

    return agent_run, result_state
