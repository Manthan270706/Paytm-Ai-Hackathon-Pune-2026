import base64
import hashlib
import json
import uuid

import pytest
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.db.models import WebhookEvent
from app.main import app
from app.tests.conftest import shared_session_factory

pytestmark = pytest.mark.asyncio

PAYTM_IV = b"@@@@&&&&####$$$$"


def generate_paytm_checksum(params: dict[str, object], key: str, salt: str = "aB3x") -> str:
    """Helper generating standard Paytm AES-CBC PKCS7 encrypted checksum."""
    parameter_string = "|".join(str(params[k]) for k in sorted(params))
    digest = hashlib.sha256(f"{parameter_string}|{salt}".encode()).hexdigest() + salt
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded = padder.update(digest.encode("ascii")) + padder.finalize()
    encryptor = Cipher(
        algorithms.AES(key.encode("utf-8")), modes.CBC(PAYTM_IV)
    ).encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(ciphertext).decode("ascii")


async def test_webhook_with_valid_cryptographic_signature_accepted_and_stored() -> None:
    """Acceptance: a test event is stored once with signature_valid recorded."""
    original_key = settings.PAYTM_MERCHANT_KEY
    test_key = "0123456789abcdef"
    settings.PAYTM_MERCHANT_KEY = test_key

    try:
        event_id = f"EVT_STAGING_{uuid.uuid4().hex[:12]}"
        payload_dict = {
            "MID": "DIY12386817555501617",
            "ORDERID": f"ORD_{uuid.uuid4().hex[:8]}",
            "STATUS": "TXN_SUCCESS",
            "TXNAMOUNT": "6000.00",
            "event_id": event_id,
        }
        checksum = generate_paytm_checksum(payload_dict, test_key)
        payload_dict["CHECKSUMHASH"] = checksum
        raw_bytes = json.dumps(payload_dict).encode("utf-8")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/webhooks/paytm",
                content=raw_bytes,
                headers={"Content-Type": "application/json"},
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["received"] is True
            assert data["event_id"] == event_id
            assert data["deduplicated"] is True
            assert data["signature_valid"] is True
            assert data["status"] == "PROCESSED"

            # Query database to confirm WebhookEvent is stored with signature_valid=True
            async with shared_session_factory() as session:
                stmt = select(WebhookEvent).where(WebhookEvent.event_id == event_id)
                db_event = (await session.execute(stmt)).scalar_one_or_none()
                assert db_event is not None
                assert db_event.signature_valid is True
                assert db_event.status == "PROCESSED"
                assert db_event.payload_hash == hashlib.sha256(raw_bytes).hexdigest()
    finally:
        settings.PAYTM_MERCHANT_KEY = original_key


async def test_webhook_with_invalid_signature_rejected() -> None:
    """Verify that webhooks with invalid signatures are rejected with 400 Bad Request."""
    original_key = settings.PAYTM_MERCHANT_KEY
    settings.PAYTM_MERCHANT_KEY = "0123456789abcdef"

    try:
        event_id = f"EVT_INVALID_{uuid.uuid4().hex[:8]}"
        payload_dict = {
            "MID": "DIY12386817555501617",
            "ORDERID": "ORD_TAMPERED",
            "STATUS": "TXN_FAILURE",
            "event_id": event_id,
            "CHECKSUMHASH": "tampered_invalid_signature_xyz",
        }
        raw_bytes = json.dumps(payload_dict).encode("utf-8")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/webhooks/paytm",
                content=raw_bytes,
                headers={"Content-Type": "application/json"},
            )
            assert resp.status_code == 400
            assert "signature verification failed" in resp.json()["detail"].lower()

            # Ensure event was not recorded
            async with shared_session_factory() as session:
                stmt = select(WebhookEvent).where(WebhookEvent.event_id == event_id)
                db_event = (await session.execute(stmt)).scalar_one_or_none()
                assert db_event is None
    finally:
        settings.PAYTM_MERCHANT_KEY = original_key


async def test_webhook_deduplication_duplicate_processed_once() -> None:
    """Verify that replay events are deduplicated and not reprocessed."""
    original_key = settings.PAYTM_MERCHANT_KEY
    test_key = "0123456789abcdef"
    settings.PAYTM_MERCHANT_KEY = test_key

    try:
        event_id = f"EVT_DEDUPE_{uuid.uuid4().hex[:12]}"
        payload_dict = {
            "MID": "DIY12386817555501617",
            "ORDERID": "ORD_DEDUPE_001",
            "STATUS": "TXN_SUCCESS",
            "event_id": event_id,
        }
        checksum = generate_paytm_checksum(payload_dict, test_key)
        payload_dict["CHECKSUMHASH"] = checksum
        raw_bytes = json.dumps(payload_dict).encode("utf-8")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # First submission
            resp1 = await client.post(
                "/api/v1/webhooks/paytm",
                content=raw_bytes,
                headers={"Content-Type": "application/json"},
            )
            assert resp1.status_code == 200
            assert resp1.json()["data"]["deduplicated"] is True
            assert resp1.json()["data"]["status"] == "PROCESSED"

            # Duplicate submission with identical event_id
            resp2 = await client.post(
                "/api/v1/webhooks/paytm",
                content=raw_bytes,
                headers={"Content-Type": "application/json"},
            )
            assert resp2.status_code == 200
            data2 = resp2.json()["data"]
            assert data2["received"] is True
            assert data2["deduplicated"] is False
            assert data2["status"] == "DUPLICATE_IGNORED"

            # Verify in DB: exactly one event exists
            async with shared_session_factory() as session:
                stmt = select(WebhookEvent).where(WebhookEvent.event_id == event_id)
                events = (await session.execute(stmt)).scalars().all()
                assert len(events) == 1
    finally:
        settings.PAYTM_MERCHANT_KEY = original_key
