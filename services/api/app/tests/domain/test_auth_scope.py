import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.auth import is_role_allowed, parse_demo_token
from app.core.exceptions import NotFoundError, ValidationError
from app.core.redaction import (
    RedactionResult,
    mask_account,
    mask_phone,
    redact,
    redact_dict,
    redact_pii,
)
from app.db.base import Base
from app.db.models import (
    Conversation,
    FeeRule,
    Merchant,
    SettlementBatch,
    SettlementEntry,
    SupportCase,
    Transaction,
)
from app.db.scoped_repository import ScopedRepository


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db_session:
        yield db_session
    await engine.dispose()


def test_redact_credentials_and_card_number_like_text() -> None:
    result = redact(
        "OTP: 123456, UPI PIN 4321, CVV: 123, card 4111 1111 1111 1111"
    )

    assert isinstance(result, RedactionResult)
    assert "123456" not in result.clean_text
    assert "4321" not in result.clean_text
    assert "CVV: 123" not in result.clean_text
    assert "4111" not in result.clean_text
    assert set(result.redacted_types) == {"CARD", "CVV", "OTP", "PIN"}


def test_redact_personal_identifiers_and_leave_normal_text_unchanged() -> None:
    result = redact("Call me at +91 9876543210; PAN ABCDE1234F. Thank you.")

    assert "9876543210" not in result.clean_text
    assert "ABCDE1234F" not in result.clean_text
    assert "Thank you." in result.clean_text
    assert set(result.redacted_types) == {"PAN", "PHONE"}
    assert redact("Payment is delayed; please share the order ID.").clean_text == (
        "Payment is delayed; please share the order ID."
    )


def test_redact_dict_recurses_and_masks_sensitive_keys() -> None:
    result = redact_dict(
        {
            "message": "Your OTP is 556677",
            "credentials": {"bank_password": "private value", "note": "CVV 987"},
            "items": [{"pin": 4321}],
            "amount": "₹6000",
        }
    )

    assert "556677" not in result["message"]
    assert result["credentials"]["bank_password"] == "[REDACTED_BANK_PASSWORD]"
    assert "987" not in result["credentials"]["note"]
    assert result["items"][0]["pin"] == "[REDACTED_PIN]"
    assert result["amount"] == "₹6000"


def test_legacy_redaction_helpers_mask_phone_and_account() -> None:
    assert mask_phone("+91 98765 43210").endswith("3210")
    assert "98765" not in mask_phone("+91 98765 43210")
    assert mask_account("123456789012").endswith("9012")
    assert "12345678" not in mask_account("123456789012")
    assert "OTP" in redact_pii("OTP 654321")


def test_role_parsing_and_authorization_default_deny() -> None:
    identity = parse_demo_token("demo-token-support_agent-1234-abcd")

    assert identity is not None
    assert identity.role == "SUPPORT_AGENT"
    assert parse_demo_token("some-support-token") is None
    assert parse_demo_token("demo-token-root-1234") is None
    assert is_role_allowed("SUPPORT_AGENT", ("SUPPORT_AGENT",)) is True
    assert is_role_allowed("MERCHANT", ("SUPPORT_AGENT",)) is False
    assert is_role_allowed("ROOT", ("SUPERVISOR",)) is False
    assert is_role_allowed("SUPERVISOR", ()) is False


@pytest.mark.asyncio
async def test_scoped_repository_hides_other_merchants_resources(
    session: AsyncSession,
) -> None:
    merchant_a_id = uuid.uuid4()
    merchant_b_id = uuid.uuid4()
    txn_a_id = uuid.uuid4()
    txn_b_id = uuid.uuid4()
    batch_a_id = uuid.uuid4()
    batch_b_id = uuid.uuid4()
    entry_a_id = uuid.uuid4()
    entry_b_id = uuid.uuid4()
    case_a_id = uuid.uuid4()
    case_b_id = uuid.uuid4()
    conversation_a_id = uuid.uuid4()
    conversation_b_id = uuid.uuid4()
    now = datetime.now(UTC)
    session.add_all(
        [
            Merchant(id=merchant_a_id, display_name="Merchant A", masked_phone="******0001"),
            Merchant(id=merchant_b_id, display_name="Merchant B", masked_phone="******0002"),
            Transaction(
                id=txn_a_id,
                merchant_id=merchant_a_id,
                provider_txn_id="provider-a",
                order_id="order-a",
                amount=Decimal("100.00"),
                currency="INR",
                status="SUCCESS",
                txn_time=now,
            ),
            Transaction(
                id=txn_b_id,
                merchant_id=merchant_b_id,
                provider_txn_id="provider-b",
                order_id="order-b",
                amount=Decimal("200.00"),
                currency="INR",
                status="SUCCESS",
                txn_time=now,
            ),
            SettlementBatch(
                id=batch_a_id,
                merchant_id=merchant_a_id,
                batch_ref="batch-a",
                date=date.today(),
                expected_settlement_date=now,
                gross=Decimal("100.00"),
                fees=Decimal("0.00"),
                refunds=Decimal("0.00"),
                net=Decimal("100.00"),
            ),
            SettlementBatch(
                id=batch_b_id,
                merchant_id=merchant_b_id,
                batch_ref="batch-b",
                date=date.today(),
                expected_settlement_date=now,
                gross=Decimal("200.00"),
                fees=Decimal("0.00"),
                refunds=Decimal("0.00"),
                net=Decimal("200.00"),
            ),
            SettlementEntry(
                id=entry_a_id, batch_id=batch_a_id, amount=Decimal("100.00")
            ),
            SettlementEntry(
                id=entry_b_id, batch_id=batch_b_id, amount=Decimal("200.00")
            ),
            SupportCase(
                id=case_a_id,
                merchant_id=merchant_a_id,
                case_number="A-1",
                summary="A case",
                idempotency_key="a-key",
            ),
            SupportCase(
                id=case_b_id,
                merchant_id=merchant_b_id,
                case_number="B-1",
                summary="B case",
                idempotency_key="b-key",
            ),
            Conversation(id=conversation_a_id, merchant_id=merchant_a_id),
            Conversation(id=conversation_b_id, merchant_id=merchant_b_id),
            FeeRule(
                id=uuid.uuid4(),
                merchant_id=merchant_a_id,
                rule_ref="fee-a",
                rate_percent=Decimal("0.00"),
                flat_amount=Decimal("0.00"),
            ),
            FeeRule(
                id=uuid.uuid4(),
                merchant_id=merchant_b_id,
                rule_ref="fee-b",
                rate_percent=Decimal("0.00"),
                flat_amount=Decimal("0.00"),
            ),
        ]
    )
    await session.flush()
    repo = ScopedRepository(session=session, merchant_id=merchant_a_id)

    assert (await repo.get_merchant()) is not None
    assert await repo.get_transaction_by_id(txn_a_id) is not None
    assert await repo.get_transaction_by_id(txn_b_id) is None
    assert await repo.get_transaction(provider_txn_id="provider-b") is None
    assert [txn.provider_txn_id for txn in await repo.list_transactions()] == ["provider-a"]
    assert await repo.get_settlement_batch("batch-b") is None
    assert await repo.get_settlement_entry(entry_b_id) is None
    assert [entry.id for entry in await repo.list_settlement_entries()] == [entry_a_id]
    assert await repo.get_case(case_b_id) is None
    assert [case.id for case in await repo.list_cases()] == [case_a_id]
    assert await repo.get_conversation(conversation_b_id) is None
    assert [rule.rule_ref for rule in await repo.get_fee_rules()] == ["fee-a"]


@pytest.mark.asyncio
async def test_scoped_case_writes_require_scope_version_and_idempotency(
    session: AsyncSession,
) -> None:
    merchant_id = uuid.uuid4()
    other_merchant_id = uuid.uuid4()
    session.add_all(
        [
            Merchant(id=merchant_id, display_name="Merchant", masked_phone="******0001"),
            Merchant(id=other_merchant_id, display_name="Other", masked_phone="******0002"),
        ]
    )
    session.add(
        SupportCase(
            id=uuid.uuid4(),
            merchant_id=other_merchant_id,
            case_number="OTHER-1",
            summary="Other case",
            idempotency_key="other-key",
        )
    )
    await session.flush()
    repo = ScopedRepository(session=session, merchant_id=merchant_id)

    with pytest.raises(ValidationError):
        await repo.create_case("A-1", "PAYOUT", "P2", "Summary")
    case = await repo.create_case(
        "A-1", "PAYOUT", "P2", "Summary", idempotency_key="my-key"
    )
    duplicate = await repo.create_case(
        "A-2", "PAYOUT", "P1", "Retry", idempotency_key="my-key"
    )
    assert duplicate.id == case.id
    updated = await repo.update_case(case.id, expected_version=1, updates={"priority": "P1"})
    assert updated.version == 2
    with pytest.raises(ValidationError):
        await repo.update_case(
            case.id, expected_version=2, updates={"merchant_id": other_merchant_id}
        )
    with pytest.raises(NotFoundError):
        await repo.update_case(uuid.uuid4(), expected_version=1, updates={"priority": "P1"})
