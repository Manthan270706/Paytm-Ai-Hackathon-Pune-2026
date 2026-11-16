# DEMO_RUNBOOK.md: OpsSaathi AI Finale Walkthrough

**Team:** Two Bits  
**Event:** Paytm Build for India AI Hackathon – Pune Finale  
**Venue:** Partex.AI, 7th Floor, Midas Tower, Rajiv Gandhi Infotech Park, Hinjawadi, Pune  
**Date:** 16 November 2026  
**Track:** Track 3: Autonomous AI Teammates  

*“Don't just respond. Investigate. Act. Coordinate. Verify.”*

---

## 1. Frozen Decisions & Baseline Configuration

| Decision Item | Confirmed Value | Rationale |
| :--- | :--- | :--- |
| **Track** | **Track 3: Autonomous AI Teammates** | End-to-end merchant operations teammate with human-in-the-loop governance. |
| **Positioning** | **Paytm Intelligence (Pi) Agent Module** | Plug-and-play module deployable internally across Paytm's 10M+ merchants and sellable to banks. |
| **Primary Golden Scenario** | **₹6,000 Missing Settlement Discrepancy** | High-impact, realistic merchant dispute. |
| **Eligible Successful Captures** | **₹15,000.00** (Decimal) | Matched by transaction & order IDs across 3 captures. |
| **Confirmed Refunds & Fees** | **₹0.00** | Seeded fee rule: 0% rate, ₹0 flat fee. |
| **Expected Settlement Net** | **₹15,000.00** | Strict Python `Decimal` calculation. |
| **Observed in Ledger** | **₹9,000.00** | Marked with explicit provenance `SYNTHETIC_DEMO`. |
| **Discrepancy Amount** | **₹6,000.00** | `expected_net - observed`. |
| **SLA Classification** | **`OVERDUE`** | Batch settlement due date is dynamically overdue. |
| **Re-sync Policy Threshold** | **₹5,000.00** | Configurable via `RESYNC_APPROVAL_THRESHOLD_INR`. Since ₹6,000 > ₹5,000, action requires supervisor approval. |
| **Supported Languages** | **English (`en`), Hindi (`hi`), Marathi (`mr`)** | Vernacular accessibility for MSMEs. |
| **Execution Environment** | **Local Laptop Execution** | Runs locally with pre-seeded standalone SQLite DB (`opssaathi_demo.db`) for 100% demo stability. |

---

## 2. 4-Minute Finale Demo Script (Judging Flow)

> **Roles:**
> - **Speaker:** Delivers narration, explains architecture, points out trust rules and unit economics.
> - **Operator:** Drives the UI, triggers voice turns, and switches console views.

| Time | Screen & Role | Action & Script | Expected Outcome |
| :--- | :--- | :--- | :--- |
| **0:00 - 0:35** | **Merchant Dashboard**<br>*(Operator)* | 1. Ensure clean state by clicking **"Reset"** in header.<br>2. Highlight official Paytm branding (`paytm UPI` vector logo) and **Pi Agent** badge.<br>3. *Speaker:* *"Meet OpsSaathi AI — an autonomous merchant operations teammate built for Paytm Intelligence (Pi). It replaces reactive call center support with proactive, audited automation."* | Dashboard loads with `ScopedRepository`; strict tenant isolation; zero cross-merchant IDOR. |
| **0:35 - 1:10** | **Proactive Settlement Watchdog & Soundbox Voice**<br>*(Operator)* | 1. Switch language to **हिन्दी (Hindi)**.<br>2. Point out the Watchdog Banner: delayed payout alert with live UTR and expected credit window.<br>3. Click **"Listen on Soundbox"**.<br>4. *Speaker:* *"Before the merchant even checks their bank, the agent detects the nodal delay and broadcasts the exact UTR on their Soundbox. Zero merchant anxiety, zero tickets."* | Banner renders dynamic Hindi alert; browser audio broadcasts Soundbox announcement in Hindi. |
| **1:10 - 1:50** | **Autonomous Chargeback Defense Builder**<br>*(Operator)* | 1. Click **"Dispute Defense"** on the ticket card.<br>2. Modal opens with 4-part legal packet.<br>3. Point out: Customer claim, Soundbox 4G counter-chime receipt, cell tower LAC matching shop GPS, and NPCI RRN.<br>4. Click **"Submit Dispute Docket"**.<br>5. *Speaker:* *"Chargebacks take BPOs 45 minutes to compile. OpsSaathi correlates IoT hardware chime logs and cell tower data into an airtight legal docket in under 4 seconds."* | Docket compiled and submitted with timestamped confirmation. |
| **1:50 - 2:35** | **Ledger Reconciliation & Policy Gate**<br>*(Operator)* | 1. In the chat box, type or click: *"Why is ₹6,000.00 missing from today's settlement?"*<br>2. Observe live SSE execution trace.<br>3. Expand Investigation Breakdown: Expected ₹15K, Observed ₹9K, Diff ₹6K.<br>4. *Speaker:* *"Notice the deterministic Decimal math — zero LLM hallucination. Because ₹6,000 exceeds our ₹5,000 policy gate, automated re-sync is held for human supervisor approval."* | Agent executes `find_transactions` and `calculate_discrepancy`. Case #1024 enters `AWAITING_APPROVAL` with version lock (v1) and action hash. |
| **2:35 - 3:05** | **Paytm Operations Console**<br>*(Operator)* | 1. Click top-right role switcher to **Console**.<br>2. Inspect the 5 multi-queue dispute cases.<br>3. Select Case #1024. | Supervisor view loads case timeline, evidence summary, and policy gate banner (> ₹5,000 threshold). |
| **3:05 - 3:25** | **Negative Test: Premature Close Blocked**<br>*(Operator)* | 1. Click **"Verify Resolution"** before bank settlement credit is simulated.<br>2. *Speaker:* *"Trust Rule 4: An agent cannot mark a case RESOLVED on its own say-so. The independent verifier blocks premature resolution because the ledger mismatch remains."* | Read-only verifier inspects ledger; discrepancy remains ₹6,000; case remains in `AWAITING_APPROVAL`. Premature resolution blocked! |
| **3:25 - 3:45** | **Supervisor Approval & Settlement Simulation**<br>*(Operator)* | 1. Click **"Review & Authorize Action"**.<br>2. Review the cryptographic action hash and confirm approval.<br>3. Click **"Simulate Bank Settlement (₹6,000)"** to deposit credit on ledger. | Action approved; case transitions to `VERIFYING`. Bank simulation adds +₹6,000 missing credit. |
| **3:45 - 4:05** | **Independent Verification Pass**<br>*(Operator)* | 1. Click **"Run Independent Verification"**.<br>2. Inspect Verification Report Card.<br>3. *Speaker:* *"The dedicated read-only role `opssaathi_verifier` performs a fresh read. Discrepancy is ₹0.00. Verdict: PASS. Only now does the case transition to RESOLVED."* | Ledger discrepancy confirmed ₹0.00; case status moves to `RESOLVED`; audit timeline recorded. |
| **4:05 - 4:20** | **Unit Economics & Conclusion**<br>*(Operator)* | 1. Highlight the **Paytm Pi ROI card**:  <br>• **72.4%** Ticket Deflection Rate  <br>• **4.2 min** Resolution TAT (down from 48h)  <br>• **₹0.38 vs ₹18.50** Cost per Resolution.<br>2. *Speaker concludes.* | Quantifiable business ROI demonstrated for Track 3 judging. |

---

## 3. Honest Disclosures & Simulation Boundaries

Per PRD §15 and Appendix C, all simulated components are explicitly labelled:

| Component | Status / Label | Technical Reality & Hackathon Justification |
| :--- | :--- | :--- |
| **Settlement Ledger** | `SYNTHETIC_DEMO` | The Paytm Settlement API is production-only (not hosted on staging). We seeded a realistic SQLite schema with real bank batch structures. |
| **Settlement Ops Adapter** | `MOCK_SETTLEMENT_OPS` | Simulates Paytm internal operations re-sync queue and batch reprocessing. |
| **Soundbox Voice** | In-Browser Web Speech API | Provides zero-latency speech playback on stage without telecom network dropouts. |
| **Replay Mode** | Local Cache Fallback | Uses temperature-0 cached LLM completions to guarantee demo resilience if venue Wi-Fi fails completely. |
| **Execution Mode** | Local Laptop Setup | Intentionally run locally on the developer machine for guaranteed fast response times and zero cloud cold-starts. |

---

## 4. Emergency Fallback Protocols (Venue Reliability)

1. **Venue Wi-Fi Disconnect:**
   - Set `DEMO_DETERMINISTIC="true"` in `.env` (or via frontend Replay toggle).
   - System serves the full golden run from local `llm_cache` with zero network dependencies.
2. **Acoustic Noise in Hackathon Hall (300+ people):**
   - Click the **Pre-recorded Audio Chips** right beside the mic button (Hindi / Marathi / English).
   - Clean audio bytes are sent to the STT adapter without background interference.
3. **External Provider Downtime:**
   - If Sarvam is unavailable: Automatically falls back to browser Web Speech API $\rightarrow$ then text chat.
   - If Groq is rate-limited: Automatically falls back to local Ollama (`qwen2.5:3b`) $\rightarrow$ then deterministic mock.

---

## 5. Clean-Machine Reset & Quick Commands

```bash
# 1. Reset database to frozen scenario via curl
curl -X POST http://localhost:8000/api/v1/demo/reset

# 2. Run repository security and integrity guard
python scripts/guard.py

# 3. Run backend test suite
python -m pytest services/api/app/tests
```
