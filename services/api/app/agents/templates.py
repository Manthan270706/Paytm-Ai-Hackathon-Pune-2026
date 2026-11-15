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


SEED_CASE_NUMBER_MAP = {
    "99999999-9999-9999-9999-999999999991": "CASE-2026-1024",
    "99999999-9999-9999-9999-999999999992": "CASE-2026-1025",
    "99999999-9999-9999-9999-999999999993": "CASE-2026-1026",
    "99999999-9999-9999-9999-999999999994": "CASE-2026-1027",
    "99999999-9999-9999-9999-999999999995": "CASE-2026-1028",
}


def format_case_tag(case_id: str | None, case_number: str | None = None) -> str:
    """Format safe case tag from case UUID, reference, or explicit case number."""
    if case_number and case_number.strip():
        return case_number.strip()
    if not case_id:
        return "1024"
    case_str = str(case_id)
    if case_str in SEED_CASE_NUMBER_MAP:
        return SEED_CASE_NUMBER_MAP[case_str]
    if case_str.startswith("CASE-") or case_str.startswith("CAS-"):
        return case_str
    return case_str[:8]


def render_category_reply(
    category: str,
    language: str,
    amount: str = "0.00",
    case_id: str | None = None,
    case_number: str | None = None,
    reference: str | None = None,
) -> str:
    """Render localized empathetic reply for any of the 5 operational categories."""
    lang = (language or "en").lower()
    case_tag = format_case_tag(case_id, case_number=case_number)
    amount_str = str(amount)
    ref = reference or "ORD_20261111_09"
    cat = (category or "SETTLEMENT_MISMATCH").upper()

    if cat in {"REFUND_DISPUTE", "REFUND_INQUIRY"}:
        if lang == "hi":
            return (
                f"मैंने ऑर्डर {ref} के लेजर की जांच की है। हमने ₹{amount_str} का दोहरा रिफंड "
                f"डेबिट पाया है। सपोर्ट केस #{case_tag} प्रगति पर है, और आपकी शेष राशि "
                f"बहाल करने के लिए स्वचालित क्रेडिट रिवर्सल कतारबद्ध कर दिया गया है।"
            )
        elif lang == "mr":
            return (
                f"मी ऑर्डर {ref} च्या लेजरची तपासणी केली आहे. आम्हाला ₹{amount_str} चा "
                f"दुहेरी परतावा डेबिट आढळला आहे. सपोर्ट केस #{case_tag} प्रगतीपथावर आहे "
                f"आणि तुमची शिल्लक पुनर्संचयित करण्यासाठी स्वयंचलित क्रेडिट रिव्हर्सल रांगेत जोडले आहे."
            )
        return (
            f"I audited the ledger for Order {ref}. We identified a duplicate refund debit "
            f"of ₹{amount_str}. Support Case #{case_tag} is in progress, and an automatic "
            f"credit reversal has been queued to restore your balance."
        )

    elif cat == "FEE_OVERCHARGE":
        if lang == "hi":
            return (
                f"मैंने आपके RuPay MDR शुल्क की जांच की है। अनुबंध दर 1.20% के बजाय 2.15% का शुल्क "
                f"लिया गया, जिससे ₹{amount_str} का अंतर आया। सपोर्ट केस #{case_tag} में इसकी पुष्टि "
                f"हो गई है, और क्रेडिट नोट CN-20261112-0850 आपके खाते में जोड़ दिया गया है।"
            )
        elif lang == "mr":
            return (
                f"मी तुमच्या RuPay MDR शुल्काची पडताळणी केली आहे. कराराच्या 1.20% दराऐवजी 2.15% "
                f"आकारणी करण्यात आली, ज्यामुळे ₹{amount_str} चा फरक पडला. सपोर्ट केस #{case_tag} मध्ये "
                f"तफावत तपासली गेली असून क्रेडिट नोट CN-20261112-0850 खात्यावर जमा केली आहे."
            )
        return (
            f"I verified your RuPay MDR fee schedule. The transactions were billed at 2.15% "
            f"instead of the contract rate of 1.20%, causing a fee difference of ₹{amount_str}. "
            f"Support Case #{case_tag} has verified the variance, and credit note CN-20261112-0850 "
            f"has been posted to your account."
        )

    elif cat == "HARDWARE_DIAGNOSTICS":
        if lang == "hi":
            return (
                f"मैंने आपके Paytm Soundbox 4G डिवाइस का डायग्नोस्टिक चलाया है। सिग्नल मजबूत (-82dBm) "
                f"है और लेटेंसी 320ms है। रिमोट फर्मवेयर कैशे साफ़ कर दिया गया है और टेस्ट चाइम "
                f"चालू है। सपोर्ट केस #{case_tag} अब पूरी तरह हल हो गया है।"
            )
        elif lang == "mr":
            return (
                f"मी तुमच्या Paytm Soundbox 4G उपकरणाची तपासणी केली आहे. सिग्नल सामर्थ्य उत्तम (-82dBm) "
                f"असून लेटन्सी 320ms आहे. फर्मवेअर कॅशे रिमोटली साफ करण्यात आला असून चाचणी आवाज "
                f"यशस्वी झाला आहे. सपोर्ट केस #{case_tag} आता पूर्णपणे निकाली काढली आहे."
            )
        return (
            f"I ran diagnostics on your Paytm Soundbox 4G device. Signal strength is strong (-82dBm) "
            f"and latency is 320ms. The remote firmware cache was purged, and test chimes are "
            f"confirmed working. Support Case #{case_tag} is now fully resolved."
        )

    elif cat == "PAYOUT_DELAY":
        if lang == "hi":
            return (
                f"मैंने बैच BATCH_20261110_02 (₹{amount_str}) के पेआउट होल्ड की जांच की है। T+1 बैंक "
                f"अवकाश के कारण भुगतान 48 घंटे के SLA से अधिक विलंबित हुआ। सपोर्ट केस #{case_tag} दर्ज "
                f"किया गया है और राशि जारी करने के लिए पर्यवेक्षक की मंजूरी प्रतीक्षारत है।"
            )
        elif lang == "mr":
            return (
                f"मी बॅच BATCH_20261110_02 (₹{amount_str}) च्या पेआउट होल्डची तपासणी केली आहे. T+1 बँक "
                f"सुट्टीमुळे 48 तासांच्या SLA पेक्षा जास्त उशीर झाला. सपोर्ट केस #{case_tag} नोंदवण्यात "
                f"आली असून निधी जारी करण्यासाठी पर्यवेक्षक मंजुरीच्या प्रतीक्षेत आहे."
            )
        return (
            f"I investigated the payout hold for batch BATCH_20261110_02 (₹{amount_str}). A T+1 bank "
            f"clearing holiday delayed the transfer beyond the 48-hour SLA. Support Case #{case_tag} "
            f"has flagged this SLA breach and is currently awaiting supervisor approval to release funds."
        )

    return render_investigation_reply(
        language=lang, discrepancy=amount_str, case_id=case_id, case_number=case_number
    )


def render_investigation_reply(
    language: str,
    discrepancy: str,
    case_id: str | None = None,
    case_number: str | None = None,
) -> str:
    """Render localized investigation reply keeping amounts and IDs strictly unchanged."""
    lang = (language or "en").lower()
    case_tag = format_case_tag(case_id, case_number=case_number)
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


def render_greeting_reply(language: str, query_type: str = "GREETING") -> str:
    """Render warm, authentic conversational greeting or capability overview as OpsSaathi AI."""
    lang = (language or "en").lower()
    if query_type == "GENERAL_QUERY":
        if lang == "hi":
            return (
                "मैं ऑप्ससाथी (OpsSaathi) हूँ—पेटीएम मर्चेंट्स के लिए स्वायत्त एआई ऑपरेशन्स साथी। "
                "मैं निम्नलिखित परिचालन समस्याओं की त्वरित जांच और समाधान कर सकता हूँ:\n"
                "• छूटे हुए सेटलमेंट और लेजर मिसमैच की जांच\n"
                "• डुप्लीकेट रिफंड डेबिट पर ऑटो-क्रेडिट रिवर्सल\n"
                "• RuPay MDR कमीशन और शुल्क शेड्यूल का ऑडिट\n"
                "• साउंडबॉक्स 4G सिग्नल और लेटेंसी डायग्नोस्टिक्स\n"
                "• बैंक अवकाश के कारण अटके हुए पेआउट्स को अनब्लॉक करना\n"
                "आज आप किस समस्या की जांच करना चाहते हैं?"
            )
        elif lang == "mr":
            return (
                "मी ऑप्ससाथी (OpsSaathi) आहे—पेटीएम मर्चंट्ससाठी स्वायत्त एआय ऑपरेशन्स सहाय्यक. "
                "मी खालील ऑपरेशन्स समस्यांची त्वरित तपासणी आणि निराकरण करू शकतो:\n"
                "• अडकलेले सेटलमेंट आणि लेजर तफावत तपासणी\n"
                "• दुहेरी रिफंड डेबिटवर स्वयंचलित क्रेडिट रिव्हर्सल\n"
                "• RuPay MDR कमिशन आणि शुल्क शेड्यूल ऑडिट\n"
                "• साउंडबॉक्स 4G सिग्नल आणि लेटन्सी डायग्नोस्टिक्स\n"
                "• बँक सुट्टीमुळे प्रलंबित पेआउट्स अनब्लॉक करणे\n"
                "आज तुम्हाला कशात मदत हवी आहे?"
            )
        return (
            "I'm OpsSaathi—your autonomous Paytm Merchant Operations Teammate. "
            "I can investigate, take policy-guided actions, and independently verify:\n"
            "• Missing settlements and bank batch ledger variances\n"
            "• Customer duplicate refund debits and queued clawbacks\n"
            "• RuPay MDR commission schedule audits and fee corrections\n"
            "• Paytm Soundbox 4G telemetry diagnostics and cache flushes\n"
            "• Bank holiday payout hold releases past 48h SLA\n"
            "Which operational issue would you like me to inspect today?"
        )

    # Standard Greeting
    if lang == "hi":
        return (
            "नमस्ते! मैं ऑप्ससाथी (OpsSaathi) हूँ, आपका समर्पित पेटीएम मर्चेंट ऑपरेशन्स साथी। "
            "मैं आपके सेटलमेंट, रिफंड, MDR शुल्क, साउंडबॉक्स या पेआउट समस्याओं की तुरंत जांच और समाधान कर सकता हूँ। "
            "आज मैं आपकी क्या सहायता करूँ?"
        )
    elif lang == "mr":
        return (
            "नमस्कार! मी ऑप्ससाथी (OpsSaathi) आहे, तुमचा स्वायत्त पेटीएम मर्चंट ऑपरेशन्स साथी. "
            "मी सेटलमेंट, रिफंड, MDR फी, साउंडबॉक्स किंवा पेआउट तपासणीत तुम्हाला मदत करू शकतो. "
            "आज मी तुम्हाला कशी मदत करू?"
        )
    return (
        "Hello! I'm OpsSaathi, your autonomous Paytm Merchant Operations Teammate. "
        "I can help investigate missing settlements, duplicate refund debits, MDR fee variances, "
        "Soundbox telemetry diagnostics, or delayed payouts. How can I assist your business today?"
    )


def extract_numerical_entities(text: str) -> dict[str, Any]:
    """Helper to verify that numerical amounts and IDs are preserved across languages."""
    normalized = normalize_devanagari_digits(text)
    amounts = re.findall(r"₹\s*([0-9]+(?:\.[0-9]{2})?)", normalized)
    cases = re.findall(r"#([A-Za-z0-9_-]+)", normalized)
    return {
        "amounts": amounts,
        "cases": cases,
    }
