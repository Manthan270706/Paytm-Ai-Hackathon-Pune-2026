import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Query

from app.api.v1.schemas import TransactionDetailResponse, TransactionItemResponse
from app.core.response import success_response

router = APIRouter()


@router.get("/transactions", summary="Tenant-scoped transaction search")
async def list_transactions(
    status: str | None = Query(None, description="Filter by status: SUCCESS, FAILED, PENDING"),
    order_id: str | None = Query(None, description="Filter by Order ID"),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    mock_merchant_id = uuid.uuid4()
    items = [
        TransactionItemResponse(
            id=uuid.uuid4(),
            merchant_id=mock_merchant_id,
            provider="PAYTM",
            provider_txn_id="TXN_78456321",
            order_id="ORD_20261112_01",
            amount=Decimal("6000.00"),
            currency="INR",
            status="SUCCESS",
            txn_time=datetime.now(UTC),
            source_type="SYNTHETIC_DEMO",
        ).model_dump(),
        TransactionItemResponse(
            id=uuid.uuid4(),
            merchant_id=mock_merchant_id,
            provider="PAYTM",
            provider_txn_id="TXN_78456320",
            order_id="ORD_20261112_02",
            amount=Decimal("9000.00"),
            currency="INR",
            status="SUCCESS",
            txn_time=datetime.now(UTC),
            source_type="SYNTHETIC_DEMO",
        ).model_dump(),
    ]
    return success_response(
        data={"items": items, "total": len(items)}, source_type="SYNTHETIC_DEMO"
    )


@router.get("/transactions/{transaction_id}", summary="Tenant-scoped transaction detail")
async def get_transaction(transaction_id: uuid.UUID) -> dict:
    return success_response(
        data=TransactionDetailResponse(
            id=transaction_id,
            merchant_id=uuid.uuid4(),
            provider="PAYTM",
            provider_txn_id="TXN_78456321",
            order_id="ORD_20261112_01",
            amount=Decimal("6000.00"),
            currency="INR",
            status="SUCCESS",
            txn_time=datetime.now(UTC),
            source_type="SYNTHETIC_DEMO",
            settlement_status="UNSETTLED",
            settlement_batch_ref="BATCH_20261112_01",
        ).model_dump(),
        source_type="SYNTHETIC_DEMO",
    )
