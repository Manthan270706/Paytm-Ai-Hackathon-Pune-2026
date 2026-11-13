import hashlib
import json
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ToolExecution
from app.integrations.mock import MockLLMProvider
from app.tools.registry import TOOL_REGISTRY, ToolContext

logger = logging.getLogger(__name__)


def compute_sha256(data: Any) -> str:
    """Deterministic hash of arbitrary JSON-compatible input."""
    serialized = json.dumps(data, default=str, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def attempt_pydantic_repair(
    raw_args: dict[str, Any], schema_cls: type[BaseModel]
) -> dict[str, Any]:
    """Single repair attempt for malformed tool arguments."""
    repaired = dict(raw_args)
    fields = schema_cls.model_fields

    for field_name, field_info in fields.items():
        if field_name not in repaired:
            # Check for case-insensitive match or common aliases
            matched = False
            norm_f = field_name.lower().replace("-", "_")
            for k in list(repaired.keys()):
                norm_k = k.lower().replace("-", "_")
                if norm_k == norm_f:
                    repaired[field_name] = repaired.pop(k)
                    matched = True
                    break
            if not matched and field_info.is_required():
                # Provide a safe default if type matches known pattern
                ann = field_info.annotation
                if ann is str:
                    repaired[field_name] = "default"
                elif ann is int:
                    repaired[field_name] = 1
                elif ann is list or getattr(ann, "__origin__", None) is list:
                    repaired[field_name] = []
                elif ann is dict or getattr(ann, "__origin__", None) is dict:
                    repaired[field_name] = {}

    return repaired


class ToolExecutionWrapper:
    """Safe wrapper for allowlisted tool execution with Pydantic validation,

    one repair retry, latency measurement, and persistence to tool_executions table.
    """

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session
        self._mock_provider = MockLLMProvider()

    async def execute_tool(
        self,
        tool_name: str,
        raw_input: dict[str, Any],
        tool_context: ToolContext,
        agent_run_id: uuid.UUID,
        idempotency_key: str | None = None,
    ) -> tuple[BaseModel, dict[str, Any]]:
        # 1. Allowlist enforcement
        if tool_name not in TOOL_REGISTRY:
            err_msg = f"Tool '{tool_name}' is not in the allowlisted tool registry."
            logger.error(err_msg)
            raise ValueError(err_msg)

        tool_def = TOOL_REGISTRY[tool_name]

        # 2. Pydantic validation of tool arguments with one repair retry
        validated_input: BaseModel
        try:
            validated_input = tool_def.input_schema.model_validate(raw_input)
        except ValidationError as e:
            logger.warning(
                "Tool %s initial validation failed: %s. Retrying with repair.",
                tool_name,
                e,
            )
            repaired_input = attempt_pydantic_repair(raw_input, tool_def.input_schema)
            try:
                validated_input = tool_def.input_schema.model_validate(repaired_input)
            except ValidationError as final_err:
                # Log failure and re-raise
                input_hash = compute_sha256(raw_input)
                await self._persist_execution(
                    agent_run_id=agent_run_id,
                    tool_name=tool_name,
                    input_hash=input_hash,
                    output_ref={"error": str(final_err), "validation_failed": True},
                    status="FAILED",
                    latency=0.0,
                    idempotency_key=idempotency_key,
                )
                raise final_err

        # 3. Compute deterministic input hash
        input_hash = compute_sha256(validated_input.model_dump())

        # 4. Execute tool runner with latency timing
        t0 = time.perf_counter()
        status = "SUCCESS"
        output_result: BaseModel

        try:
            output_result = await tool_def.runner(validated_input, tool_context)
        except NotImplementedError:
            # Deterministic mock fallback for Phase 2 stubs
            logger.info(
                "Tool %s runner raised NotImplementedError; returning deterministic mock output.",
                tool_name,
            )
            output_result = await self._mock_provider.generate_structured(
                prompt=f"Generate mock output for {tool_name}",
                schema=tool_def.output_schema,
            )
        except Exception as exc:
            status = "FAILED"
            latency = time.perf_counter() - t0
            await self._persist_execution(
                agent_run_id=agent_run_id,
                tool_name=tool_name,
                input_hash=input_hash,
                output_ref={"error": str(exc)},
                status=status,
                latency=latency,
                idempotency_key=idempotency_key,
            )
            raise exc

        latency = time.perf_counter() - t0
        output_dict = output_result.model_dump(mode="json")

        # 5. Persist to tool_executions table if DB session is present
        await self._persist_execution(
            agent_run_id=agent_run_id,
            tool_name=tool_name,
            input_hash=input_hash,
            output_ref=output_dict,
            status=status,
            latency=latency,
            idempotency_key=idempotency_key,
        )

        trace_event = {
            "node": tool_name,
            "tool": tool_name,
            "status": status,
            "latency": round(latency, 4),
            "input_hash": input_hash,
            "output_ref": output_dict,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        return output_result, trace_event

    async def _persist_execution(
        self,
        agent_run_id: uuid.UUID,
        tool_name: str,
        input_hash: str,
        output_ref: dict[str, Any] | None,
        status: str,
        latency: float,
        idempotency_key: str | None = None,
    ) -> None:
        if self.session is None:
            return

        exec_row = ToolExecution(
            id=uuid.uuid4(),
            agent_run_id=agent_run_id,
            tool=tool_name,
            input_hash=input_hash,
            output_ref=output_ref,
            status=status,
            latency=latency,
            idempotency_key=idempotency_key or f"EXEC-{uuid.uuid4().hex[:12]}",
            created_at=datetime.now(UTC),
        )
        self.session.add(exec_row)
        await self.session.flush()
