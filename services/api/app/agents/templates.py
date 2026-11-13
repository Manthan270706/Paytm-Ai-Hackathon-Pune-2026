import re
from typing import Any

DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

MARATHI_MARKERS = {
    "आहे", "नाही", "नाहीत", "करा", "पैसे", "मिळाले", "माझे", "माझा", "माझी",
    "झाले", "झालेला", "झालेले", "झाली", "अडकले", "अडकला", "आले", "आला",
    "मध्ये", "कधी", "कसा", "कशी", "तुमच्या", "खात्यात", "रुपये", "बॅच",
}

HINDI_MARKERS = {
    "है", "नहीं", "क्यो", "क्यों", "मेरा", "मेरी", "मेरे", "हुआ", "हुए", "हुई",
    "रुपये", "आया", "आए", "आयी", "खाते", "में", "कीजिए", "बताइए", "कब", "बैच",
}


def normalize_devanagari_digits(text: str) -> str:
    """Normalize Devanagari numerals (०-९) to standard ASCII numerals (0-9)."""
    return text.translate(DEVANAGARI_DIGITS)


def detect_language(text: str, fallback: str = "en") -> str:
    """Detect language (en, hi, mr) from message text with Devanagari discrimination."""
    if not text:
        return fallback

    # Check for Devanagari Unicode block (\u0900-\u097F)
    if re.search(r"[\u0900-\u097F]", text):
        words = set(re.findall(r"[\u0900-\u097F]+", text))
        mr_matches = len(words.intersection(MARATHI_MARKERS))
        hi_matches = len(words.intersection(HINDI_MARKERS))

        if mr_matches > hi_matches:
            return "mr"
        elif hi_matches > 0:
            return "hi"
        # If words contain specific Marathi suffixes or verbs
        if any(w.endswith(("चे", "च्या", "ने", "ला", "त")) for w in words):
            return "mr"
        return "hi"

    # Latin script fallback to provided preference or default
    return fallback.lower() if fallback in {"en", "hi", "mr"} else "en"


def format_case_tag(case_id: str | None) -> str:
    """Format safe case tag from case UUID or reference."""
    if not case_id:
        return "1024"
    return str(case_id)[:8]


def render_investigation_reply(
    language: str,
    discrepancy: str,
    case_id: str | None = None,
) -> str:
    """Render localized investigation reply keeping amounts and IDs strictly unchanged."""
    lang = (language or "en").lower()
    case_tag = format_case_tag(case_id)
    # Ensure amount digits are strictly preserved
    amount_str = str(discrepancy)

    if lang == "hi":
        return (
            f"मैंने आपके सेटलमेंट रिकॉर्ड्स की जांच की है। हमें ₹{amount_str} का लेन-देन मिला है "
            f"जो आपके खाते में नहीं पहुंचा था। मैंने सपोर्ट केस #{case_tag} दर्ज कर दिया है और "
            f"सेटलमेंट पुनः समन्वय का अनुरोध किया है, जो वर्तमान में पर्यवेक्षक की मंजूरी के "
            f"लिए प्रतीक्षारत है।"
        )
    elif lang == "mr":
        return (
            f"मी तुमच्या सेटलमेंटच्या नोंदी तपासल्या आहेत. ₹{amount_str} ची रक्कम तुमच्या खात्यात "
            f"जमा झालेली नाही. मी यासाठी सपोर्ट केस #{case_tag} नोंदवली आहे आणि "
            f"सेटलमेंट री-सिंकची विनंती केली आहे, जी मंजुरीच्या प्रतीक्षेत आहे."
        )
    return (
        f"I investigated your settlement records. We found a ₹{amount_str} payment that was "
        "successfully captured but is missing from your settlement batch. "
        f"I have raised Support Case #{case_tag} and requested a settlement re-sync, "
        "which is currently awaiting supervisor approval."
    )


def render_verified_reply(
    language: str,
    discrepancy: str,
    case_id: str | None = None,
) -> str:
    """Render localized verified resolution message keeping numbers unchanged."""
    lang = (language or "en").lower()
    case_tag = format_case_tag(case_id)
    amount_str = str(discrepancy)

    if lang == "hi":
        return (
            f"सपोर्ट केस #{case_tag} का सत्यापन पूरा हो गया है। छूटे हुए ₹{amount_str} के सेटलमेंट "
            f"की पुष्टि हो गई है और केस अब सफलतापूर्वक हल हो गया है।"
        )
    elif lang == "mr":
        return (
            f"सपोर्ट केस #{case_tag} ची पडताळणी पूर्ण झाली आहे. अडकलेल्या ₹{amount_str} च्या सेटलमेंटची "
            f"पुष्टी झाली असून केस आता यशस्वीपणे निकाली काढली आहे."
        )
    return (
        f"Support Case #{case_tag} has been independently verified. Your missing settlement "
        f"of ₹{amount_str} has been confirmed and the case is now resolved."
    )


def render_pending_approval_reply(
    language: str,
    discrepancy: str,
    case_id: str | None = None,
) -> str:
    """Render localized supervisor approval pending notice."""
    lang = (language or "en").lower()
    case_tag = format_case_tag(case_id)
    amount_str = str(discrepancy)

    if lang == "hi":
        return (
            f"सपोर्ट केस #{case_tag} (राशि ₹{amount_str}) सेटलमेंट ऑपरेशन्स को प्रेषित कर दिया "
            f"गया है और पर्यवेक्षक की मंजूरी के लिए प्रतीक्षारत है।"
        )
    elif lang == "mr":
        return (
            f"सपोर्ट केस #{case_tag} (रक्कम ₹{amount_str}) सेटलमेंट ऑपरेशन्सकडे पाठवण्यात आली असून "
            f"पर्यवेक्षक मंजुरीच्या प्रतीक्षेत आहे."
        )
    return (
        f"Support Case #{case_tag} for ₹{amount_str} has been forwarded to Settlement Operations "
        "and is currently awaiting supervisor approval."
    )


def render_no_discrepancy_reply(language: str, batch_ref: str | None = None) -> str:
    """Render localized no discrepancy found message."""
    lang = (language or "en").lower()
    ref = batch_ref or "latest"

    if lang == "hi":
        return f"आपके सेटलमेंट बैच {ref} में कोई विसंगति नहीं मिली। सभी कैप्चर किए गए भुगतान मेल खाते हैं।"
    elif lang == "mr":
        return f"तुमच्या सेटलमेंट बॅच {ref} मध्ये कोणतीही तफावत आढळली नाही. सर्व पेमेंट्स जुळत आहेत."
    return f"All captured payments match settlement batch {ref}. No discrepancy was found."


def extract_numerical_entities(text: str) -> dict[str, Any]:
    """Helper to verify that numerical amounts and IDs are preserved across languages."""
    normalized = normalize_devanagari_digits(text)
    amounts = re.findall(r"₹\s*([0-9]+(?:\.[0-9]{2})?)", normalized)
    cases = re.findall(r"#([A-Za-z0-9_-]+)", normalized)
    return {
        "amounts": amounts,
        "cases": cases,
    }
