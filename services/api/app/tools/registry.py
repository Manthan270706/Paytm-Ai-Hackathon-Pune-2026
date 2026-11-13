import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SettlementBatch
from app.db.scoped_repository import ScopedRepository
from app.domain.reconciliation import reconcile
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
    SettlementEntryRecord,
    TransactionRecord,
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
# Tool Implementations (P3-A1 Investigation Wiring)
# ------------------------------------------------------------------------------
async def run_get_merchant_context(
    inp: GetMerchantContextInput, ctx: ToolContext
) -> GetMerchantContextOutput:
    if ctx.session is not None:
        repo = ScopedRepository(session=ctx.session, merchant_id=ctx.merchant_id)
        merchant = await repo.get_merchant()
        if merchant:
            return GetMerchantContextOutput(
                mid=merchant.external_mid,
                display_name=merchant.display_name,
                status=merchant.status,
                preferred_language="en",
                source_type="SYNTHETIC_DEMO",
            )
    return GetMerchantContextOutput(
        mid="MID_DEMO_TWOBITS",
        display_name="Two Bits Chai & Snacks",
        status="ACTIVE",
        preferred_language="en",
        source_type="SYNTHETIC_DEMO",
    )


async def run_find_transactions(
    inp: FindTransactionsInput, ctx: ToolContext
) -> FindTransactionsOutput:
    txns = []
    if ctx.session is not None:
        repo = ScopedRepository(session=ctx.session, merchant_id=ctx.merchant_id)
        if inp.order_id or inp.transaction_id:
            txn = await repo.get_transaction(
                provider_txn_id=inp.transaction_id,
                order_id=inp.order_id,
            )
            if txn:
                txns = [txn]
        else:
            txns = await repo.list_transactions()
            if inp.amount is not None:
                matched = [t for t in txns if t.amount == inp.amount]
                if matched:
                    txns = matched
            if inp.transaction_date is not None:
                matched_date = [t for t in txns if t.txn_time.date() == inp.transaction_date]
                if matched_date:
                    txns = matched_date

    records = [
        TransactionRecord(
            id=str(t.id),
            order_id=t.order_id,
            provider_txn_id=t.provider_txn_id,
            amount=t.amount,
            currency=t.currency,
            status=t.status,
            txn_time=t.txn_time,
            source_type=t.source_type,
        )
        for t in txns
    ]
    return FindTransactionsOutput(
        transactions=records,
        source_ids=[str(t.id) for t in txns],
    )


async def run_get_settlement_entries(
    inp: GetSettlementEntriesInput, ctx: ToolContext
) -> GetSettlementEntriesOutput:
    entries = []
    batch_ref_str = "BATCH_20261112_01"
    if ctx.session is not None:
        repo = ScopedRepository(session=ctx.session, merchant_id=ctx.merchant_id)
        if inp.batch_ref:
            batch = await repo.get_settlement_batch(inp.batch_ref)
            if batch:
                entries = await repo.list_settlement_entries(batch_id=batch.id)
                batch_ref_str = batch.batch_ref
        else:
            entries = await repo.list_settlement_entries()
            if entries:
                first_batch = (
                    await ctx.session.execute(
                        select(SettlementBatch).where(SettlementBatch.id == entries[0].batch_id)
                    )
                ).scalar_one_or_none()
                if first_batch:
                    batch_ref_str = first_batch.batch_ref

    records = [
        SettlementEntryRecord(
            id=str(e.id),
            batch_ref=batch_ref_str,
            transaction_id=str(e.transaction_id) if e.transaction_id else None,
            amount=e.amount,
            entry_type=e.entry_type,
            status=e.status,
            source_type=e.source_type,
        )
        for e in entries
    ]
    return GetSettlementEntriesOutput(
        entries=records,
        source_ids=[str(e.id) for e in entries],
    )


async def run_calculate_discrepancy(
    inp: CalculateDiscrepancyInput, ctx: ToolContext
) -> CalculateDiscrepancyOutput:
    if ctx.session is not None:
        repo = ScopedRepository(session=ctx.session, merchant_id=ctx.merchant_id)
        if inp.transaction_ids:
            captures = []
            for tid in inp.transaction_ids:
                try:
                    t = await repo.get_transaction_by_id(uuid.UUID(tid))
                    if t:
                        captures.append(t)
                except ValueError:
                    pass
        else:
            captures = await repo.list_transactions()

        if inp.settlement_entry_ids:
            entries = []
            for eid in inp.settlement_entry_ids:
                try:
                    e = await repo.get_settlement_entry(uuid.UUID(eid))
                    if e:
                        entries.append(e)
                except ValueError:
                    pass
        else:
            entries = await repo.list_settlement_entries()

        fee_rules = await repo.get_fee_rules()
        fee_records = []
        if fee_rules:
            for r in fee_rules:
                fee_records.append(
                    {
                        "id": str(r.id),
                        "amount": getattr(r, "flat_amount", Decimal("0.00")),
                        "status": "DOCUMENTED",
                        "source_type": getattr(r, "source_type", "SYNTHETIC_DEMO"),
                    }
                )
        else:
            fee_records = [
                {
                    "id": str(uuid.uuid4()),
                    "amount": Decimal("0.00"),
                    "status": "DOCUMENTED",
                    "source_type": "SYNTHETIC_DEMO",
                }
            ]

        now = datetime.now(UTC)
        expected_date = (now - timedelta(days=1)).date()
        if entries:
            first_batch = (
                await ctx.session.execute(
                    select(SettlementBatch).where(SettlementBatch.id == entries[0].batch_id)
                )
            ).scalar_one_or_none()
            if first_batch and first_batch.expected_settlement_date:
                batch_dt = first_batch.expected_settlement_date
                if batch_dt.tzinfo is None:
                    batch_dt = batch_dt.replace(tzinfo=UTC)
                if batch_dt > now:
                    expected_date = batch_dt.date()
                else:
                    expected_date = (now - timedelta(days=1)).date()

        # Map captures to dicts for reconcile
        recon_captures = [
            {
                "id": str(t.id),
                "amount": t.amount,
                "status": t.status,
                "provider_txn_id": t.provider_txn_id,
                "order_id": t.order_id,
                "source_type": t.source_type,
            }
            for t in captures
        ]

        # Map entries with linked transaction references
        txn_map = {t.id: t for t in captures}
        recon_entries = []
        for e in entries:
            t = txn_map.get(e.transaction_id) if e.transaction_id else None
            recon_entries.append({
                "id": str(e.id),
                "amount": e.amount,
                "status": e.status,
                "provider_txn_id": t.provider_txn_id if t else str(e.transaction_id),
                "order_id": t.order_id if t else None,
                "source_type": e.source_type,
            })

        now = datetime.now(UTC)
        result = reconcile(
            captures=recon_captures,
            refunds=[],
            fees=fee_records,
            taxes=[],
            entries=recon_entries,
            expected_settlement_date=expected_date,
            now=now,
        )

        effective_reason = result.reason_code
        if expected_date < now.date() and result.discrepancy > 0:
            effective_reason = "OVERDUE"

        return CalculateDiscrepancyOutput(
            expected_net=result.expected_net,
            observed=result.observed,
            discrepancy=result.discrepancy,
            reason_code=effective_reason,
            trace=result.trace,
            source_ids=result.source_ids,
        )

    # Fallback for sessionless execution
    exp = Decimal("15000.00")
    obs = Decimal("9000.00")
    return CalculateDiscrepancyOutput(
        expected_net=exp,
        observed=obs,
        discrepancy=exp - obs,
        reason_code="OVERDUE",
        trace={"currency": "INR", "expected_settlement_date": "2026-11-12", "components": {}},
        source_ids=[],
    )


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
