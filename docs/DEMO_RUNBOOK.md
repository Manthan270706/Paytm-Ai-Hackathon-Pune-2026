# DEMO_RUNBOOK.md: OpsSaathi AI

**Team:** Two Bits  
**Event:** Paytm Build for India AI Hackathon – Pune Finale  
**Venue:** Partex.AI, 7th Floor, Midas Tower, Rajiv Gandhi Infotech Park, Hinjawadi, Pune  
**Date:** 15 November 2026  
**Track:** Track 3: Autonomous AI Teammates  

---

## 1. Frozen Decisions & Baseline Configuration (P0-H3)

| Decision Item | Confirmed Value | Rationale |
| :--- | :--- | :--- |
| **Track** | **Track 3: Autonomous AI Teammates** | Full customer-service / merchant-ops workflow handled end-to-end with human-in-the-loop oversight. |
| **Primary Golden Scenario** | **₹6,000 Missing Settlement Discrepancy** | Realistic, high-frequency merchant crisis. |
| **Eligible Successful Captures** | **₹15,000** (Decimal) | Matched by transaction / order ID. |
| **Confirmed Refunds & Fees** | **₹0.00** | Seeded fee rule: 0% rate, ₹0 flat fee. |
| **Expected Settlement Net** | **₹15,000.00** | Strict Decimal math. |
| **Observed in Ledger** | **₹9,000.00** | Marked `SYNTHETIC_DEMO`. |
| **Discrepancy Amount** | **₹6,000.00** | `expected_net - observed`. |
| **SLA Classification** | **`OVERDUE`** | Batch settlement due date is seeded in the past. |
| **Re-sync Policy Threshold** | **₹5,000.00** | Configurable via `RESYNC_APPROVAL_THRESHOLD_INR`. Since ₹6,000 > ₹5,000, action requires human approval. |
| **Supported Languages** | **English (`en`), Hindi (`hi`), Marathi (`mr`)** | Native vernacular support for Maharashtra MSMEs. |
| **Human Gate Reviewer** | **Team Lead (Human)** | Responsible for merges, git tags (`gate-1` to `gate-5`), and credentials. |
| **Lane Split** | **Codex** (Core trust logic) & **Antigravity** (Scaffold, UI, Routes, Agent Graph, Adapters) | Separation of concerns per `AGENTS.md`. |

---

## 2. 4-Minute Finale Demo Script (Judging Flow)

| Time | Screen / Actor | Action & Script | Expected Outcome |
| :--- | :--- | :--- | :--- |
| **0:00 - 0:30** | **Merchant Dashboard** (Mobile View) | Log in as demo merchant (Ramesh Kirana Store). Show payments summary and explain: *"OpsSaathi is an autonomous teammate that investigates and acts, not a FAQ chatbot."* | Merchant profile loaded with `ScopedRepository`; zero IDOR. |
| **0:30 - 1:15** | **Chat / Voice Session** | Click microphone (or select Marathi/Hindi voice sample): *"माझा ₹६,००० चा सेटलमेंट का अडकला आहे?"* (Why is my ₹6,000 settlement stuck?) | Voice transcribed via Sarvam (or browser fallback); intent classified as `SETTLEMENT_MISMATCH`. |
| **1:15 - 2:00** | **Investigation Panel & SSE Live Trace** | Agent executes `find_transactions`, `get_settlement_entries`, and `calculate_discrepancy`. Live trace streams tool executions. | Backend Decimal math displays: Expected ₹15,000, Observed ₹9,000, Discrepancy ₹6,000 (`OVERDUE`). Provenance badges show `SYNTHETIC_DEMO`. |
| **2:00 - 2:45** | **Policy Gate & Case Creation** | OpsSaathi creates Support Case #1024. It initiates `request_settlement_resync`. Because ₹6,000 > ₹5,000 threshold, policy returns `REQUIRE_HUMAN_APPROVAL`. | Checkpoint persisted in LangGraph. Case status enters `AWAITING_APPROVAL`. Case version and action hash locked. |
| **2:45 - 3:30** | **Paytm Ops Console** (Dual Screen) | Switch to Support Lead view. Reviewer sees executive dossier with discrepancy trace and clicks **Approve Re-sync**. | Backend validates reviewer role, checks `case.version` and `action_hash`. Mock Settlement Ops acknowledges re-sync. |
| **3:30 - 4:15** | **Simulate Bank Settlement & Verification** | Support lead clicks audited button: **Simulate bank settlement** (+₹6,000). Click **Run Independent Verification**. | `opssaathi_verifier` (read-only DB role) reads fresh state: Observed is now ₹15,000. Verification returns `PASS`. Case moves to `RESOLVED`. |
| **4:15 - 5:00** | **Metrics & Audit Timeline** | Open Metrics tile and Audit Log. Show Mean Time to Resolution, straight-through processing %, and append-only event stream. | Demonstrates measurable operational outcome for Track 3. |

---

## 3. Emergency Fallback Protocols (Venue Reliability)

1. **Venue Wi-Fi Disconnect:**
   * Set `DEMO_DETERMINISTIC="true"` in `.env`.
   * The system serves the complete golden run from local `llm_cache` with temperature 0. A small "replay mode" badge will appear in the UI.
2. **Acoustic Noise in Hackathon Hall:**
   * In a crowded room with 300+ developers, live browser microphone can fail.
   * Use the **Pre-recorded Audio Chips** right beside the mic button (English, Hindi, Marathi) to feed clean audio into the STT pipeline.
3. **External Provider Outages:**
   * Sarvam down $\rightarrow$ falls back to Browser Web Speech API $\rightarrow$ falls back to typed chat.
   * Gemini rate limit $\rightarrow$ falls back to deterministic local mock adapter.
