# OPSSAATHI AI: PRODUCT REQUIREMENTS DOCUMENT

**Autonomous Merchant Operations Teammate**

Prepared by Team Two Bits
Paytm Build for India AI Hackathon, Pune Finale
Finale: 15 November 2026. **Version 1.1, 13 November 2026** (supersedes v1.0 of 12 November 2026)

*Don't just respond. Investigate. Act. Verify.*

> **Purpose.** This is the engineering source of truth for the finale build. The pitch deck must describe only implemented capabilities or clearly label simulated and future integrations.

---

## Document Control

| Field | Value |
| --- | --- |
| Product | OpsSaathi AI |
| Team | Two Bits |
| Event | Paytm Build for India AI Hackathon, Pune, in-person finale |
| Track | Track 3: Autonomous AI Teammates (customer-service workflow, end to end) |
| Date / venue | 15 November 2026, Partex.AI, Midas Tower, Hinjawadi, Pune |
| Version | 1.1, 13 November 2026 |
| MVP focus | Merchant payment and settlement discrepancy investigation with verified case resolution |

### Changelog: v1.0 to v1.1

| # | Change | Where |
| --- | --- | --- |
| C1 | Added `support_cases.version`, `approvals.case_version`, `approvals.action_hash` so stale-approval checks (409) actually work | §8, §11 |
| C2 | `merchant_id` removed from every tool input; bound server-side from the session | §7.3 |
| C3 | All data access goes through `ScopedRepository(merchant_id)`; optional Postgres row-level security | §7.4 |
| C4 | Prompt-injection and sensitive-input defences: redaction, allowlisted tools, schema-validated LLM output | §13 |
| C5 | Verification made visibly independent: read-only DB role, "Simulate bank settlement" action, before/after diff | §7.5, §10 |
| C6 | SLA-aware reconciliation with reason codes (`WITHIN_SLA_PENDING`, `OVERDUE`, `MISSING`, `INSUFFICIENT_EVIDENCE`) | §10 |
| C7 | Live agent trace streamed over SSE | §9, §6 |
| C8 | Deterministic demo mode (temperature 0, response cache, record/replay) | §12, §14 |
| C9 | New cross-system action tool `request_settlement_resync` against a labelled mock Settlement Operations adapter | §7.3, §11 |
| C10 | Outcome metrics (`GET /api/v1/metrics`) and dashboard tile | §9, §6 |
| C11 | Multilingual replies (English, Hindi, Marathi); Sarvam primary voice, browser voice fallback | §4, §12 |
| C12 | Follow-up worker uses `SELECT ... FOR UPDATE SKIP LOCKED`; async DB layer standardised | §12 |
| C13 | Agent rules file (`AGENTS.md`) and one git worktree per lane | §18, App. B |

---

## Executive Summary

OpsSaathi AI is an AI-powered operations teammate for payment-platform merchant support. A merchant reports an issue through chat or an in-browser voice session, in English, Hindi or Marathi. The system retrieves authorized records, investigates through backend tools, calculates discrepancies deterministically, classifies them against the settlement SLA, evaluates policy, creates and tracks a support case, takes a permitted cross-system action (a settlement re-sync request) behind a policy gate, coordinates with a human when required, follows up, and verifies the final state with an independent fresh read before saying the issue is resolved.

The finale MVP focuses on one complete workflow: a successful payment is missing from the expected settlement. It demonstrates a demo merchant, transaction lookup, a clearly labelled synthetic settlement ledger when staging settlement data is unavailable, evidence-backed investigation with a live agent trace, policy-controlled case creation and re-sync request, human approval, case timeline, voice interaction, outcome metrics, and independent verification.

> **Product truth.** A support ticket is not a financial resolution. Report "case created" or "under investigation" until a fresh backend read proves the final state.

---

## 1. Product Definition

### 1.1 Vision

Give every merchant a dependable AI operations teammate that understands an issue, investigates it, coordinates the right action and proves what happened.

### 1.2 Problem

- Merchants may see a payment marked successful while the expected settlement is not visible or is lower than expected.
- Support journeys can require repeated explanations, manual lookups, handoffs and uncertain status.
- A generic chatbot can explain policies but may not retrieve records, execute controlled workflows or verify outcomes.
- Chat and voice histories can be disconnected, forcing merchants to repeat context.
- Merchants in India often prefer Hindi or Marathi, and many support tools only work well in English.

### 1.3 Target Users

| Persona | Need | Product response |
| --- | --- | --- |
| Merchant | Understand missing/delayed/failed payments and receive updates in their language. | Chat/voice intake, evidence, case tracking. |
| Support agent | Receive actionable cases with context. | Queue, investigation summary, timeline, approvals. |
| Supervisor | Control risk and service quality. | RBAC, audit trail, workload, escalation, outcome metrics. |
| Judge | See a real working workflow. | Seeded scenario, live agent trace, visible tools, states and verification. |

---

## 2. Goals and Non-Goals

### 2.1 MVP Goals

- Complete one end-to-end settlement discrepancy workflow using seeded demo data.
- Support text chat and voice with shared conversation and case context, in English, Hindi and Marathi.
- Use a stateful agent workflow with typed tools, policy checks and persistence.
- Show evidence and source provenance behind every financial conclusion.
- Take one visible cross-system action (settlement re-sync request) under policy control.
- Create, assign, track and close cases only after independent verification.
- Show measurable outcomes (time to response, time to verified resolution, handled vs escalated).
- Work locally if internet, LLM or telephony provider is unavailable.

### 2.2 Non-Goals for 15 November

- No real-money movement, automatic bank transfer or unapproved refund execution.
- No access to arbitrary Paytm merchants or internal Paytm systems.
- No claim of production settlement integration without authorized production credentials.
- No unrestricted autonomous PSTN calling. In-app voice is the MVP; telephony is optional and future.
- No full KYC, dispute, chargeback or device-diagnostics platform in the first build.
- Do not imply official Paytm endorsement; this is a hackathon prototype for the merchant-support problem.

### 2.3 Demo Success Criteria

| Metric | Acceptance target | Proof |
| --- | --- | --- |
| Workflow completion | One discrepancy completes end-to-end. | Golden demo run. |
| Evidence grounding | Every financial claim has a backend source or DEMO label. | Evidence panel and tool trace. |
| Safe actions | Sensitive actions require approval or are denied. | Policy tests. |
| Resolution integrity | No RESOLVED state before verification PASS. | Premature-close test. |
| Independent verification | Verifier uses a read-only DB role and shows before/after evidence. | Verify panel diff, DB role test. |
| Channel continuity | Chat and voice use the same case context. | Switch channel mid-case. |
| Language | Same case handled in English and Hindi or Marathi. | Language switch demo. |
| Reliability | Provider failure does not break case access. | Disable API key and rerun. |
| Measurable outcome | Metrics tile shows response and resolution times. | Metrics panel. |

---

## 3. Scope and Priorities

| Priority | Feature | Finale commitment |
| --- | --- | --- |
| P0 | Demo login, merchant context, role-aware session | Working with seeded accounts. |
| P0 | Chat complaint intake and intent classification | Working end-to-end. |
| P0 | Transaction lookup and deterministic, SLA-aware discrepancy calculation | Seeded data; Paytm staging adapter if credentials work. |
| P0 | LangGraph investigation workflow and typed tools (server-bound merchant scope) | Visible node/tool events. |
| P0 | Policy engine and human approval gate with version/hash checks | Working; sensitive actions blocked pending approval. |
| P0 | Case create, assign, timeline and status | Persisted and visible. |
| P0 | Independent verification before closure | Fresh read via read-only DB role. |
| P0 | Voice session | Sarvam STT/TTS primary; browser speech fallback; text fallback. |
| P1 | Settlement re-sync request tool (mock Settlement Ops adapter) | Policy-gated; clearly labelled mock. |
| P1 | Live agent trace over SSE | Working in investigation panel. |
| P1 | Multilingual replies (en, hi, mr) | Language detection plus localized templates and LLM replies. |
| P1 | Outcome metrics endpoint and tile | Computed from case events. |
| P1 | Deterministic demo mode (cache plus replay) | Golden scenario works with LLM offline. |
| P1 | Paytm staging payment status and webhooks | If test credentials and HTTPS callback are available. |
| P1 | Follow-up scheduler | Worker plus manual "run follow-up now" trigger. |
| P2 | PSTN calling, production settlement API, live multi-merchant onboarding | Future only; do not promise as delivered. |

---

## 4. Functional Requirements

| ID | Acceptance behaviour |
| --- | --- |
| FR-01 Identity & tenant scope | Load authenticated demo merchant. Every query is scoped server-side through `ScopedRepository`; changing a URL must not expose another merchant. |
| FR-02 Issue intake | Accept chat/voice complaint; extract category, amount, date, transaction/order reference. Ask for missing facts; never invent them. |
| FR-03 Intent routing | Classify PAYMENT_STATUS, SETTLEMENT_MISMATCH, REFUND_STATUS, QR_DEVICE_ISSUE or OTHER. Unsupported cases go to human queue. |
| FR-04 Transaction lookup | Read transaction records only through tenant-scoped backend tools. LLM cannot fabricate records or supply a merchant ID. |
| FR-05 Reconciliation | Use Decimal-based domain code to calculate expected vs observed settlement from explicit records/rules and return an SLA reason code. |
| FR-06 Evidence summary | Show records checked, status, calculation, reason code, source labels, limitations and next action. |
| FR-07 Policy evaluation | Each action returns ALLOW, DENY or REQUIRE_HUMAN_APPROVAL with a reason code. |
| FR-08 Case creation | Create case with ID, merchant, category, severity, evidence refs, queue, status, version and timestamps; idempotent. |
| FR-09 Human approval | Authorized support role approves/rejects; backend validates role, case version and action hash, then persists the decision. |
| FR-10 Case timeline | Show chronological status, actions, approvals and merchant-visible messages; hide internal notes. |
| FR-11 Voice session | Capture speech with browser permission, transcribe via Sarvam (fallback: browser speech), use same graph, display and optionally speak response. |
| FR-12 Shared context | Voice resumes same authenticated conversation and active case as chat. |
| FR-13 Follow-up | Store follow-up time/flag; worker re-checks status and notifies only on meaningful change; no duplicate runs. |
| FR-14 Verification | Freshly re-fetch source record using the read-only verifier role; only explicit passing criteria permit RESOLVED. |
| FR-15 Audit | Log actor, timestamp, correlation ID, action and outcome for tools, approvals, webhooks and state transitions. |
| FR-16 Failure handling | Provider/tool failure is reported honestly; safe reads may retry boundedly; non-idempotent actions are not blindly repeated. |
| FR-17 Language | Detect merchant language (en, hi, mr), reply in that language, keep money amounts and IDs unchanged across languages. |
| FR-18 Live trace | Stream agent node and tool events to the UI over SSE; the persisted `tool_executions` rows remain the record. |
| FR-19 Settlement re-sync | `request_settlement_resync` sends a re-sync request to the mock Settlement Ops adapter; policy-gated by amount threshold; never moves money. |
| FR-20 Outcome metrics | Compute time to first response, time to verified resolution, handled vs escalated, and repeat explanations avoided from `case_events`. |
| FR-21 Input safety | Redact OTP/PIN/card patterns before logging or LLM calls; treat all merchant text as data, never as instructions. |

---

## 5. User Journeys

### 5.1 Primary Journey: Missing Settlement

1. Merchant opens the demo workspace and selects "My payment is missing from settlement" (in any supported language).
2. Merchant provides or confirms transaction/order reference and expected amount.
3. Agent identifies the merchant from the session and retrieves matching payment records through backend tools. The live trace shows each step.
4. Reconciliation service compares eligible payments, confirmed refunds, documented fees and settlement entries, and returns a reason code. Example: payment successful; ₹6,000 `OVERDUE` in the synthetic demo ledger. UI labels synthetic data.
5. Agent explains the evidence, in the merchant's language, and says whether this is within the normal settlement window or overdue.
6. Policy engine allows support-case creation, and holds the settlement re-sync request for approval because the discrepancy exceeds the threshold. Fund movement and refund execution stay blocked.
7. Case is created, assigned to Settlement Operations and shown in the timeline.
8. Support user approves the re-sync request; the mock Settlement Ops adapter acknowledges it.
9. Merchant receives a chat/voice update.
10. A support user clicks "Simulate bank settlement" in the ops console, which adds the missing ledger entry with a before/after record.
11. On follow-up, the verifier performs a fresh read with the read-only role. Only a matching final settlement state closes the case. The UI shows the before/after evidence diff and timestamp.
12. Metrics tile updates with the case's response and resolution times.

### 5.2 Voice Journey

Merchant selects the microphone, grants permission, speaks, reviews transcription and submits. The same agent graph processes the request. Response appears as text and may be spoken. If Sarvam fails, browser speech is used; if speech recognition fails or permission is denied, typed input remains available. MVP voice is an in-app session, not unrestricted telephone calling. The AI identity is disclosed at session start.

### 5.3 Human Approval Journey

A gated action creates an approval request that stores the case version and an action hash, and persists a graph checkpoint. An authorized support agent reviews evidence and approves/rejects. On resume the backend re-checks reviewer role, current case version, action hash and policy. If the case or action changed, the API returns 409 CONFLICT and the approval must be re-requested. Rejection records a reason and returns a safe explanation.

### 5.4 Failure Journey

On provider timeout, record a failed tool event. Retry only safe idempotent reads with bounded backoff. Never claim success after a timeout. Merchant can still view the case and request human support. In deterministic demo mode, the cached golden-scenario responses keep the flow working without the LLM.

---

## 6. UX Screens

| Screen | Required elements |
| --- | --- |
| Merchant dashboard | Merchant name/ID, payment/settlement summary, open cases, Ask OpsSaathi entry, language selector. |
| Chat + voice workspace | Message history, mic/recording state, transcript preview, text fallback, evidence cards, case card. |
| Investigation panel | Live agent trace (SSE), records checked, calculation, reason code, data source labels: PAYTM_STAGING or SYNTHETIC_DEMO. |
| Case detail | Case ID, category, priority, status, owner queue, timeline, next update. |
| Operations console | Case queue, filters, evidence, approval requests, assign/escalate, "Simulate bank settlement" action, audit events. |
| Approval modal | Action, policy reason, evidence, case version, approve/reject, rejection reason. |
| Verification panel | Before/after evidence diff, verification timestamp, PASS/FAIL, verifier role label. |
| Metrics tile | Time to first response, time to verified resolution, handled vs escalated, repeat explanations avoided. |
| Integration health | Paytm/LLM/voice/database status and active provider; never expose secrets. |

---

## 7. Technical Architecture

**Architecture principle:** the LLM handles language and workflow orchestration; deterministic backend services own identity, arithmetic, authorization, state transitions and financial truth.

```
MERCHANT / SUPPORT USER
        |
React + Vite + TypeScript (Chat / Voice / Case UI)
        |  HTTPS REST + SSE (live trace)
FastAPI API Layer (async)
  Auth + RBAC + Tenant Scope + Validation + Rate Limits
        |
LangGraph Supervisor (persisted workflow)
  Intake -> Investigate -> Policy -> Action -> Verify
     |         |          |        |         |
 Gemini/    Read tools   Policy   Case     Verify svc
 Sarvam    (ScopedRepo)  engine   svc     (read-only role)
     |         |          |        |         |
     +---------+----------+--------+---------+
                        |
              PostgreSQL source of truth
   merchants | transactions | settlements | cases | approvals
   tool runs | conversations | audit | metrics events
                        |
              Integration adapters
   Paytm staging | Synthetic ledger | Mock Settlement Ops
   Sarvam STT/TTS | Browser voice | Gemini
```

### 7.1 Component Responsibilities

| Component | Owns | Must not |
| --- | --- | --- |
| Frontend | UX, audio capture, rendering, API calls, SSE display. | Store merchant keys, authorize actions, mark case resolved locally. |
| FastAPI | Auth, validation, tenant scope, API contracts. | Trust LLM-provided merchant IDs or amounts. |
| LangGraph | Stateful workflow, routing, checkpoints, tool selection. | Run arbitrary SQL or unrestricted financial actions. |
| Domain services | Decimal reconciliation, SLA classification, policy, case lifecycle, verification. | Delegate arithmetic or permissions to LLM. |
| Policy engine | ALLOW/DENY/REQUIRE_APPROVAL and reason codes. | Trust frontend approval claims. |
| PostgreSQL | Durable source of truth and audit. | Store raw provider secrets. |
| Adapters | Paytm/Gemini/Sarvam/voice/Settlement Ops integration. | Couple core business logic to one vendor. |

### 7.2 Agent Workflow

```
START
 -> authenticate_session
 -> sanitize_input (redact OTP/PIN/card patterns, detect language)
 -> collect_issue (clarify missing reference / date / amount)
 -> classify_issue
 -> load_merchant_context
 -> investigate (read-only tools)
 -> reconcile_deterministically (returns reason code)
 -> prepare_evidence_summary
 -> evaluate_policy
      DENY             -> explain + human escalation
      REQUIRE_APPROVAL -> persist checkpoint (+ case version, action hash) + wait
      ALLOW            -> execute permitted case action / settlement re-sync
 -> verify_action (fresh read)
 -> update_case_timeline
 -> communicate (chat / voice, in merchant's language)
 -> follow_up if pending
 -> verify_resolution
      PASS -> RESOLVED
      FAIL -> remain IN_PROGRESS / PENDING_EXTERNAL
 -> END
```

Every node emits a trace event (node name, tool name, status, latency) that is written to `tool_executions` and streamed over SSE.

### 7.3 Tool Contracts

**Rule: no tool accepts `merchant_id` as an input.** The merchant scope is bound server-side from the authenticated session when the tool is constructed. The LLM cannot pass, change or guess it.

| Tool | Input / output and safety |
| --- | --- |
| get_merchant_context | No inputs; returns allowed merchant scope from the session; read-only. |
| find_transactions | Date, amount, order/transaction ref; returns matched records and source IDs; tenant-scoped. |
| get_settlement_entries | Date range; returns entries with source_type; tenant-scoped. |
| calculate_discrepancy | Record IDs; returns Decimal totals, discrepancy, SLA reason code and calculation trace. |
| create_support_case | Category/evidence/summary; returns case ID; idempotency key; no money movement. |
| assign_case | Case/queue; role checked; append event. |
| request_approval | Case/action/evidence; creates approval storing case version and action hash, plus graph checkpoint. |
| request_settlement_resync | Case/batch ref; calls mock Settlement Ops adapter; policy-gated by threshold; idempotent; never moves money. |
| apply_case_update | Case/allowed transition/note/expected version; validates state machine and version. |
| verify_resolution | Case/rule; fresh read through read-only role returns PASS/FAIL, before/after evidence and timestamp. |
| send_merchant_update | Case/template/language; consent and visibility checked. |

All LLM tool-call arguments and all structured LLM outputs are validated against Pydantic schemas. On a validation failure the graph makes one repair retry, then falls back to a deterministic path or human escalation. Tools outside the allowlist cannot be called.

### 7.4 Tenant Isolation

- All data access goes through a `ScopedRepository(merchant_id)` factory, created per request from the authenticated session. Repositories do not expose an unscoped query method.
- Optional defence in depth: Postgres row-level security keyed to a per-request session variable. Enable it if time allows; the repository layer is the P0 control.
- Test: merchant A requesting any merchant B resource by ID receives 404 or 403 on every route.

### 7.5 Independent Verification

- The verification service uses a separate **read-only database role** (`opssaathi_verifier`) that cannot write to any table.
- `verify_resolution` fetches the source records fresh (no cached or in-memory results) and compares them to the recorded before-state.
- The ops console action **"Simulate bank settlement"** is labelled as a demo simulation of the bank-side event. It writes the missing ledger entry as `SYNTHETIC_DEMO` and is audited. The verifier did not write that entry, and the verification panel shows the before/after diff and the evidence timestamp.

---

## 8. Data Model

Use UUID primary keys, UTC timestamps, NUMERIC(12,2) for INR, foreign keys, indexes on merchant_id/status/created_at, and explicit source provenance on every imported or synthetic record. Use async SQLAlchemy throughout (no mixed sync/async sessions).

| Table | Key fields | Purpose |
| --- | --- | --- |
| users | id, email, role, is_active, preferred_language | Merchant/support identities. |
| merchants | id, external_mid nullable, display_name, masked_phone, status | Merchant profile. |
| merchant_users | user_id, merchant_id, role | Tenant membership. |
| transactions | id, merchant_id, provider, provider_txn_id, order_id, amount, currency, status, txn_time, source_type | Payment records. |
| fee_rules | id, merchant_id, rule_ref, rate_percent, flat_amount, active, source_type | Documented fee rules (seeded at 0 for the demo). |
| settlement_batches | id, merchant_id, batch_ref, date, expected_settlement_date, gross, fees, refunds, net, status, source_type | Settlement summary. |
| settlement_entries | id, batch_id, transaction_id, amount, entry_type, status, source_type | Transaction settlement mapping. |
| support_cases | id, merchant_id, case_number, category, priority, status, queue, summary, idempotency_key, followup_at, **version** | Case source of truth; `version` increments on every change. |
| case_events | id, case_id, actor, event_type, from/to status, visibility, payload, created_at | Append-only timeline; source for metrics. |
| conversations | id, merchant_id, channel, language, active_case_id, created_at | Shared chat/voice context. |
| messages | id, conversation_id, role, content/transcript_ref, language, created_at | Conversation messages (redacted). |
| agent_runs | id, conversation_id, case_id, provider, model, status, trace_id | Agent execution metadata. |
| tool_executions | id, agent_run_id, tool, input_hash, output_ref, status, latency, idempotency_key | Tool trace; feeds SSE. |
| approvals | id, case_id, action, **case_version**, **action_hash**, requested_by, decided_by, decision, reason, status | Human approvals; stale if version or hash differs. |
| resync_requests | id, case_id, batch_ref, status, idempotency_key, adapter_ref, created_at | Settlement re-sync requests to the mock adapter. |
| followup_jobs | id, case_id, run_at, status, locked_at, attempts | Follow-up queue (claimed with `FOR UPDATE SKIP LOCKED`). |
| llm_cache | key_hash, request_hash, response_json, created_at | Deterministic demo mode cache and replay fixtures. |
| calls | id, conversation_id, consent, started_at, ended_at, outcome | Voice session metadata. |
| webhook_events | id, provider, event_id, signature_valid, payload_hash, status | Webhook deduplication. |
| audit_events | id, actor, action, resource, trace_id, created_at | Security/business audit. |

### 8.1 Case State Machine

```
NEW -> TRIAGED -> INVESTIGATING -> ACTION_REQUIRED
                         |                 |
                         |                 +-> AWAITING_APPROVAL -> APPROVED / REJECTED
                         |                                              |
                         +----------------------------------> IN_PROGRESS -> PENDING_EXTERNAL
                                                                  |               |
                                                                  +---------------+
                                                                          |
                                                                      VERIFYING
                                                                     /         \
                                                                  PASS         FAIL
                                                                   |             |
                                                               RESOLVED     IN_PROGRESS
ESCALATED / CANCELLED: reachable by authorized, audited transitions.
```

Enforce transitions in the backend; never accept arbitrary frontend status. Every transition checks the expected `version` and increments it; a mismatch returns CONFLICT.

---

## 9. API Specification

| Method / route | Purpose / controls |
| --- | --- |
| POST /api/v1/auth/demo-login | Start demo session; demo only. |
| GET /api/v1/me | Current user and allowed merchant scope. |
| GET /api/v1/merchants/{id} | Tenant-scoped merchant summary. |
| GET /api/v1/transactions | Tenant-scoped search; validated filters. |
| GET /api/v1/transactions/{id} | Tenant-scoped transaction detail. |
| GET /api/v1/settlements | Return entries with source_type. |
| POST /api/v1/agent/messages | Start/resume graph; conversation-scoped. |
| GET /api/v1/agent/runs/{id}/events | SSE stream of live node/tool trace; tenant-scoped. |
| POST /api/v1/voice/sessions | Create voice session; authenticated; records AI-identity disclosure. |
| POST /api/v1/voice/transcriptions | Submit transcript to same conversation. |
| GET /api/v1/cases | Role-filtered case list. |
| POST /api/v1/cases | Create case; Idempotency-Key required. |
| GET /api/v1/cases/{id} | Case and timeline. |
| POST /api/v1/cases/{id}/approve | Support role only; checks case version and action hash. |
| POST /api/v1/cases/{id}/reject | Support role; reason required. |
| POST /api/v1/cases/{id}/assign | Support role; queue allowlist. |
| POST /api/v1/cases/{id}/verify | Fresh verification read via read-only role. |
| POST /api/v1/cases/{id}/followup/run | Support role; manual follow-up trigger for the demo. |
| POST /api/v1/demo/simulate-settlement | Support role, demo mode only; writes the missing ledger entry (audited, SYNTHETIC_DEMO). |
| POST /api/v1/demo/reset | Demo mode only; reseeds the scenario. |
| GET /api/v1/metrics | Role-filtered outcome metrics from `case_events`. |
| POST /api/v1/webhooks/paytm | Public HTTPS; checksum validation and dedupe. |
| GET /api/v1/health | Safe liveness/readiness response; no secrets. |

### 9.1 API Response Convention

```json
{
  "ok": true,
  "data": {},
  "meta": {"request_id": "uuid", "source_type": "SYNTHETIC_DEMO", "timestamp": "UTC ISO-8601"},
  "error": null
}
```

Stable error codes: `VALIDATION_ERROR`, `NOT_FOUND`, `FORBIDDEN`, `APPROVAL_REQUIRED`, `PROVIDER_UNAVAILABLE`, `RATE_LIMITED`, `CONFLICT`.

---

## 10. Reconciliation Rules

All monetary values use Decimal. The LLM may explain the result but may not calculate or alter totals.

```
expected_net =
    sum(successful_capture_amounts)
  - sum(confirmed_refunds)
  - sum(documented_fees)
  - sum(documented_tax)

observed    = sum(settlement_entries_for_batch)
discrepancy = expected_net - observed
```

Rules:

- Match by provider transaction ID / order ID, never amount alone.
- Exclude failed/cancelled payments.
- Include only confirmed refunds with source records.
- Do not infer fees if no fee record/rule exists.
- Incomplete data => `INSUFFICIENT_EVIDENCE`, never a guess.
- Show inputs, source IDs, currency and provenance.

### 10.1 SLA-aware reason codes

Every reconciliation returns one reason code, computed against `settlement_batches.expected_settlement_date` and "now" (injectable clock for tests):

| Reason code | Meaning | Agent behaviour |
| --- | --- | --- |
| `NO_DISCREPANCY` | Observed equals expected. | Report match. |
| `WITHIN_SLA_PENDING` | Discrepancy exists but the expected settlement date has not passed. | Tell the merchant it is normal and give the date; no escalation. |
| `OVERDUE` | Expected settlement date has passed and discrepancy > 0. | Create case, request re-sync (policy-gated). |
| `MISSING` | A successful payment has no settlement entry at all and the batch is closed. | Create case, high priority. |
| `INSUFFICIENT_EVIDENCE` | Required records or fee data are absent. | Ask for or route to a human; make no claim. |

### 10.2 Seeded demo scenario (frozen)

| Item | Value |
| --- | --- |
| Eligible successful payments | ₹15,000 (matched by transaction/order ID) |
| Confirmed refunds | ₹0 |
| Fee rule | Seeded rule with rate 0 and flat amount 0, so documented fees = ₹0 |
| Documented tax | ₹0 |
| `expected_net` | ₹15,000 |
| Observed in synthetic ledger | ₹9,000 |
| `discrepancy` | ₹6,000 |
| Expected settlement date | Seeded as already past, so reason code is `OVERDUE` |
| Re-sync approval threshold | ₹5,000 (configurable); ₹6,000 exceeds it, so approval is required |

Every such row is marked `SYNTHETIC_DEMO`. Do not represent it as Paytm production data. After "Simulate bank settlement" adds the missing ₹6,000 entry, observed = ₹15,000 and verification passes.

---

## 11. Policy and Human Approval

| Action | Decision | Rule |
| --- | --- | --- |
| Read own transaction status | ALLOW | Authenticated + tenant-scoped. |
| Calculate discrepancy | ALLOW | Required source records exist; deterministic code. |
| Create support case | ALLOW | Low-risk operational action. |
| Assign internal queue | ALLOW | Support role or approved workflow; audited. |
| In-app status update | ALLOW | Approved template; no sensitive data. |
| Settlement re-sync request, discrepancy ≤ threshold | ALLOW | Mock adapter; no money movement; idempotent; audited. |
| Settlement re-sync request, discrepancy > threshold | REQUIRE_APPROVAL | Support role approves; version and action hash re-checked on resume. |
| Initiate refund | REQUIRE_APPROVAL / DENY in MVP | Financially sensitive; no live execution in demo. |
| Transfer funds / change bank details | DENY | Out of scope and high risk. |
| Close case | ALLOW only after verification PASS | Prevent false resolution. |
| Outbound phone call | Consent + configured provider required | Otherwise in-app voice only. |

A graph pause is not a security boundary. On resume, re-check reviewer role, case version, action hash, action parameters and policy. Frontend state cannot authorize an action. A mismatch returns 409 CONFLICT and the approval must be requested again.

---

## 12. Integrations and Free-First Stack

| Layer | Recommended | Free / cost reality |
| --- | --- | --- |
| Frontend | React + Vite + TypeScript + Tailwind + shadcn/ui | Open-source; free local development. |
| Backend | Python + FastAPI + Pydantic + async SQLAlchemy + Alembic | Open-source; free local development. |
| Agent | LangGraph | Open-source framework; self-host runtime. |
| Database | PostgreSQL | Open-source; local Docker is reliable. |
| Queue/cache | No Redis; `followup_jobs` table claimed with `FOR UPDATE SKIP LOCKED`; `llm_cache` table | Reduce setup risk; add Redis only if required. |
| LLM | Gemini API free tier or Sarvam API | Free tiers have model/rate limits and data terms; verify live account limits. |
| Indian voice (primary) | Sarvam STT/TTS | Docs list ₹100 signup credits for verified users; usage is charged after credits. |
| Voice fallback | Browser speech APIs / MediaRecorder + typed fallback | Browser/device support varies; always offer text. |
| Telephony | Twilio/Exotel adapter only if approved and funded | Future only; do not make PSTN a P0 dependency. |
| Tests | Pytest, HTTPX, Vitest, Playwright | Open-source; run locally. |
| Deployment | Docker Compose local; optional Vercel/Render preview | Free tiers have limits/sleep/resource constraints; local is finale fallback. |
| Tunnel | Cloudflare Tunnel or ngrok for the Paytm webhook only | Free tiers sufficient. |
| Monitoring | Structured logs, trace IDs, health endpoint, `tool_executions` | No paid monitoring required for MVP. |

### 12.1 Provider Adapter Interfaces

Implement `LLMProvider.generate_structured()`, `SpeechToText.transcribe()`, `TextToSpeech.synthesize()`, `PaymentProvider.get_transaction_status()`, `SettlementProvider.list_entries()` and `SettlementOpsProvider.request_resync()`. Keep vendor SDK code inside adapters so the workflow remains provider-independent. Each interface has a `mock` implementation.

### 12.2 Provider fallback chain

| Capability | Order |
| --- | --- |
| LLM | `LLM_PROVIDER` (gemini or sarvam) -> deterministic demo cache -> mock |
| Speech to text | Sarvam -> browser speech -> typed input |
| Text to speech | Sarvam -> browser speech synthesis -> text only |
| Payment status | Paytm staging -> labelled fixtures (never silently mixed) |
| Settlement | Synthetic ledger (production API is not available in staging) |
| Settlement Ops | Mock adapter (clearly labelled) |

### 12.3 Deterministic demo mode

With `DEMO_DETERMINISTIC=true`: LLM temperature is 0; each LLM request is hashed and its response stored in `llm_cache`; a recorded fixture set for the golden scenario (all three languages) can be replayed with no network. The UI shows a small "replay mode" badge when responses come from the cache. This is a reliability feature and must be disclosed in the demo.

### 12.4 Multilingual support

- Supported: English (`en`), Hindi (`hi`), Marathi (`mr`).
- Language is detected from the merchant's message (or the selector) and stored on the conversation.
- Money amounts, IDs, dates and case numbers are never translated or reformatted by the LLM; they are inserted from backend values.
- Merchant-visible status templates exist in all three languages.
- Voice: Sarvam is primary for all three; browser speech is the fallback and may support fewer languages.

### 12.5 Paytm Integration Truth

- Paytm states developers can sign up for a Paytm for Business account and obtain test API keys for testing. Keys are merchant-specific and must remain server-side.
- Payment callbacks/webhooks can notify the backend of payment/refund status; validate the documented checksum/signature and deduplicate events.
- Paytm Settlement API documentation states it is production-only and not hosted in staging. Therefore, use a clearly labelled synthetic settlement ledger for the finale unless authorized production access is explicitly available.
- Do not use real merchant data without authorization. Keep Paytm staging data and synthetic demo data visibly distinct.
- The Settlement Ops adapter is a **mock** of an internal operations system. Label it as such in the UI and the pitch.

---

## 13. Security, Privacy and Compliance

- Never ask for, log, store or repeat UPI PIN, OTP, full card number, CVV, bank password or full bank credentials.
- **Input redaction:** a sanitizer masks OTP-, PIN- and card-number-like patterns in merchant text before it is logged, stored or sent to any LLM. If a merchant volunteers such data, the agent tells them not to share it.
- **Prompt injection:** treat all merchant text, transaction notes and any retrieved text as untrusted data, never as instructions. The system prompt and tool allowlist are fixed server-side.
- Allowlist tools; validate every tool-call argument and every structured LLM output against Pydantic schemas; one repair retry, then deterministic fallback or human escalation.
- Never trust LLM output as SQL, identity, arithmetic, authorization or payment proof.
- Store Paytm MID/key, Gemini key and Sarvam key only in backend environment variables or secret manager; never in frontend or Git.
- Commit `.env.example` with placeholders; `.env` is gitignored. Rotate any exposed key.
- Authenticate every API request; enforce tenant scoping through `ScopedRepository`.
- Use roles: MERCHANT, SUPPORT_AGENT, SUPERVISOR. Default-deny sensitive actions.
- The verifier uses a read-only database role.
- Validate Paytm callback/webhook checksums; deduplicate events; make processing idempotent.
- Use HTTPS in deployment; restrict CORS; rate-limit endpoints; validate request sizes.
- Obtain microphone permission; show recording state; avoid retaining raw audio unless needed and consented.
- Disclose AI identity in voice sessions; offer human handoff; respect consent and opt-out.
- Use synthetic or masked data in the public demo; do not send real customer data to LLMs.
- Maintain append-only audit events for case changes, approvals and external actions.

---

## 14. Reliability and Failure Handling

| Failure | Required behaviour |
| --- | --- |
| LLM timeout / quota | Bounded retry; fall back to deterministic demo cache, then mock; keep case tools available. |
| LLM returns invalid structure | One repair retry, then deterministic path or human escalation. |
| Sarvam unavailable | Fall back to browser speech, then text entry; do not block support. |
| Paytm staging unavailable | Show integration unavailable and use labelled fixtures; never silently mix data. |
| Duplicate webhook | Deduplicate by event ID/hash; idempotent processing. |
| Database unavailable | Controlled 503; do not acknowledge writes. |
| Case action timeout | Check idempotency key before retry; prevent duplicates. |
| Re-sync request timeout | Check `resync_requests` idempotency key; never send a second request blindly. |
| Unauthorized / stale approval | Reject 403 / 409; re-check current policy, version and hash. |
| Follow-up worker race | `SKIP LOCKED` claim; no duplicate runs. |
| Verification fails | Remain IN_PROGRESS/PENDING_EXTERNAL; explain what remains unverified. |
| Mic permission denied | Immediately offer text chat. |

---

## 15. Testing and Definition of Done

| Test layer | Required coverage |
| --- | --- |
| Unit | Decimal reconciliation, SLA reason codes, policy, case transitions and versioning, tenant scope, idempotency, validation, input redaction. |
| Integration | Repositories, LangGraph tools, provider adapters mocked, webhook signature/dedupe, approval resume with stale version/hash, follow-up claim. |
| API | Auth and 400/401/403/404/409/429/503 responses; SSE stream scope. |
| E2E | Complaint -> investigate -> case -> approval -> re-sync -> simulate settlement -> fresh verify -> resolve; chat-to-voice switch; language switch. |
| Resilience | LLM/STT unavailable, replay mode, duplicate webhook, DB failure, retry without duplicate write. |
| Security | Cross-merchant IDOR on every route, secret leak scan, forbidden action, no OTP/PIN collection, tool schema has no `merchant_id`, verifier role cannot write, prompt-injection sample strings ignored. |

### 15.1 Acceptance Checklist

- [ ] Judge can log in without manual database edits.
- [ ] Seeded payment and settlement discrepancy is visible (₹15,000 expected, ₹9,000 observed, ₹6,000 `OVERDUE`).
- [ ] Source type is clearly labelled PAYTM_STAGING or SYNTHETIC_DEMO; the mock Settlement Ops adapter is labelled mock.
- [ ] Agent retrieves evidence through backend tools and displays it with a live trace.
- [ ] Discrepancy and reason code use Decimal-based backend code.
- [ ] Case is created exactly once and has a visible ID/timeline.
- [ ] Re-sync request above the threshold is paused for approval.
- [ ] Unauthorized user cannot approve via direct API call.
- [ ] Approval on a changed case version or action hash is rejected with 409.
- [ ] No tool input schema contains `merchant_id`.
- [ ] Case cannot be resolved without fresh verification PASS, and the verifier cannot write.
- [ ] Verification panel shows a before/after diff and timestamp.
- [ ] Chat and voice share the same conversation/case context.
- [ ] Same case works in English and at least one of Hindi or Marathi.
- [ ] Metrics tile shows response and resolution times.
- [ ] Voice/LLM failure leaves typed chat and case tracking usable; replay mode works with the LLM offline.
- [ ] No secrets, OTPs, PINs or full bank credentials appear in UI/logs/repository.

---

## 16. Finale Demo Script (4 to 5 Minutes)

| Time | Show | Narration |
| --- | --- | --- |
| 0:00-0:30 | Merchant dashboard | OpsSaathi is a shared operations teammate, not a FAQ chatbot. |
| 0:30-1:15 | Ask by chat or voice (switch language once): "My ₹6,000 payment is missing from settlement." | Same case context works across chat and voice, in the merchant's language. |
| 1:15-2:00 | Investigation panel with live trace | Agent retrieves payment records and the labelled synthetic ledger; backend calculates the discrepancy and marks it OVERDUE. |
| 2:00-2:45 | Policy + case creation | Case creation is allowed; the re-sync request above the threshold is held for approval. |
| 2:45-3:30 | Support console | Human reviewer sees evidence and approves; mock Settlement Ops acknowledges the re-sync. |
| 3:30-4:15 | Simulate bank settlement; run Verify | Fresh read by a read-only verifier shows the before/after diff; only then is the case resolved. |
| 4:15-5:00 | Metrics, audit timeline, architecture | Show outcome metrics, source labels, event history, human oversight and fallbacks. |

> **Demo safety.** Use seeded data and a reset button. Never depend on a real payment, live settlement or outbound phone call to complete judging. If the LLM is slow, enable replay mode and say so.

---

## 17. Build Plan: 13-15 November 2026

| When | Deliverable | Exit condition |
| --- | --- | --- |
| Fri 13 Nov, 17:00-19:30 | External keys; repo; contract (schema, OpenAPI, adapter and tool stubs); seed; Compose; `AGENTS.md` | One command starts app/API/DB; health endpoint works. **Gate 1.** |
| Fri 13 Nov, 19:30-23:30 | Domain services (reconciliation, policy, state machine, RBAC/scope); route implementations; UI shell; graph skeleton | Tests green; chat reaches graph stub. **Gate 2.** |
| Sat 14 Nov, 08:00-13:00 | Investigation wiring, case creation, approval flow, verification, timeline | Golden path works by hand and premature close is blocked. **Gate 3.** |
| Sat 14 Nov, 13:00-18:30 | Voice (Sarvam + browser), Gemini, Paytm staging, webhooks, follow-up worker, re-sync tool, SSE trace, multilingual, metrics, replay mode, failure drills | Golden path passes with each integration on and off. **Gate 4.** |
| Sat 14 Nov, 18:30-23:30 | E2E, API and security tests, final audit, deck, runbook | **Gate 5: feature freeze.** |
| Sun 15 Nov | Rehearsal, local backup, recording, internet/API checks | Golden demo passes twice from clean reset. |

---

## 18. Team Workstreams

| Workstream | Responsibilities |
| --- | --- |
| Product/demo lead | Scope freeze, user story, acceptance criteria, pitch alignment, demo narration. |
| Frontend | Dashboard, chat/voice, case details, operations console, approval and verification panels, metrics tile, loading/error states. |
| Backend/data | FastAPI, PostgreSQL, migrations, fixtures, reconciliation, auth/RBAC, `ScopedRepository`, case lifecycle, verifier role. |
| Agent/integrations | LangGraph, typed tools, Gemini/Sarvam/Paytm/Settlement Ops adapters, traces, SSE, replay cache. |
| QA/release | Golden scenario, test checklist, Docker, deployment, secrets, demo reset and fallback rehearsal. |

Assign actual owners within Two Bits. Do not invent names in the PRD. If the team is small, combine workstreams but keep one accountable owner per deliverable. Each AI coding lane works on its own branch in its own git worktree and follows `AGENTS.md`.

---

## 19. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Paytm staging credentials unavailable | Use provider adapter and labelled synthetic fixtures; disclose status. |
| Settlement API unavailable in staging | Use synthetic settlement data; official docs say production-only. |
| LLM free-tier quota | Short prompts, structured outputs, cache, replay mode and deterministic fallback. |
| Sarvam access/credits unavailable | Register with event email early; browser voice/text fallback. |
| Telephony cost/compliance | Keep PSTN optional; demonstrate in-app voice. |
| Scope creep | Freeze P0 and P1 list at Gate 5; no new feature before acceptance tests pass. |
| Hallucinated financial result | Backend tools only; source provenance; fresh independent verification. |
| Judge doubts verification is real | Read-only verifier role; before/after diff; labelled simulation action. |
| Venue network failure | Local Docker Compose, seeded offline demo, replay mode. |
| AI coding tool conflicts across lanes | OpenAPI contract as the only interface; one worktree per lane; `AGENTS.md` file ownership rules. |

---

## 20. Decisions Required Immediately

1. Assign team owners for the five workstreams.
2. Confirm Paytm staging MID and Merchant Key availability; never paste keys into chat or documents.
3. Register/access Sarvam AI using the same email used for hackathon registration, as instructed by organizers.
4. Run a live provider test and select Gemini or Sarvam as the primary LLM; keep the fallback chain.
5. Confirm the frozen seed scenario in §10.2 and the ₹5,000 re-sync threshold.
6. Run a clean-machine setup and full golden demo before travelling.

---

## 21. Official References

- Paytm developer documentation: https://www.paytmpayments.com/docs
- Paytm test API access FAQ: https://business.paytm.com/support/can-i-try-paytms-payment-apis-and-sdks-for-free
- Paytm API keys dashboard: https://dashboard.paytm.com/next/apikeys
- Paytm callback and webhook docs: https://www.paytmpayments.com/docs/callback-and-webhook
- Paytm Settlement API (production-only, not hosted on staging): https://www.paytmpayments.com/docs/api/settlement-api
- Gemini API pricing / free tier: https://ai.google.dev/gemini-api/docs/pricing
- Sarvam pricing / signup credits: https://docs.sarvam.ai/api/getting-started/pricing
- Twilio trial limits: https://www.twilio.com/docs/usage/trials
- Render free service limits: https://render.com/docs/free
- Vercel Hobby plan: https://vercel.com/docs/plans/hobby

---

## Appendix A: Environment Template

```bash
# .env.example only; never commit real .env
APP_ENV="development"
DATABASE_URL="postgresql+psycopg://user:password@localhost:5432/opssaathi"
VERIFIER_DATABASE_URL="postgresql+psycopg://verifier_ro:password@localhost:5432/opssaathi"  # read-only role
JWT_SECRET="CHANGE_ME"

LLM_PROVIDER="gemini"          # gemini | sarvam | mock
GEMINI_API_KEY="YOUR_KEY"
SARVAM_API_KEY="YOUR_KEY"

PAYTM_ENVIRONMENT="staging"
PAYTM_MID="YOUR_TEST_MID"
PAYTM_MERCHANT_KEY="YOUR_TEST_MERCHANT_KEY"
PAYTM_WEBSITE_NAME="WEBSTAGING"

FRONTEND_ORIGIN="http://localhost:5173"
VOICE_PROVIDER="sarvam"        # sarvam | browser | twilio (browser is the automatic fallback)
DEFAULT_LANGUAGE="en"          # en | hi | mr

DEMO_DATA_MODE="true"
DEMO_DETERMINISTIC="false"     # true = temperature 0, cache and replay
RESYNC_APPROVAL_THRESHOLD_INR="5000"
SETTLEMENT_OPS_ADAPTER="mock"
```

## Appendix B: Repository Structure

```
opssaathi-ai/
  AGENTS.md                      # rules for AI coding tools (read first)
  apps/web/                      # React + Vite + TypeScript
  services/api/app/
    api/v1/                      # FastAPI routes
    core/                        # config, auth, logging, redaction
    db/                          # async SQLAlchemy models, migrations, ScopedRepository
    domain/                      # reconciliation, SLA, policy, case lifecycle, verification
    agents/                      # LangGraph graph, nodes, prompts
    tools/                       # typed allowlisted tools (no merchant_id inputs)
    integrations/{paytm,gemini,sarvam,voice,settlement_ops}/
    workers/                     # follow-up jobs
    tests/
  infra/docker-compose.yml
  docs/{PRD,API_CONTRACTS,DEMO_RUNBOOK}.md
  .env.example
  .gitignore
  README.md
```

## Appendix C: Non-Negotiable Product Rule

> **Trust rule.** OpsSaathi must never invent payment status, perform an unauthorized financial action, expose one merchant's data to another, or announce resolution without independent verification. A smaller working product with trustworthy evidence is stronger than a broad demo with fake functionality.

---

Two Bits | Paytm Build for India AI Hackathon, Pune Finale | v1.1 | 13 Nov 2026
