# OpsSaathi AI: Pitch Deck & Judging Presentation

**Team:** Two Bits  
**Event:** Paytm Build for India AI Hackathon – Pune Finale  
**Date:** 15 November 2026  
**Venue:** Partex.AI, Midas Tower, Rajiv Gandhi Infotech Park, Hinjawadi, Pune  
**Track:** Track 3: Autonomous AI Teammates  

*“Don't just respond. Investigate. Act. Coordinate. Verify.”*

---

## Slide 1: Title & The Vision
### **OpsSaathi AI**
#### The Autonomous Merchant Operations Teammate for Paytm

- **The Vision:** Transforming customer support from passive text generation into an active, policy-bounded operational teammate that investigates records, coordinates human approvals, executes audited actions, and independently verifies outcomes.
- **Track 3 Focus:** End-to-end customer service and operations automation with strict human-in-the-loop governance.

---

## Slide 2: The Core Problem: The MSME Settlement Crisis
### Why Traditional Chatbots Fail Indian Merchants

1. **High-Stakes Anxiety:** When ₹6,000 is missing from daily settlement, a kirana store owner cannot buy inventory. It is an operational crisis, not an informational query.
2. **The "Ping-Pong" Support Trap:** Merchants call, repeat their problem in Hindi or Marathi, get assigned a generic ticket, wait 48 hours, and repeat the story to three different agents.
3. **Chatbots Hallucinate Math:** Standard generative LLMs cannot be trusted with floats, rupees, or ledger reconciliation.
4. **No Actionable Authority:** Standard bots cannot trigger re-syncs or coordinate with internal Settlement Ops teams.

---

## Slide 3: The Solution: OpsSaathi AI
### An Active Teammate, Not a FAQ Bot

OpsSaathi bridges the merchant-facing mobile experience and the internal Paytm Operations Console into a single coordinated workflow:

- **Listens & Speaks in Vernacular:** Native voice intake in Hindi, Marathi, and English with seamless in-call language switching.
- **Cross-System Autonomous Investigation:** Pulls payment captures, parses settlement batches, and performs deterministic `Decimal` reconciliation.
- **Enforces Policy Gates:** Automatically flags high-value actions (e.g., > ₹5,000 threshold) and holds them for human supervisor authorization.
- **Coordinates Dual Workflows:** Arms support leads with instant dossiers, cryptographic action hashes, and one-click approvals.
- **Independently Verifies Resolution:** Employs a dedicated read-only database role (`opssaathi_verifier`) to confirm ledger match before closing any case.

---

## Slide 4: The 6 Non-Negotiable Trust Rules
### Enterprise-Grade Financial Safety (PRD §4 & AGENTS.md)

| Rule | Principle | Implementation |
| :--- | :--- | :--- |
| **1. Zero Float Money** | Financial integrity | Python `Decimal(12,2)` precision throughout backend and tools; no float arithmetic. |
| **2. Explicit Provenance** | Zero data hallucination | Every financial payload carries `PAYTM_STAGING` or `SYNTHETIC_DEMO` badge. |
| **3. Policy-Bounded Action** | Human oversight | Settlement re-syncs > ₹5,000 require supervisor approval before dispatch. |
| **4. Cryptographic Concurrency** | Race protection | Optimistic concurrency versioning (`case.version`) and SHA-256 `action_hash`. |
| **5. Cross-Channel Continuity** | Frictionless experience | Identical conversation context and case memory shared across chat and voice. |
| **6. Independent Verification** | Zero premature resolution | Verification must pass via read-only session (`PRAGMA query_only=ON`) before status can reach `RESOLVED`. |

---

## Slide 5: System Architecture
### Dual-Pane Coordination Engine

```
   [ Merchant: Mobile Web UI ]             [ Paytm Operations Console ]
         (Voice / Chat)                         (Supervisor Review)
               │                                         │
               ▼                                         ▼
      React 18 + Vite + Tailwind CSS (TypeScript, Lucide Icons, Mobile-First)
               │                                         │
               └────────────────────┬────────────────────┘
                                    │ HTTPS REST + SSE Live Trace
                                    ▼
                         FastAPI Backend Service
               • ScopedRepository (Tenant Isolation & Anti-IDOR)
               • Request ID Tracing & In-Memory Rate Limiting
               • Sensitive Data Masking (Card PAN, CVV, OTP, PIN)
                                    │
                                    ▼
                     LangGraph Supervisor Workflow
        ┌─────────────────────────────────────────────────────────┐
        │ Intake ──> Investigate ──> Reconcile ──> Policy Gate   │
        │                                                │        │
        │ Resolved <── Verify <── Action Execution <── Human OK  │
        └─────────────────────────────────────────────────────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     ▼                             ▼
           PostgreSQL / SQLite            Integration Adapters
        • Support Cases & Timeline     • Paytm Staging API / Webhooks
        • Resync Requests & Idemp Keys • Gemini 1.5 Flash (Structured LLM)
        • Read-Only Verifier Role      • Sarvam AI (Indian STT/TTS)
        • Append-Only Audit Ledger     • Mock Settlement Ops Provider
```

---

## Slide 6: The 4-Minute Finale Demo Walkthrough
### Golden Path Execution (`scripts/golden_run.md`)

```mermaid
sequenceDiagram
    autonumber
    actor M as Merchant (Ramesh)
    participant UI as Mobile Web App
    participant AG as OpsSaathi Agent
    participant OC as Ops Console
    actor S as Supervisor
    participant DB as Read-Only Verifier

    M->>UI: Voice Turn (Hindi): "₹6,000 सेटलमेंट अडकला आहे"
    UI->>AG: POST /api/v1/voice/turn (transcribe & run)
    AG->>AG: calculate_discrepancy (Expected ₹15k, Observed ₹9k)
    AG->>AG: Policy Check (> ₹5k requires approval)
    AG->>UI: Response + Creates Case #1024 (AWAITING_APPROVAL)
    S->>OC: Inspects Support Queue & Case Dossier
    S->>OC: Clicks "Verify Resolution" (PREMATURE RESOLVE BLOCKED)
    S->>OC: Clicks "Review & Approve Action" (SHA-256 Hash Verified)
    OC->>AG: Case enters VERIFYING; settlement re-sync scheduled
    S->>OC: Clicks "Simulate Bank Settlement (₹6,000)" [Demo step]
    S->>OC: Clicks "Verify Resolution"
    OC->>DB: Fresh read via opssaathi_verifier (Observed = ₹15,000)
    DB-->>OC: Verdict: PASS (Discrepancy: ₹0.00)
    OC->>UI: Case Status: RESOLVED
```

---

## Slide 7: Measurable Operational Outcomes
### Track 3 Business Impact Metrics (PRD §6 & FR-20)

| Metric | Industry Baseline | With OpsSaathi AI | Verification |
| :--- | :--- | :--- | :--- |
| **Time to First Response** | 4 to 8 hours | **< 3 seconds** | Real-time SSE live trace |
| **Discrepancy Triage Time** | 20 to 45 minutes | **Instant (< 2s)** | Deterministic backend reconciliation |
| **Straight-Through Resolution** | ~15% | **65%+** (Autonomous under threshold) | Policy engine routing |
| **Repeat Explanations** | 2 to 3 per ticket | **0** | Chat <-> Voice continuity memory |
| **Financial Hallucination Risk** | High with raw LLMs | **Zero** | `Decimal` math + Verifier read gate |

---

## Slide 8: Resilience & Production Readiness
### 12 Failure Drills Verified (PRD §14)

All 12 failure drills verified via automated test suite `scripts/run_failure_drills.py`:

1. **LLM Quota/Timeout:** Automatic fallback to local cache and deterministic mock.
2. **LLM Invalid JSON:** Deterministic Pydantic repair retry and regex fallback.
3. **Sarvam Voice Down:** Seamless fallback to browser Web Speech synthesis and text.
4. **Paytm Staging Down:** Explicit "integration unavailable" banner; labelled demo fixtures.
5. **Duplicate Webhook:** Idempotent event deduplication by hash/ID (`DUPLICATE_IGNORED`).
6. **Database Offline:** Controlled HTTP 503; zero unacknowledged writes.
7. **Action Timeout:** `Idempotency-Key` header prevents duplicate write replays.
8. **Re-sync Timeout:** `resync_requests` idempotency check prevents duplicate dispatch.
9. **Stale/Unauthorized Approval:** 403 Forbidden on role mismatch; 409 Conflict on version drift.
10. **Worker Concurrency Race:** `SKIP LOCKED` atomic job claiming prevents duplicate runs.
11. **Verification Failure:** Remains `VERIFYING`; blocks premature case resolution.
12. **Mic Permission Denied:** Automatic fallback to chat interface with zero UI freeze.

---

## Slide 9: Honest Disclosures & Simulation Boundaries
### Full Transparency for Hackathon Judges (PRD §15 & Appendix C)

| Component | Status | Production Path |
| :--- | :--- | :--- |
| **Settlement Ledger** | `SYNTHETIC_DEMO` | Paytm Settlement API is production-only; staging ledger is seeded with realistic batches. |
| **Settlement Ops Adapter** | `MOCK_SETTLEMENT_OPS` | Simulates internal Paytm ticketing / re-sync fulfillment pipeline. |
| **Voice Interface** | In-app Web Audio | Uses Sarvam AI REST API; production can connect to Paytm Soundbox or telephony. |
| **Offline Replay Mode** | Local Cache Fallback | Guarantees judging execution even if venue Wi-Fi drops completely. |
| **No Official Endorsement** | Student/Independent Entry | Built strictly for the Paytm Build for India AI Hackathon 2026. |

---

## Slide 10: Conclusion & Next Steps
### The Future of Autonomous Merchant Operations

- **Full Lifecycle Teammate:** OpsSaathi proves that AI teammates can safely handle critical financial operations when bounded by deterministic reconciliation, policy gates, and independent verification.
- **Production Scalability:** Ready for integration with live Paytm Merchant App SDKs, Soundbox devices, and internal Jira/ServiceNow queue workflows.
- **Repo Quality:** 157 pytest tests passing, 0 linter errors, 0 type errors, Playwright E2E passing twice from a clean reset.

**Thank you, Judges & Mentors!**  
*Team Two Bits — Pune Finale 2026*
