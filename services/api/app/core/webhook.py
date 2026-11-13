"""Paytm callback checksum verification and replay deduplication."""

import base64
import hashlib
import hmac
import json
from collections.abc import Sequence
from typing import Any
from urllib.parse import parse_qsl

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import WebhookEvent

_PAYTM_IV = b"@@@@&&&&####$$$$"


def _reject_duplicate_json_keys(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate callback parameter")
        result[key] = value
    return result


def _parse_callback(payload_bytes: bytes) -> dict[str, Any] | None:
    try:
        payload_text = payload_bytes.decode("utf-8")
        if payload_text.lstrip().startswith("{"):
            payload = json.loads(payload_text, object_pairs_hook=_reject_duplicate_json_keys)
            if not isinstance(payload, dict):
                return None
            return payload

        pairs = parse_qsl(payload_text, keep_blank_values=True, strict_parsing=True)
        payload = dict(pairs)
        if len(payload) != len(pairs):
            return None
        return payload
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None


def _paytm_parameter_string(params: dict[str, Any]) -> str | None:
    values: list[str] = []
    for key in sorted(params):
        value = params[key]
        if value is None or (isinstance(value, str) and value.lower() == "null"):
            values.append("")
        elif isinstance(value, (str, int, float, bool)):
            values.append(str(value))
        else:
            # Paytm checksums are defined over flat callback parameters.
            return None
    return "|".join(values)


def _decrypt_paytm_checksum(signature: str, merchant_key: str) -> bytes | None:
    try:
        key = merchant_key.encode("utf-8")
        if len(key) not in (16, 24, 32):
            return None
        encrypted = base64.b64decode(signature, validate=True)
        if not encrypted or len(encrypted) % (algorithms.AES.block_size // 8) != 0:
            return None

        decryptor = Cipher(algorithms.AES(key), modes.CBC(_PAYTM_IV)).decryptor()
        padded = decryptor.update(encrypted) + decryptor.finalize()
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        return unpadder.update(padded) + unpadder.finalize()
    except (ValueError, TypeError):
        return None


def verify_paytm_signature(
    payload_bytes: bytes,
    signature: str,
    merchant_key: str,
) -> bool:
    """Verify Paytm's encrypted SHA-256 checksum for JSON or form callback data.

    The Paytm SDK signs sorted parameter values joined by ``|``, appends a
    four-character salt, hashes with SHA-256, then encrypts the hash and salt
    with AES-CBC using the merchant key and Paytm's documented fixed IV.
    """
    if not payload_bytes or not signature or not merchant_key:
        return False

    params = _parse_callback(payload_bytes)
    if params is None:
        return False

    embedded_signature = params.pop("CHECKSUMHASH", None)
    if embedded_signature is not None and embedded_signature != signature:
        return False

    parameter_string = _paytm_parameter_string(params)
    if parameter_string is None:
        return False

    decrypted_checksum = _decrypt_paytm_checksum(signature, merchant_key)
    if decrypted_checksum is None or len(decrypted_checksum) < 5:
        return False

    try:
        checksum_text = decrypted_checksum.decode("ascii")
    except UnicodeDecodeError:
        return False

    salt = checksum_text[-4:]
    expected = hashlib.sha256(f"{parameter_string}|{salt}".encode()).hexdigest() + salt
    return hmac.compare_digest(checksum_text, expected)


async def deduplicate_webhook(
    event_id: str,
    session: AsyncSession,
    *,
    payload_bytes: bytes | None = None,
) -> bool:
    """Record a new event ID once, returning False for duplicate or invalid IDs.

    Callers should pass the raw payload when available so ``payload_hash``
    records the actual callback body. The keyword-only argument keeps existing
    two-argument callers compatible; those callers get a stable event-ID hash.
    """
    if not event_id or len(event_id) > 100:
        return False

    hash_input = payload_bytes if payload_bytes is not None else event_id.encode()
    event = WebhookEvent(
        event_id=event_id,
        signature_valid=True,
        payload_hash=hashlib.sha256(hash_input).hexdigest(),
    )
    try:
        async with session.begin_nested():
            session.add(event)
            await session.flush()
    except IntegrityError:
        return False
    return True
