"""Paytm Pi Agent Module: Proactive Settlement Watchdog & Autonomous Chargeback Defense.

High-Impact Operational Automation:
1. Proactive Settlement Watchdog: Monitors settlement batches & bank SLAs, emits regional
   alerts with exact UTR and clearing windows before merchants raise tickets.
2. Simulated Soundbox Broadcast: Speaks status updates over the merchant's soundbox channel.
3. Autonomous Chargeback Defense Builder: Compiles counter-chime audio logs, NPCI RRNs,
   and merchant proofs into an arbitration-ready dispute docket.
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthContext, get_auth_context
from app.core.response import success_response
from app.db.models import SettlementBatch, SupportCase, Transaction
from app.db.seed import BATCH_ID, CASE_1_ID, CASE_2_ID, MERCHANT_ID
from app.db.session import get_db_session

router = APIRouter()


class WatchdogAlert(BaseModel):
    alert_id: str
    batch_ref: str
    amount: Decimal
    currency: str = "INR"
    utr_number: str
    delay_reason: str
    clearing_bank: str
    expected_credit_window: str
    case_number: str
    case_id: str
    severity: str  # INFO, WARNING, CRITICAL
    messages: dict[str, str]
    soundbox_announcement: str
    detected_at: str
    status: str  # PROACTIVELY_RESOLVING, ESCALATED_TO_NODAL


class ChargebackDefensePacket(BaseModel):
    case_number: str
    order_id: str
    disputed_amount: Decimal
    merchant_name: str
    merchant_mid: str
    kyc_status: str
    dispute_category: str
    customer_claim: str
    # Soundbox hardware proof
    soundbox_proof: dict[str, Any]
    # Banking & NPCI audit proof
    npci_trace: dict[str, Any]
    # Arbitration defense document
    arbitration_docket_markdown: str
    generated_at: str
    submission_deadline: str
    status: str  # READY_FOR_ARBITRATION, SUBMITTED


@router.post("/watchdog/scan", summary="Run proactive settlement watchdog scan")
async def run_watchdog_scan(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Proactively evaluates merchant batches for overdue settlements and SLA spillover."""
    merchant_id = auth.active_merchant_id or MERCHANT_ID
    now = datetime.now(UTC)

    # 1. Inspect settlement batches for delayed payouts
    query = (
        select(SettlementBatch)
        .where(SettlementBatch.merchant_id == merchant_id)
        .order_by(SettlementBatch.date.desc())
    )
    batches = list((await session.execute(query)).scalars().all())

    # Build active watchdog alert for the overdue discrepancy
    discrepancy_amount = Decimal("6000.00")
    batch_ref = batches[0].batch_ref if batches else "BATCH_20261112_01"

    alert = WatchdogAlert(
        alert_id=f"WDG-{uuid.uuid4().hex[:8].upper()}",
        batch_ref=batch_ref,
        amount=discrepancy_amount,
        currency="INR",
        utr_number="NPCI/HDFC/20261112/984210",
        delay_reason="Clearing delay at nodal sponsor bank (NPCI settlement cycle cutoff spillover)",
        clearing_bank="HDFC Bank Nodal Account",
        expected_credit_window="Today by 11:30 AM IST",
        case_number="CASE-2026-1024",
        case_id=str(CASE_1_ID),
        severity="WARNING",
        messages={
            "en": (
                "Paytm Pi Watchdog Alert: Your ₹6,000 settlement (Batch BATCH_20261112_01) is queued "
                "at HDFC Nodal Clearing (UTR: NPCI/HDFC/20261112/984210). Auto-investigation CASE-2026-1024 "
                "is tracking this. Expected credit: 11:30 AM today."
            ),
            "hi": (
                "पेटीएम पाई वॉचडॉग अलर्ट: आपका ₹६,००० का सेटलमेंट (बैच BATCH_20261112_01) नोडल बैंक क्लीयरिंग "
                "में लंबित है (UTR: NPCI/HDFC/20261112/984210)। केस CASE-2026-1024 स्वचालित रूप से ट्रैक कर रहा है। "
                "संभावित क्रेडिट: आज पूर्वाह्न ११:३० बजे।"
            ),
            "mr": (
                "पेटीएम पाय वॉचडॉग अलर्ट: तुमचे ₹६,००० चे सेटलमेंट (बॅच BATCH_20261112_01) नोडल बँक क्लिअरिंगमध्ये "
                "प्रलंबित आहे (UTR: NPCI/HDFC/20261112/984210). केस CASE-2026-1024 ट्रॅक करत आहे. "
                "अपेक्षित क्रेडिट: आज सकाळी ११:३०."
            ),
        },
        soundbox_announcement="पेटीएम पर छह हज़ार रुपये का सेटलमेंट नोडल बैंक में प्रोसेस हो रहा है। ग्यारह तीस तक आपके खाते में आ जाएगा।",
        detected_at=now.isoformat(),
        status="PROACTIVELY_RESOLVING",
    )

    return success_response(
        data={
            "alert": alert.model_dump(),
            "scan_timestamp": now.isoformat(),
            "batches_analyzed": len(batches),
            "proactive_cases_linked": 1,
            "deflection_achieved": True,
        },
        source_type="SYNTHETIC_DEMO",
    )


@router.get("/watchdog/alerts", summary="Fetch active proactive alerts")
async def get_watchdog_alerts(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict:
    """Returns active proactive watchdog alerts for merchant dashboard."""
    # Deterministic active alert for seed scenario
    alert = WatchdogAlert(
        alert_id="WDG-SND-9842",
        batch_ref="BATCH_20261112_01",
        amount=Decimal("6000.00"),
        currency="INR",
        utr_number="NPCI/HDFC/20261112/984210",
        delay_reason="Clearing delay at nodal sponsor bank (NPCI settlement cycle cutoff spillover)",
        clearing_bank="HDFC Bank Nodal Account",
        expected_credit_window="Today by 11:30 AM IST",
        case_number="CASE-2026-1024",
        case_id=str(CASE_1_ID),
        severity="WARNING",
        messages={
            "en": "Paytm Pi Watchdog: ₹6,000 settlement queued at nodal bank (UTR: NPCI/HDFC/20261112/984210). Case CASE-2026-1024 tracking. Expected credit: 11:30 AM.",
            "hi": "पेटीएम पाई वॉचडॉग: ₹६,००० का सेटलमेंट नोडल बैंक में लंबित (UTR: NPCI/HDFC/20261112/984210)। केस CASE-2026-1024 सक्रिय। संभावित क्रेडिट: ११:३० AM।",
            "mr": "पेटीएम पाय वॉचडॉग: ₹६,००० सेटलमेंट नोडल बँकेत प्रलंबित आहे. केस CASE-2026-1024 सक्रिय. अपेक्षित क्रेडिट: ११:३० AM.",
        },
        soundbox_announcement="पेटीएम पर छह हज़ार रुपये का सेटलमेंट नोडल बैंक में प्रोसेस हो रहा है। ग्यारह तीस तक आपके खाते में आ जाएगा।",
        detected_at=(datetime.now(UTC) - timedelta(minutes=15)).isoformat(),
        status="PROACTIVELY_RESOLVING",
    )

    return success_response(
        data={"alerts": [alert.model_dump()]},
        source_type="SYNTHETIC_DEMO",
    )


@router.get("/cases/{case_id}/chargeback-packet", summary="Build autonomous chargeback defense docket")
async def get_chargeback_defense_packet(
    case_id: uuid.UUID,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Autonomous Chargeback Defense Builder: Compiles multi-source proof for NPCI dispute."""
    # Find case or fallback to Case 2 template
    case_query = select(SupportCase).where(SupportCase.id == case_id)
    case_obj = (await session.execute(case_query)).scalar_one_or_none()

    case_num = case_obj.case_number if case_obj else "CASE-2026-1025"
    summary_text = case_obj.summary if case_obj else "Customer claims money was debited twice and merchant refused refund"

    import re
    amt_match = re.search(r"[₹Rs\.]*\s*([0-9,]+(?:\.[0-9]{2})?)", summary_text)
    if amt_match:
        try:
            amount = Decimal(amt_match.group(1).replace(",", ""))
        except Exception:
            amount = Decimal("1200.00")
    else:
        amount = Decimal("1200.00")

    order_match = re.search(r"#(ORD_[0-9a-zA-Z_]+|BATCH_[0-9a-zA-Z_]+)", summary_text)
    order_id = order_match.group(1) if order_match else ("BATCH_20261112_01" if "1024" in case_num else "ORD_20261111_09")
    claim_text = summary_text

    now = datetime.now(UTC)
    deadline = (now + timedelta(days=3)).strftime("%d %b %Y, 17:00 IST")

    docket_md = f"""# NPCI / Bank Dispute Arbitration Defense Docket
**Case Reference:** `{case_num}` | **Order / Batch ID:** `{order_id}`  
**Disputed Amount:** ₹{amount:,.2f} INR | **Generated by:** Paytm Pi Autonomous Risk Agent  
**Submission Deadline:** {deadline}

---

## 1. Merchant & Account Verification
- **Merchant Legal Name:** Two Bits General Store & Cafe
- **Paytm Merchant MID:** `PAYTM_MID_9823419082`
- **KYC Status:** `VERIFIED_TIER_2` (Aadhaar & GSTIN Checked)
- **Settlement Account:** HDFC Bank A/c ending in `**4920` (IFSC: HDFC0001284)

## 2. In-Store Hardware Proof (Paytm Soundbox 4G)
- **Device Serial / IMEI:** `863920049281729`
- **Firmware Version:** `v4.2.1-paytm-4g-secure`
- **Broadcast Audio Confirmation:** `SUCCESS` (Chime played in Hindi)
- **Timestamp:** `11 Nov 2026, 14:32:04 IST` (Within 3.1s of QR scan)
- **Cell Tower Location (LAC/CellID):** `404-45-7281-9102` (Verified at Merchant GPS Lat: 18.5204, Long: 73.8567)

## 3. Financial & NPCI Transaction Ledger
- **Paytm Transaction ID:** `TXN_7845631982`
- **NPCI RRN:** `631892019482`
- **Customer Bank Auth Code:** `HDFC_AUTH_89214`
- **Payer VPA:** `customer@okhdfcbank`
- **Dispute Diagnosis:** Primary transaction was successfully captured and goods were delivered at store; dispute record: {claim_text}. Merchant was credited only once.

## 4. Legal Arbitration Conclusion
> **MERCHANT POSITION:** The merchant fulfilled goods at the counter upon valid Soundbox voice confirmation. The claim of 'Goods Not Received' is demonstrably false. Any secondary debit or discrepancy is an issuing bank-side hold and should be released by the issuing bank without penalizing the merchant.
"""

    packet = ChargebackDefensePacket(
        case_number=case_num,
        order_id=order_id,
        disputed_amount=amount,
        merchant_name="Two Bits General Store",
        merchant_mid="PAYTM_MID_9823419082",
        kyc_status="VERIFIED_TIER_2",
        dispute_category="PAYMENT_AND_DELIVERY_DISPUTE",
        customer_claim=claim_text,
        soundbox_proof={
            "device_model": "Paytm Soundbox 4G Pro",
            "imei": "863920049281729",
            "audio_broadcast_time": "2026-11-11T14:32:04+05:30",
            "broadcast_status": "CHIME_SUCCESS_VERIFIED",
            "voice_language": "hi_IN",
            "tower_cell_id": "404-45-7281-9102",
        },
        npci_trace={
            "npci_rrn": "631892019482",
            "payer_vpa": "customer@okhdfcbank",
            "auth_code": "HDFC_AUTH_89214",
            "gateway_status": "DUPLICATE_AUTH_HOLD_REVERSIBLE",
        },
        arbitration_docket_markdown=docket_md,
        generated_at=now.isoformat(),
        submission_deadline=deadline,
        status="READY_FOR_ARBITRATION",
    )

    return success_response(
        data=packet.model_dump(),
        source_type="SYNTHETIC_DEMO",
    )
