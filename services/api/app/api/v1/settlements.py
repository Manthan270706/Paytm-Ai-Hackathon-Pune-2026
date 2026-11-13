import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import APIRouter

from app.api.v1.schemas import SettlementBatchResponse, SettlementEntryResponse
from app.core.response import success_response

router = APIRouter()


@router.get("/settlements", summary="Return settlement batches and entries")
async def list_settlements() -> dict:
    mock_batch_id = uuid.uuid4()
    mock_merchant_id = uuid.uuid4()
    batch = SettlementBatchResponse(
        id=mock_batch_id,
        merchant_id=mock_merchant_id,
        batch_ref="BATCH_20261112_01",
        date=date(2026, 11, 12),
        expected_settlement_date=datetime.now(UTC),
        gross=Decimal("9000.00"),
        fees=Decimal("0.00"),
        refunds=Decimal("0.00"),
        net=Decimal("9000.00"),
        status="PARTIAL",
        source_type="SYNTHETIC_DEMO",
        entries_count=1,
    )
    entry = SettlementEntryResponse(
        id=uuid.uuid4(),
        batch_id=mock_batch_id,
        transaction_id=uuid.uuid4(),
        amount=Decimal("9000.00"),
        entry_type="CAPTURE",
        status="SETTLED",
        source_type="SYNTHETIC_DEMO",
        created_at=datetime.now(UTC),
    )
    return success_response(
        data={
            "batches": [batch.model_dump()],
            "entries": [entry.model_dump()],
            "discrepancy_amount": Decimal("6000.00"),
            "reason_code": "OVERDUE",
        },
        source_type="SYNTHETIC_DEMO",
    )
