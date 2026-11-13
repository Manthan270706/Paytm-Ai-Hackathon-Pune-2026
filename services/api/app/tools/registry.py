import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.schemas import (
    ApplyCaseUpdateInput,
    ApplyCaseUpdateOutput,
    AssignCaseInput,
    AssignCaseOutput,
    CalculateDiscrepancyInput,
    CalculateDiscrepancyOutput,
    CreateSupportCaseInput,
    CreateSupportCaseOutput,
    FindTransactionsInput,
    FindTransactionsOutput,
    GetMerchantContextInput,
    GetMerchantContextOutput,
    GetSettlementEntriesInput,
    GetSettlementEntriesOutput,
    RequestApprovalInput,
    RequestApprovalOutput,
    RequestSettlementResyncInput,
    RequestSettlementResyncOutput,
    SendMerchantUpdateInput,
    SendMerchantUpdateOutput,
    VerifyResolutionInput,
    VerifyResolutionOutput,
)

TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound=BaseModel)


@dataclass
class ToolContext:
    """Server-side execution context. Merchant scope is bound here, never from LLM input."""

    merchant_id: uuid.UUID
    session: AsyncSession | None = None
    verifier_session: AsyncSession | None = None
    user_id: uuid.UUID | None = None


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    runner: Callable[[Any, ToolContext], Any]


# ------------------------------------------------------------------------------
# Tool Stubs (raising NotImplementedError or returning mock structure)
# ------------------------------------------------------------------------------
async def run_get_merchant_context(
    inp: GetMerchantContextInput, ctx: ToolContext
) -> GetMerchantContextOutput:
    raise NotImplementedError("TODO: Tool implementation in Phase 2/3")


async def run_find_transactions(
    inp: FindTransactionsInput, ctx: ToolContext
) -> FindTransactionsOutput:
    raise NotImplementedError("TODO: Tool implementation in Phase 2/3")


async def run_get_settlement_entries(
    inp: GetSettlementEntriesInput, ctx: ToolContext
) -> GetSettlementEntriesOutput:
    raise NotImplementedError("TODO: Tool implementation in Phase 2/3")


async def run_calculate_discrepancy(
    inp: CalculateDiscrepancyInput, ctx: ToolContext
) -> CalculateDiscrepancyOutput:
    raise NotImplementedError("TODO: Tool implementation in Phase 2/3")


async def run_create_support_case(
    inp: CreateSupportCaseInput, ctx: ToolContext
) -> CreateSupportCaseOutput:
    raise NotImplementedError("TODO: Tool implementation in Phase 2/3")


async def run_assign_case(inp: AssignCaseInput, ctx: ToolContext) -> AssignCaseOutput:
    raise NotImplementedError("TODO: Tool implementation in Phase 2/3")


async def run_request_approval(
    inp: RequestApprovalInput, ctx: ToolContext
) -> RequestApprovalOutput:
    raise NotImplementedError("TODO: Tool implementation in Phase 2/3")


async def run_request_settlement_resync(
    inp: RequestSettlementResyncInput, ctx: ToolContext
) -> RequestSettlementResyncOutput:
    raise NotImplementedError("TODO: Tool implementation in Phase 2/3")


async def run_apply_case_update(
    inp: ApplyCaseUpdateInput, ctx: ToolContext
) -> ApplyCaseUpdateOutput:
    raise NotImplementedError("TODO: Tool implementation in Phase 2/3")


async def run_verify_resolution(
    inp: VerifyResolutionInput, ctx: ToolContext
) -> VerifyResolutionOutput:
    raise NotImplementedError("TODO: Tool implementation in Phase 2/3")


async def run_send_merchant_update(
    inp: SendMerchantUpdateInput, ctx: ToolContext
) -> SendMerchantUpdateOutput:
    raise NotImplementedError("TODO: Tool implementation in Phase 2/3")


# ------------------------------------------------------------------------------
# The 11 Allowlisted PRD Tools Registry
# ------------------------------------------------------------------------------
ALL_TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="get_merchant_context",
        description="Returns allowed merchant scope from the session; read-only.",
        input_schema=GetMerchantContextInput,
        output_schema=GetMerchantContextOutput,
        runner=run_get_merchant_context,
    ),
    ToolDefinition(
        name="find_transactions",
        description="Search transactions by date, amount, order/transaction ref; tenant-scoped.",
        input_schema=FindTransactionsInput,
        output_schema=FindTransactionsOutput,
        runner=run_find_transactions,
    ),
    ToolDefinition(
        name="get_settlement_entries",
        description="Fetch settlement entries with source_type; tenant-scoped.",
        input_schema=GetSettlementEntriesInput,
        output_schema=GetSettlementEntriesOutput,
        runner=run_get_settlement_entries,
    ),
    ToolDefinition(
        name="calculate_discrepancy",
        description="Compute Decimal totals, discrepancy, SLA reason code and trace.",
        input_schema=CalculateDiscrepancyInput,
        output_schema=CalculateDiscrepancyOutput,
        runner=run_calculate_discrepancy,
    ),
    ToolDefinition(
        name="create_support_case",
        description="Create operational support case; returns case ID; no money movement.",
        input_schema=CreateSupportCaseInput,
        output_schema=CreateSupportCaseOutput,
        runner=run_create_support_case,
    ),
    ToolDefinition(
        name="assign_case",
        description="Assign support case to internal queue; role checked; appends audit event.",
        input_schema=AssignCaseInput,
        output_schema=AssignCaseOutput,
        runner=run_assign_case,
    ),
    ToolDefinition(
        name="request_approval",
        description="Creates approval storing case version and action hash.",
        input_schema=RequestApprovalInput,
        output_schema=RequestApprovalOutput,
        runner=run_request_approval,
    ),
    ToolDefinition(
        name="request_settlement_resync",
        description="Calls mock Settlement Ops adapter; policy-gated by threshold; idempotent.",
        input_schema=RequestSettlementResyncInput,
        output_schema=RequestSettlementResyncOutput,
        runner=run_request_settlement_resync,
    ),
    ToolDefinition(
        name="apply_case_update",
        description="Update case state machine and notes with optimistic version check.",
        input_schema=ApplyCaseUpdateInput,
        output_schema=ApplyCaseUpdateOutput,
        runner=run_apply_case_update,
    ),
    ToolDefinition(
        name="verify_resolution",
        description="Fresh read via read-only role; returns PASS/FAIL with before/after evidence.",
        input_schema=VerifyResolutionInput,
        output_schema=VerifyResolutionOutput,
        runner=run_verify_resolution,
    ),
    ToolDefinition(
        name="send_merchant_update",
        description="Sends notification to merchant in preferred language; consent checked.",
        input_schema=SendMerchantUpdateInput,
        output_schema=SendMerchantUpdateOutput,
        runner=run_send_merchant_update,
    ),
]

TOOL_REGISTRY: dict[str, ToolDefinition] = {t.name: t for t in ALL_TOOLS}
