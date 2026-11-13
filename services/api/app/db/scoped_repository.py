import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CaseEvent,
    FeeRule,
    Merchant,
    SettlementBatch,
    SettlementEntry,
    SupportCase,
    Transaction,
)


class ScopedRepository:
    """Tenant-scoped data access layer.

    All queries execute with an explicit merchant_id filter to enforce strict multi-tenant
    isolation. Repositories exposing unscoped queries are strictly prohibited in the agent workflow.

    Frozen signature per BUILD_PLAN.md §4. Implemented by Codex in task P2-C3.
    """

    def __init__(self, session: AsyncSession, merchant_id: uuid.UUID) -> None:
        self.session = session
        self.merchant_id = merchant_id

    async def get_merchant(self) -> Merchant | None:
        """Fetch current merchant record."""
        raise NotImplementedError("TODO(core): Codex task P2-C3")

    async def get_transaction(
        self,
        provider_txn_id: str | None = None,
        order_id: str | None = None,
    ) -> Transaction | None:
        """Fetch transaction scoped to this merchant."""
        raise NotImplementedError("TODO(core): Codex task P2-C3")

    async def list_transactions(
        self,
        status: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[Transaction]:
        """List transactions scoped to this merchant."""
        raise NotImplementedError("TODO(core): Codex task P2-C3")

    async def get_settlement_batch(self, batch_ref: str) -> SettlementBatch | None:
        """Fetch settlement batch scoped to this merchant."""
        raise NotImplementedError("TODO(core): Codex task P2-C3")

    async def list_settlement_entries(
        self,
        batch_id: uuid.UUID | None = None,
    ) -> list[SettlementEntry]:
        """List settlement entries scoped to this merchant."""
        raise NotImplementedError("TODO(core): Codex task P2-C3")

    async def get_case(self, case_id: uuid.UUID) -> SupportCase | None:
        """Fetch support case scoped to this merchant."""
        raise NotImplementedError("TODO(core): Codex task P2-C3")

    async def list_cases(self, status: str | None = None) -> list[SupportCase]:
        """List support cases scoped to this merchant."""
        raise NotImplementedError("TODO(core): Codex task P2-C3")

    async def create_case(
        self,
        case_number: str,
        category: str,
        priority: str,
        summary: str,
        queue: str = "SETTLEMENTS",
        idempotency_key: str | None = None,
    ) -> SupportCase:
        """Create new support case scoped to this merchant."""
        raise NotImplementedError("TODO(core): Codex task P2-C3")

    async def update_case(
        self,
        case_id: uuid.UUID,
        expected_version: int,
        updates: dict[str, Any],
    ) -> SupportCase:
        """Update case with optimistic version locking."""
        raise NotImplementedError("TODO(core): Codex task P2-C3")

    async def create_case_event(
        self,
        case_id: uuid.UUID,
        actor: str,
        event_type: str,
        payload: dict[str, Any],
        from_status: str | None = None,
        to_status: str | None = None,
    ) -> CaseEvent:
        """Append case event to audit timeline."""
        raise NotImplementedError("TODO(core): Codex task P2-C3")

    async def get_fee_rules(self) -> list[FeeRule]:
        """Fetch active fee rules scoped to this merchant."""
        raise NotImplementedError("TODO(core): Codex task P2-C3")
