"""Merchant-scoped repository queries and writes."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.db.models import (
    CaseEvent,
    Conversation,
    FeeRule,
    Merchant,
    SettlementBatch,
    SettlementEntry,
    SupportCase,
    Transaction,
)


class ScopedRepository:
    """Data access bound to exactly one authenticated merchant."""

    _CASE_UPDATE_FIELDS = frozenset({"category", "priority", "queue", "summary", "followup_at"})

    def __init__(self, session: AsyncSession, merchant_id: uuid.UUID) -> None:
        if not isinstance(merchant_id, uuid.UUID):
            raise ValueError("ScopedRepository requires a bound merchant UUID")
        self.session = session
        self.merchant_id = merchant_id

    async def get_merchant(self) -> Merchant | None:
        result = await self.session.execute(select(Merchant).where(Merchant.id == self.merchant_id))
        return result.scalar_one_or_none()

    async def get_transaction(
        self,
        provider_txn_id: str | None = None,
        order_id: str | None = None,
    ) -> Transaction | None:
        filters = []
        if provider_txn_id:
            filters.append(Transaction.provider_txn_id == provider_txn_id)
        if order_id:
            filters.append(Transaction.order_id == order_id)
        if not filters:
            return None
        stmt = select(Transaction).where(Transaction.merchant_id == self.merchant_id, *filters)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_transaction_by_id(self, transaction_id: uuid.UUID) -> Transaction | None:
        stmt = select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.merchant_id == self.merchant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_transactions(
        self,
        status: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[Transaction]:
        stmt = select(Transaction).where(Transaction.merchant_id == self.merchant_id)
        if status:
            stmt = stmt.where(Transaction.status == status)
        if start_time:
            stmt = stmt.where(Transaction.txn_time >= start_time)
        if end_time:
            stmt = stmt.where(Transaction.txn_time <= end_time)
        result = await self.session.execute(stmt.order_by(Transaction.txn_time.desc()))
        return list(result.scalars().all())

    async def get_settlement_batch(self, batch_ref: str) -> SettlementBatch | None:
        stmt = select(SettlementBatch).where(
            SettlementBatch.batch_ref == batch_ref,
            SettlementBatch.merchant_id == self.merchant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_settlement_entry(self, entry_id: uuid.UUID) -> SettlementEntry | None:
        stmt = (
            select(SettlementEntry)
            .join(SettlementBatch, SettlementEntry.batch_id == SettlementBatch.id)
            .where(
                SettlementEntry.id == entry_id,
                SettlementBatch.merchant_id == self.merchant_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_settlement_entries(
        self,
        batch_id: uuid.UUID | None = None,
    ) -> list[SettlementEntry]:
        stmt = (
            select(SettlementEntry)
            .join(SettlementBatch, SettlementEntry.batch_id == SettlementBatch.id)
            .where(SettlementBatch.merchant_id == self.merchant_id)
        )
        if batch_id is not None:
            stmt = stmt.where(SettlementEntry.batch_id == batch_id)
        result = await self.session.execute(stmt.order_by(SettlementEntry.created_at))
        return list(result.scalars().all())

    async def get_case(self, case_id: uuid.UUID) -> SupportCase | None:
        stmt = select(SupportCase).where(
            SupportCase.id == case_id,
            SupportCase.merchant_id == self.merchant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_cases(self, status: str | None = None) -> list[SupportCase]:
        stmt = select(SupportCase).where(SupportCase.merchant_id == self.merchant_id)
        if status:
            stmt = stmt.where(SupportCase.status == status)
        result = await self.session.execute(stmt.order_by(SupportCase.created_at.desc()))
        return list(result.scalars().all())

    async def get_conversation(self, conversation_id: uuid.UUID) -> Conversation | None:
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.merchant_id == self.merchant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_case(
        self,
        case_number: str,
        category: str,
        priority: str,
        summary: str,
        queue: str = "SETTLEMENTS",
        idempotency_key: str | None = None,
    ) -> SupportCase:
        if not idempotency_key or not idempotency_key.strip():
            raise ValidationError("Idempotency-Key is required for case creation")
        stmt = select(SupportCase).where(
            SupportCase.merchant_id == self.merchant_id,
            SupportCase.idempotency_key == idempotency_key,
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            return existing

        case = SupportCase(
            id=uuid.uuid4(),
            merchant_id=self.merchant_id,
            case_number=case_number,
            category=category,
            priority=priority,
            summary=summary,
            queue=queue,
            idempotency_key=idempotency_key,
            status="NEW",
            version=1,
        )
        self.session.add(case)
        await self.session.flush()
        return case

    async def update_case(
        self,
        case_id: uuid.UUID,
        expected_version: int,
        updates: dict[str, Any],
    ) -> SupportCase:
        case = await self.get_case(case_id)
        if case is None:
            raise NotFoundError("Case not found in merchant scope")
        if case.version != expected_version:
            raise ConflictError(
                "Case version changed",
                details={"expected_version": expected_version, "current_version": case.version},
            )
        invalid_fields = set(updates) - self._CASE_UPDATE_FIELDS
        if invalid_fields:
            raise ValidationError(
                "Case update contains protected or unsupported fields",
                details={"fields": sorted(invalid_fields)},
            )
        for field, value in updates.items():
            setattr(case, field, value)
        case.version += 1
        case.updated_at = datetime.now(UTC)
        await self.session.flush()
        return case

    async def create_case_event(
        self,
        case_id: uuid.UUID,
        actor: str,
        event_type: str,
        payload: dict[str, Any],
        from_status: str | None = None,
        to_status: str | None = None,
    ) -> CaseEvent:
        case = await self.get_case(case_id)
        if case is None:
            raise NotFoundError("Case not found in merchant scope")
        event = CaseEvent(
            id=uuid.uuid4(),
            case_id=case.id,
            actor=actor,
            event_type=event_type,
            payload=payload,
            from_status=from_status,
            to_status=to_status,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def get_fee_rules(self) -> list[FeeRule]:
        stmt = select(FeeRule).where(
            FeeRule.merchant_id == self.merchant_id,
            FeeRule.active.is_(True),
        )
        result = await self.session.execute(stmt.order_by(FeeRule.created_at))
        return list(result.scalars().all())
