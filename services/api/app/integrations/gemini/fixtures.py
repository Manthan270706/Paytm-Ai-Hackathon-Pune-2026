import hashlib

# Pre-recorded golden scenario fixtures for English, Hindi, and Marathi (PRD §12.3)
GOLDEN_EXTRACTION_FIXTURE = {
    "amount": "6000.00",
    "reference": "BATCH_20261112_01",
    "category": "SETTLEMENT_MISMATCH",
    "missing_fields": [],
}

GOLDEN_INTENT_FIXTURE = {
    "intent": "SETTLEMENT_MISMATCH",
    "confidence": 1.0,
    "reasoning": "Merchant reports missing captured payment from settlement batch.",
}

# Key phrases mapped to golden fixtures
GOLDEN_PHRASES = [
    # English
    "missing from settlement",
    "payment from yesterday is missing",
    "6000",
    "6,000",
    "batch_20261112_01",
    "settlement batch status",
    "missing settlement",
    # Hindi
    "भुगतान सेटलमेंट में नहीं आया",
    "सेटलमेंट में नहीं मिला",
    "सेटलमेंट क्यों रुका",
    "मेरा ₹6,000",
    "मेरा ₹६,०००",
    "६,०००",
    "६०००",
    "भुगतान",
    # Marathi
    "पेमेंट सेटलमेंटमध्ये जमा झालेले नाही",
    "माझे ₹६,००० चे पेमेंट",
    "माझा ₹६,००० चा सेटलमेंट",
    "माझे ₹6,000 चे पेमेंट",
    "सेटलमेंटमध्ये का नाही",
    "अडकले आहे",
    "अडकला आहे",
    "जमा झाले नाही",
]


def matches_golden_scenario(prompt: str) -> bool:
    prompt_lower = prompt.lower()
    return any(p.lower() in prompt_lower for p in GOLDEN_PHRASES)


def compute_request_hash(
    prompt: str, schema_name: str, system_prompt: str | None = None
) -> str:
    """Stable SHA-256 hash of an LLM request prompt and target schema."""
    raw = f"{schema_name}::{system_prompt or ''}::{prompt.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
