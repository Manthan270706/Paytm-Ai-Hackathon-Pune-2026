# DEMO_RUNBOOK.md: OpsSaathi AI Finale Walkthrough

**Team:** Two Bits  
**Event:** Paytm Build for India AI Hackathon – Pune Finale  
**Venue:** Partex.AI, 7th Floor, Midas Tower, Rajiv Gandhi Infotech Park, Hinjawadi, Pune  
**Date:** 15 November 2026  
**Track:** Track 3: Autonomous AI Teammates  

*“Don't just respond. Investigate. Act. Coordinate. Verify.”*

---

## 1. Frozen Decisions & Baseline Configuration (P0-H3)

| Decision Item | Confirmed Value | Rationale |
| :--- | :--- | :--- |
| **Track** | **Track 3: Autonomous AI Teammates** | End-to-end merchant operations teammate with human-in-the-loop governance. |
| **Primary Golden Scenario** | **₹6,000 Missing Settlement Discrepancy** | High-impact, realistic merchant dispute. |
| **Eligible Successful Captures** | **₹15,000.00** (Decimal) | Matched by transaction & order IDs. |
| **Confirmed Refunds & Fees** | **₹0.00** | Seeded fee rule: 0% rate, ₹0 flat fee. |
| **Expected Settlement Net** | **₹15,000.00** | Strict Python `Decimal` calculation. |
| **Observed in Ledger** | **₹9,000.00** | Marked with explicit provenance `SYNTHETIC_DEMO`. |
| **Discrepancy Amount** | **₹6,000.00** | `expected_net - observed`. |
| **SLA Classification** | **`OVERDUE`** | Batch settlement due date is seeded in the past. |
| **Re-sync Policy Threshold** | **₹5,000.00** | Configurable via `RESYNC_APPROVAL_THRESHOLD_INR`. Since ₹6,000 > ₹5,000, action requires supervisor approval. |
| **Supported Languages** | **English (`en`), Hindi (`hi`), Marathi (`mr`)** | Vernacular accessibility for MSMEs. |
| **Human Gate Reviewer** | **Team Lead (Human)** | Responsible for merges, git tags (`gate-1` to `gate-5`), and credentials. |
| **Lane Split** | **Codex** (Core trust logic) & **Antigravity** (Scaffold, UI, Routes, Agent Graph, Adapters) | Separation of concerns per `AGENTS.md`. |

---

## 2. 4-Minute Finale Demo Script (Judging Flow)

> **Roles:**
> - **Speaker:** Delivers narration, explains architecture, points out trust rules.
> - **Operator:** Drives the UI, triggers voice turns, and switches console views.

| Time | Screen & Role | Action & Script | Expected Outcome |
| :--- | :--- | :--- | :--- |
| **0:00 - 0:30** | **Merchant Dashboard**<br>*(Operator)* | 1. Ensure clean state by clicking **Reset Demo Scenario**.<br>2. Show Ramesh Kirana Store's dashboard.<br>3. *Speaker:* *"OpsSaathi AI is an autonomous teammate that investigates, acts, coordinates, and verifies — not a generic chatbot."* | Dashboard loads with `ScopedRepository`; strict tenant isolation; zero cross-merchant IDOR. |
| **0:30 - 1:15** | **Multilingual Voice Intake**<br>*(Operator)* | 1. Click language selector: switch to Marathi (`mr`) or Hindi (`hi`).<br>2. Click Microphone button (notice AI disclosure and fallback chip).<br>3. Submit query: *"माझा ₹६,००० चा सेटलमेंट का अडकला आहे?"* (or click Marathi Audio Chip). | Voice transcribed via Sarvam (or browser fallback); intent classified as `SETTLEMENT_MISMATCH`. Conversation preserved in memory. |
| **1:15 - 2:00** | **Investigation Panel & SSE Live Trace**<br>*(Operator)* | 1. Observe SSE live trace streaming tool execution nodes.<br>2. Expand Investigation Breakdown.<br>3. *Speaker:* *"Notice the deterministic math: Expected ₹15,000, Observed ₹9,000, Discrepancy ₹6,000. Status is OVERDUE. Notice the provenance badge: SYNTHETIC_DEMO."* | Agent executes `find_transactions`, `get_settlement_entries`, and `calculate_discrepancy`. Strict Decimal calculation without LLM math hallucination. |
| **2:00 - 2:45** | **Policy Gate & Case Creation**<br>*(Operator)* | 1. Agent creates Support Case #1024.<br>2. Agent evaluates policy for `request_settlement_resync`.<br>3. *Speaker:* *"Because ₹6,000 exceeds our ₹5,000 policy gate, automated re-sync is held for human supervisor approval."* | Case enters `AWAITING_APPROVAL`. Checkpoint persisted in LangGraph. Case version (v1) and action hash locked. |
| **2:45 - 3:15** | **Paytm Operations Console**<br>*(Operator)* | 1. Switch top role to **Support Agent / Supervisor**.<br>2. Navigate to **Ops Console**.<br>3. Inspect the Support Cases Queue and select Case #1024. | Supervisor view loads case timeline, evidence summary, and policy gate banner (> ₹5,000). |
| **3:15 - 3:30** | **Negative Test: Premature Close Blocked**<br>*(Operator)* | 1. Click **Verify Resolution** before bank credit is simulated.<br>2. *Speaker:* *"Trust Rule 6: An agent cannot mark a case RESOLVED based on its own say-so. The independent verifier blocks premature resolution because the ledger mismatch remains."* | Verifier inspects ledger; discrepancy remains ₹6,000; case remains in `AWAITING_APPROVAL` / `VERIFYING`. Premature resolution blocked. |
| **3:30 - 4:00** | **Supervisor Approval & Settlement Simulation**<br>*(Operator)* | 1. Click **Review & Approve Action**.<br>2. Review the cryptographic action hash and confirm approval.<br>3. Case transitions to `VERIFYING`.<br>4. Click **Simulate Bank Settlement (₹6,000)**. | Backend validates reviewer role, increments version, and executes re-sync. Audited bank simulation inserts missing credit (+₹6,000). |
| **4:00 - 4:30** | **Independent Verification Pass**<br>*(Operator)* | 1. Click **Verify Resolution**.<br>2. Inspect the Independent Verification Report Card.<br>3. *Speaker:* *"The dedicated read-only role `opssaathi_verifier` performs a fresh read. Before: ₹9,000; After: ₹15,000; Discrepancy: ₹0.00. Verdict: PASS. Only now does the case become RESOLVED."* | Read-only verifier confirms ledger match. Case status moves to `RESOLVED`. Audit timeline records the verification event. |
| **4:30 - 5:00** | **Outcome Metrics & Wrap-Up**<br>*(Operator)* | 1. Point to the Real-Time Metrics Tile.<br>2. Highlight: Time to First Response (< 3s), Time to Resolution, Straight-Through Rate, and Zero Repeat Explanations.<br>3. *Speaker concludes.* | Demonstrates quantifiable operational efficiency for Track 3. |

---

## 3. Honest Disclosures & Simulation Boundaries

Per PRD §15 and Appendix C, all simulated components are explicitly labelled:

| Component | Status / Label | Technical Reality & Hackathon Justification |
| :--- | :--- | :--- |
| **Settlement Ledger** | `SYNTHETIC_DEMO` | The Paytm Settlement API is production-only (not hosted on staging). We seeded a realistic PostgreSQL/SQLite schema with real bank batch structures. |
| **Settlement Ops Adapter** | `MOCK_SETTLEMENT_OPS` | Simulates Paytm internal operations re-sync queue and batch reprocessing. |
| **Voice Interface** | In-App Audio (WebRTC/MediaRecorder) | Powered by Sarvam AI REST API. Real telephony (PSTN/Inbound calls) was kept optional to eliminate telecom failure points on stage. |
| **Replay Mode** | Local Cache Fallback | Uses temperature-0 cached LLM completions to guarantee demo resilience if venue Wi-Fi fails completely. |
| **Paytm Endorsement** | Independent Project | This is a student hackathon submission for the Paytm Build for India AI Hackathon 2026; no official endorsement by One97 Communications is claimed. |

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
   - If Gemini is rate-limited: Automatically falls back to deterministic local mock adapter.
   - If Paytm Staging is down: Explicit badge indicates integration unavailable and uses labelled fixtures.

---

## 5. Clean-Machine Reset Command Reference

```bash
# 1. Reset database to frozen scenario via curl
curl -X POST http://localhost:8000/api/v1/demo/reset

# 2. Run full automated verification suite
python scripts/guard.py
python scripts/run_failure_drills.py
python -m pytest services/api/app/tests

# 3. Run Playwright end-to-end golden run
cd apps/web && npx playwright test
```
