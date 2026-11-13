import base64
import hashlib
import json
from urllib.parse import urlencode

import pytest
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from sqlalchemy import select

from app.core.webhook import deduplicate_webhook, verify_paytm_signature
from app.db.models import WebhookEvent
from app.tests.conftest import shared_session_factory

MERCHANT_KEY = "0123456789abcdef"
PAYTM_IV = b"@@@@&&&&####$$$$"


def make_checksum(params: dict[str, object], salt: str = "aB3x") -> str:
    parameter_string = "|".join(str(params[key]) for key in sorted(params))
    digest = hashlib.sha256(f"{parameter_string}|{salt}".encode()).hexdigest() + salt
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded = padder.update(digest.encode("ascii")) + padder.finalize()
    encryptor = Cipher(
        algorithms.AES(MERCHANT_KEY.encode("utf-8")), modes.CBC(PAYTM_IV)
    ).encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(ciphertext).decode("ascii")


def test_paytm_checksum_accepts_valid_json_and_form_payloads() -> None:
    params: dict[str, object] = {
        "ORDERID": "ORD-123",
        "STATUS": "TXN_SUCCESS",
        "MID": "MID-456",
    }
    checksum = make_checksum(params)

    json_payload = json.dumps({**params, "CHECKSUMHASH": checksum}).encode("utf-8")
    form_payload = urlencode({**params, "CHECKSUMHASH": checksum}).encode("ascii")

    assert verify_paytm_signature(json_payload, checksum, MERCHANT_KEY)
    assert verify_paytm_signature(form_payload, checksum, MERCHANT_KEY)


def test_paytm_checksum_rejects_tampered_malformed_or_ambiguous_payloads() -> None:
    params = {"ORDERID": "ORD-123", "STATUS": "TXN_SUCCESS"}
    checksum = make_checksum(params)

    assert not verify_paytm_signature(
        b'{"ORDERID":"ORD-123","STATUS":"TXN_FAILURE"}', checksum, MERCHANT_KEY
    )
    assert not verify_paytm_signature(b"not-a-callback", checksum, MERCHANT_KEY)
    assert not verify_paytm_signature(
        b'{"ORDERID":"one","ORDERID":"two"}', checksum, MERCHANT_KEY
    )
    assert not verify_paytm_signature(
        b'{"ORDERID":"ORD-123","STATUS":"TXN_SUCCESS"}', "invalid", MERCHANT_KEY
    )


@pytest.mark.asyncio
async def test_webhook_event_id_is_recorded_once() -> None:
    async with shared_session_factory() as session:
        assert await deduplicate_webhook("evt_p4_c1_once", session)
        assert not await deduplicate_webhook("evt_p4_c1_once", session)


@pytest.mark.asyncio
async def test_webhook_event_id_validation() -> None:
    async with shared_session_factory() as session:
        assert not await deduplicate_webhook("", session)
        assert not await deduplicate_webhook("x" * 101, session)


@pytest.mark.asyncio
async def test_webhook_stores_raw_payload_hash() -> None:
    payload = b'{"ORDERID":"ORD-789"}'
    async with shared_session_factory() as session:
        assert await deduplicate_webhook("evt_p4_c1_payload", session, payload_bytes=payload)
        result = await session.execute(
            select(WebhookEvent).where(WebhookEvent.event_id == "evt_p4_c1_payload")
        )
        event = result.scalar_one()

    assert event.payload_hash == hashlib.sha256(payload).hexdigest()
