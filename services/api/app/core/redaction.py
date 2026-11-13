"""Redact credentials and personal identifiers before logging or LLM calls."""

import re
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, Field


class RedactionResult(BaseModel):
    clean_text: str
    redacted_types: list[str] = Field(default_factory=list)


_OTP = re.compile(
    r"\b(?:otp|one[- ]time(?:\s+password)?|verification code)\b\s*(?:is|[:=])?\s*(\d{4,8})",
    re.IGNORECASE,
)
_PIN = re.compile(r"\b(?:upi\s*)?pin\b\s*(?:is|[:=])?\s*(\d{4,6})", re.IGNORECASE)
_CVV = re.compile(r"\b(?:cvv|cvc|security code)\b\s*(?:is|[:=])?\s*(\d{3,4})", re.IGNORECASE)
_CARD_LABELLED = re.compile(
    r"\b(?:card(?:\s+number|\s+no\.?|\s+details)?|credit card|debit card)\b"
    r"\s*(?:is|[:=])?\s*((?:\d[ -]?){12,19}\d)",
    re.IGNORECASE,
)
_ACCOUNT = re.compile(
    r"\b(?:bank\s+account|account\s+number|account\s+no\.?|a/c\s+no\.?)\b"
    r"\s*(?:is|[:=])?\s*(\d(?:[ -]?\d){7,17})\b",
    re.IGNORECASE,
)
_AADHAAR = re.compile(
    r"\b(?:aadhaar|aadhar)\b\s*(?:number|no\.?|is|[:=])?\s*(\d{4}[ -]?\d{4}[ -]?\d{4})",
    re.IGNORECASE,
)
_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.IGNORECASE)
_PHONE_LABELLED = re.compile(
    r"\b(?:phone|mobile|telephone)\b(?:\s+number)?\s*(?:is|[:=])?\s*(\+?\d[\d ()-]{7,}\d)",
    re.IGNORECASE,
)
_CARD_CANDIDATE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_INDIAN_PHONE = re.compile(r"(?<!\d)(?:\+?91[ -]?)?[6-9]\d{9}(?!\d)")
_SENSITIVE_KEY = re.compile(
    r"(?:otp|one.?time.?password|pin|cvv|cvc|password|secret|card.?number|account.?number|"
    r"bank.?account|aadhaar|aadhar|pan)",
    re.IGNORECASE,
)


def _digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def _is_card_number(value: str) -> bool:
    digits = _digits(value)
    if not 13 <= len(digits) <= 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for index, character in enumerate(digits):
        number = int(character)
        if index % 2 == parity:
            number *= 2
            if number > 9:
                number -= 9
        checksum += number
    return checksum % 10 == 0


def mask_phone(phone: str) -> str:
    """Mask a phone number while retaining its last four digits."""
    digits = _digits(phone)
    if len(digits) <= 4:
        return "[REDACTED_PHONE]"
    return f"{'*' * (len(digits) - 4)}{digits[-4:]}"


def mask_account(account: str) -> str:
    """Mask a bank account number while retaining its last four digits."""
    digits = _digits(account)
    if len(digits) <= 4:
        return "[REDACTED_ACCOUNT]"
    return f"{'*' * (len(digits) - 4)}{digits[-4:]}"


def redact(text: str) -> RedactionResult:
    """Mask OTP, PIN, CVV, card data and other common Indian identifiers."""
    clean_text = text
    detected: set[str] = set()

    def replace(pattern: re.Pattern[str], replacement: str, kind: str) -> None:
        nonlocal clean_text
        clean_text, count = pattern.subn(replacement, clean_text)
        if count:
            detected.add(kind)

    replace(_OTP, "[REDACTED_OTP]", "OTP")
    replace(_PIN, "[REDACTED_PIN]", "PIN")
    replace(_CVV, "[REDACTED_CVV]", "CVV")
    replace(_CARD_LABELLED, "[REDACTED_CARD]", "CARD")
    replace(_ACCOUNT, "[REDACTED_ACCOUNT]", "ACCOUNT")
    replace(_AADHAAR, "[REDACTED_AADHAAR]", "AADHAAR")
    replace(_PAN, "[REDACTED_PAN]", "PAN")

    def replace_phone(match: re.Match[str]) -> str:
        detected.add("PHONE")
        return mask_phone(match.group(1))

    clean_text = _PHONE_LABELLED.sub(replace_phone, clean_text)

    def replace_card(match: re.Match[str]) -> str:
        if _is_card_number(match.group(0)):
            detected.add("CARD")
            return "[REDACTED_CARD]"
        return match.group(0)

    clean_text = _CARD_CANDIDATE.sub(replace_card, clean_text)

    def replace_indian_phone(match: re.Match[str]) -> str:
        detected.add("PHONE")
        return mask_phone(match.group(0))

    clean_text = _INDIAN_PHONE.sub(replace_indian_phone, clean_text)
    return RedactionResult(clean_text=clean_text, redacted_types=sorted(detected))


def redact_pii(text: str) -> str:
    """Compatibility helper returning only the sanitized text."""
    return redact(text).clean_text


def redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize text and replace values stored under sensitive keys."""
    def clean(value: Any, key: str = "") -> Any:
        if _SENSITIVE_KEY.search(key):
            kind = re.sub(r"[^A-Za-z]+", "_", key).strip("_").upper() or "SENSITIVE"
            return f"[REDACTED_{kind}]"
        if isinstance(value, str):
            return redact_pii(value)
        if isinstance(value, Mapping):
            return {
                str(child_key): clean(child_value, str(child_key))
                for child_key, child_value in value.items()
            }
        if isinstance(value, list):
            return [clean(item, key) for item in value]
        if isinstance(value, tuple):
            return tuple(clean(item, key) for item in value)
        return value

    return {str(key): clean(value, str(key)) for key, value in data.items()}
