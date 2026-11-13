# BUILD_PLAN.md: OpsSaathi AI

Shared execution plan for the human and both AI tools. Read this together with `AGENTS.md` (rules) and `docs/PRD.md` v1.1 (requirements). If anything here conflicts with the PRD, the PRD wins; tell the human.

Plan written Fri 13 Nov 2026, 17:30 IST. Finale: Sun 15 Nov 2026, Partex.AI, Hinjawadi, Pune.

---

## 0. How to use this document

**Owners**

| Tag | Who | What they do |
| --- | --- | --- |
| `[HUMAN]` | Team member | Keys, decisions, merges, gate checks, final review |
| `[CODEX]` | Codex (limited weekly credits) | Core trust logic only: money, permissions, tenant scope, approval resume, verification, webhook signature, security tests, final audit |
| `[AGY]` | Antigravity (plenty of credits) | Scaffolding, routes, UI, agent wiring, adapters, workers, E2E, deck and docs |

**Task IDs.** Every task has an ID like `P2-C1` (Phase 2, Codex task 1) or `P2-A3` (Phase 2, Antigravity task 3). Tell an AI "do task P2-C1" and it must read only that task, `AGENTS.md`, and the PRD sections the task lists.

**Task template.** Each task lists: Owner, Depends on, Read (PRD sections and files), Files to create or change, Steps, Acceptance (what must be true), Evidence (what the AI reports back).

**Rule for all AIs.** Do the task you were given. Do not start the next task. Report evidence and stop.

---

## 1. Safety measures to ensure correct work

These apply to every phase. They are the reason both tools can work fast without breaking the product.

### 1.1 Seven safeguards

1. **Contract first.** The OpenAPI file, adapter interfaces and tool signatures (PRD §7.3, §9, §12.1) are fixed in Phase 1. Lanes only talk to each other through them. Nobody changes a contract without the human.
2. **Two-key rule for risky code.** Anything touching money, permissions, tenant scope, approval resume or verification is written by one tool and reviewed by the other (or by the human). Codex writes it; Antigravity's output on these areas is never merged without a Codex review or human review.
3. **Tests with the code.** No task is done until its tests exist and pass. An AI may never delete or weaken a test to make it pass.
4. **Guard script.** `scripts/guard.sh` (task P1-A7) runs on every commit and in CI. It fails the build if it finds: `float` used for money in `domain/`, `merchant_id` in any tool input schema, `.env` or key-like strings in tracked files, string-built SQL, or an unscoped query on merchant tables.
5. **Gates with git tags.** Each phase ends in a gate. If the gate checklist is not fully green, nobody starts the next phase. Passing a gate means `git tag gate-N` on a clean `main`. Failing means roll back to the last tag or fix forward, decided by the human.
6. **Stop-and-ask triggers.** An AI must stop and ask the human (one short question, no coding yet) if: the task conflicts with `AGENTS.md` or the PRD; a contract would need to change; a rule about money, permissions or verification is unclear; it needs to edit outside its lane; the same test fails twice for the same reason.
7. **Small diffs, own worktree.** One branch and one git worktree per task. Aim for under about 400 changed lines per merge. The human reviews every merge to `main`.

### 1.2 Per-task checklist the AI must self-run before reporting done

- [ ] Task acceptance criteria met, each one named in the report.
- [ ] Only files in the task's list (and their tests) changed.
- [ ] Targeted tests pass; `ruff` and `mypy` (or `eslint` and `tsc` for web) pass on touched files.
- [ ] `scripts/guard.sh` passes.
- [ ] No float money, no unscoped queries, no `merchant_id` in a tool schema, no secrets, no raw sensitive input in logs.
- [ ] Report is short: files changed, tests run and result, open questions.

### 1.3 Human review checklist at every merge

- [ ] Diff touches only the task's files.
- [ ] Tests were added, not removed or loosened.
- [ ] If the area is risky (money, permissions, scope, approval, verification), the other tool or the human reviewed it.
- [ ] Guard script and the test suite pass on the branch.
- [ ] Seed scenario unchanged: ₹15,000 expected, ₹9,000 observed, ₹6,000 `OVERDUE`, threshold ₹5,000.

### 1.4 Golden run script

`scripts/golden_run.md` (task P1-A8) lists the exact end-to-end steps with expected results. From Gate 3 onwards, run it by hand (and later via Playwright) at every gate and before every merge that touches the agent, policy, cases or verification.

### 1.5 What "wrong" looks like (tell the AI to watch for these)

- A reply that states an amount or status not present in a tool result.
- A case that becomes `RESOLVED` without a verification PASS.
- Any route that returns data for a merchant other than the session's.
- An approval that still succeeds after the case changed.
- A tool that accepts or returns `merchant_id`.
- A test that passes only because the mock returns the answer.

---

## 2. Codex credit discipline

Codex has limited weekly credits. Quality must not drop, so spend credits only on the work Codex is best used for: precise, test-backed code in the trust-critical areas.

### 2.1 Prompt to paste at the start of every Codex session

```text
You are working on the OpsSaathi AI repo. You have a LIMITED credit budget. Spend it only on the single task I give you.

BEFORE ANYTHING ELSE
- Read AGENTS.md once, and only the PRD sections and files named in the task. Do not scan or summarize the whole repo.
- If the task is ambiguous, or conflicts with AGENTS.md or the PRD, ask me ONE short question and wait. Do not guess about money, permissions or verification.

HOW TO WORK
- Do only the task I name. Do not start the next task, add features, refactor, rename, or touch files outside the task's list.
- Write the code and its tests together. Tests are mandatory. Never skip, delete or weaken a test to save credits.
- Do not generate UI, scaffolding, docs, READMEs, comments essays or example data unless the task says so.
- Do not install packages, browse the web, or change config unless the task says so.
- Read each file at most once. Make edits in as few passes as possible. Do not re-read a file after you edit it.
- Run only the targeted tests for your task (for example: pytest services/api/app/tests/domain/test_reconciliation.py -q), then the guard script once at the end. Do not run the full suite repeatedly.
- If the same test fails twice for the same reason, STOP. Report the failure and your best hypothesis. Do not loop.
- Do not write long explanations or restate the task. No thinking-out-loud in the output.

STOP CONDITION
- As soon as the task's acceptance criteria pass, stop.

FINAL REPORT (10 lines or fewer)
1. Files changed
2. Tests added and result
3. Acceptance criteria met (one line each)
4. Open questions or risks
Nothing else.
```

### 2.2 Codex budget guide

These percentages are planning estimates, not measured. Check your remaining credits after the first task and adjust.

| Codex task | Approx. share of weekly credits |
| --- | --- |
| P2-C1 Reconciliation | 12% |
| P2-C2 Policy engine and case state machine | 12% |
| P2-C3 Auth, scope, redaction | 12% |
| P3-C1 Approval resume checks | 10% |
| P3-C2 Verification service | 10% |
| P4-C1 Webhook signature and dedupe | 8% |
| P5-C1 Security test suite | 8% |
| P5-C2 Final audit | 8% |
| Reserve for failures found at gates | 20% |

If credits run low: keep the reserve, drop nothing from the table, and move only the "tests for Antigravity-written code" review (not the writing) to the human. Never trade correctness of the trust logic for credits.

### 2.3 Things Codex should NOT be used for

UI, scaffolding, migrations boilerplate, route wiring, adapters, docs, the pitch deck, seed data, Playwright tests, formatting, or exploring the repo. All of these go to Antigravity.

---

## 3. Antigravity prompt (paste at the start of every session)

```text
You are working on the OpsSaathi AI repo. Read AGENTS.md and the PRD sections named in my task. Do only the task I name, inside its lane and file list.

RULES
- Follow AGENTS.md trust rules exactly. Never edit domain/ logic, ScopedRepository, redaction, approval-resume checks, verification service, or webhook signature code. Those belong to the Core lane. If your task seems to need a change there, stop and tell me.
- Call Core-lane functions through their frozen signatures (see BUILD_PLAN.md section 4). If a Core function is still a stub, code against the stub and mark TODO(core).
- Do not change the OpenAPI contract, adapter interfaces or tool signatures without asking me.
- Write tests with the code. Run the targeted tests, ruff/mypy (or eslint/tsc), and scripts/guard.sh before reporting.
- Work on your own branch and worktree. Do not touch main.
- No secrets in files or logs. Every adapter has a mock. Every screen has loading, empty and error states.

FINAL REPORT (short): files changed, tests run and result, acceptance criteria met, open questions.
```

---

## 4. Frozen signatures between lanes

Antigravity creates these as typed stubs in P1-A5 (raising `NotImplementedError`). Codex implements them in its tasks without changing the signatures. The human approves any change.

| Module | Function / class | Returns |
| --- | --- | --- |
| `domain/reconciliation.py` | `reconcile(captures, refunds, fees, taxes, entries, expected_settlement_date, now)` | `ReconciliationResult` (expected_net, observed, discrepancy, reason_code, trace, source_ids) |
| `domain/policy.py` | `evaluate(action, context)` | `PolicyDecision` (decision, reason_code) |
| `domain/case_lifecycle.py` | `transition(case, to_status, expected_version, actor)` | `CaseTransition` (new status, new version, event) or raises `CONFLICT`/`FORBIDDEN` |
| `domain/approvals.py` | `validate_resume(approval, case, reviewer, action)` | `None` or raises `FORBIDDEN`/`CONFLICT` |
| `domain/verification.py` | `verify_resolution(case_id, rule, verifier_session, now)` | `VerificationResult` (PASS/FAIL, before, after, evidence_timestamp) |
| `db/scoped_repository.py` | `ScopedRepository(session, merchant_id)` | Repositories exposing only scoped queries |
| `core/redaction.py` | `redact(text)` | `RedactionResult` (clean_text, redacted_types) |
| `core/webhook.py` | `validate_paytm_checksum(payload, checksum, key)` | `bool` |

---

## 5. Phase plan

Times are IST. The plan assumes work until about Sat 23:30, a sleep break, then a final rehearsal on Sunday.

### Phase 0: External setup (Fri 17:30-18:15)

Run these in the background while Phase 1 starts. A missing key never blocks the build; every provider has a fallback (PRD §12.2).

**P0-H1 `[HUMAN]` Provider access**
1. Register for Sarvam with the same email used for hackathon registration; verify it; copy the API key.
2. Get the Paytm staging test MID and merchant key from the Paytm for Business dashboard.
3. Create a Gemini API key in Google AI Studio.
4. Install Cloudflare Tunnel or ngrok (needed only for the Paytm webhook).
5. Put keys only in a local `.env`. Never paste keys into any chat or document.
- Acceptance: keys saved locally, or missing ones noted.

**P0-H2 `[HUMAN]` Machine and repo**
1. Confirm Docker, Python 3.11+, Node 20+ and git work.
2. Create the git repo; add `AGENTS.md` (root), `docs/PRD.md` and this `docs/BUILD_PLAN.md`.
3. Open Codex and Antigravity on the same repo folder. Create one git worktree per lane later.
- Acceptance: both tools can open the repo; both docs are committed.

**P0-H3 `[HUMAN]` Confirm decisions**
1. Confirm the frozen seed scenario (₹15,000 / ₹9,000 / ₹6,000, `OVERDUE`) and the ₹5,000 re-sync threshold.
2. Note the team members and who reviews merges.
- Acceptance: decisions written at the top of `docs/DEMO_RUNBOOK.md`.

---

### Phase 1: Foundation and contract (Fri 18:15-20:00)

Goal: one command starts everything, the contract exists, and every lane has stubs to build against. Mostly Antigravity, run in order below (some in parallel where noted).

**P1-A1 `[AGY]` Repo scaffold and Compose**
- Read: PRD §7, §12, Appendix B.
- Steps: create the directory structure from Appendix B; `.gitignore` (includes `.env`); `.env.example` from Appendix A; `infra/docker-compose.yml` with Postgres, API and web; `GET /api/v1/health`.
- Acceptance: `docker compose up` starts all three from clean; health returns OK.
- Evidence: command output summary.

**P1-A2 `[AGY]` Database models and migration** (after P1-A1)
- Read: PRD §8.
- Steps: async SQLAlchemy models for every table in §8, including `support_cases.version`, `approvals.case_version`, `approvals.action_hash`, `fee_rules`, `resync_requests`, `followup_jobs`, `llm_cache`; UUID keys; `NUMERIC(12,2)`; indexes; `source_type` on financial rows; one Alembic migration; a read-only role `opssaathi_verifier` with SELECT only.
- Acceptance: migration applies on a clean database; verifier role cannot INSERT (include a small test).
- Evidence: migration result; test result.

**P1-A3 `[AGY]` API contract stubs** (after P1-A1, parallel with P1-A2)
- Read: PRD §9, §9.1.
- Steps: every route in §9 as a FastAPI stub with Pydantic request and response models, the standard envelope, and the stable error codes; export the OpenAPI file to `docs/openapi.json`.
- Acceptance: `/docs` lists every route; OpenAPI file committed.

**P1-A4 `[AGY]` Adapter interfaces and mocks** (parallel)
- Read: PRD §12.1, §12.2.
- Steps: define `LLMProvider`, `SpeechToText`, `TextToSpeech`, `PaymentProvider`, `SettlementProvider`, `SettlementOpsProvider`; add a `mock` implementation for each.
- Acceptance: each interface has a mock; importing them has no vendor SDK dependency outside `integrations/`.

**P1-A5 `[AGY]` Core-lane stubs with frozen signatures** (after P1-A2)
- Read: this plan §4.
- Steps: create each function and class in §4 with the exact signature and `NotImplementedError`; create `ScopedRepository` skeleton; add empty test files named for each Codex task.
- Acceptance: stubs import cleanly; signatures match §4.

**P1-A6 `[AGY]` Tool stubs** (parallel)
- Read: PRD §7.3.
- Steps: typed tool stubs for all 11 tools. No tool input schema may contain `merchant_id`; the scope is bound from the session when the tool is built.
- Acceptance: a test iterates every tool schema and asserts no `merchant_id` field.

**P1-A7 `[AGY]` Guard script and pre-commit**
- Read: this plan §1.1(4).
- Steps: write `scripts/guard.sh` with the checks listed there; hook it to pre-commit and a CI-style `make guard`.
- Acceptance: a deliberately bad sample (float money, `merchant_id` in a tool schema, a fake key) makes it fail; the clean repo passes.

**P1-A8 `[AGY]` Seed, reset and golden run script**
- Read: PRD §10.2, §16.
- Steps: seed script for the frozen scenario with every row `SYNTHETIC_DEMO` (fee rule at rate 0 and flat 0; expected settlement date in the past); `POST /api/v1/demo/reset`; demo users (merchant, support agent, supervisor); write `scripts/golden_run.md` with exact steps and expected results.
- Acceptance: reset gives identical data every time (expected ₹15,000, observed ₹9,000).

**P1-H1 `[HUMAN]` Gate 1 check**
- [ ] `docker compose up` works from a clean clone.
- [ ] Health returns OK; `/docs` shows every route.
- [ ] Seed and reset work; numbers are right.
- [ ] Guard script catches a deliberate violation.
- [ ] Stubs match §4.
- Then: merge to `main` and `git tag gate-1`.

---

### Phase 2: Core trust logic and lane skeletons (Fri 20:00-Sat 00:00)

Codex and Antigravity work in parallel on separate worktrees. Codex tasks run one after another in the order below.

#### Codex lane

**P2-C1 `[CODEX]` Reconciliation and SLA reason codes**
- Read: PRD §10, §10.1, §10.2; `domain/reconciliation.py` stub.
- Files: `domain/reconciliation.py`, `tests/domain/test_reconciliation.py`.
- Steps: implement `reconcile` with Decimal only; match by transaction or order ID, never amount alone; exclude failed and cancelled payments; include only confirmed refunds; never infer fees; return reason codes `NO_DISCREPANCY`, `WITHIN_SLA_PENDING`, `OVERDUE`, `MISSING`, `INSUFFICIENT_EVIDENCE`; include a calculation trace and source IDs; clock is injected.
- Tests: the frozen scenario (₹6,000 `OVERDUE`); before the due date (`WITHIN_SLA_PENDING`); failed payment excluded; confirmed refund included; unconfirmed refund ignored; missing fee data gives `INSUFFICIENT_EVIDENCE`; no entry in a closed batch gives `MISSING`; amount-only match is rejected; no float is used.
- Acceptance: all tests pass; guard passes.

**P2-C2 `[CODEX]` Policy engine and case state machine** (after P2-C1)
- Read: PRD §8.1, §11; stubs in `domain/policy.py` and `domain/case_lifecycle.py`.
- Files: those two modules and their tests.
- Steps: policy returns ALLOW, DENY or REQUIRE_HUMAN_APPROVAL with a reason code for every row of the PRD §11 table, including the ₹5,000 re-sync threshold (read from config, not hard-coded); state machine enforces the allowed transitions, checks `expected_version`, increments `version`, and emits an event; `RESOLVED` only reachable from `VERIFYING` with PASS.
- Tests: every policy row; refund requires approval; fund transfer denied; close denied without verification PASS; illegal transitions rejected; stale version gives `CONFLICT`.
- Acceptance: all pass.

**P2-C3 `[CODEX]` Auth, tenant scope and redaction** (after P2-C2)
- Read: PRD §7.4, §13; `db/scoped_repository.py`, `core/redaction.py`, `core/auth*`.
- Files: those modules and tests.
- Steps: `ScopedRepository` exposes only merchant-scoped queries (no unscoped method); role checks for MERCHANT, SUPPORT_AGENT, SUPERVISOR with default-deny; `redact` masks OTP, PIN, CVV and card-number-like text.
- Tests: merchant A cannot read merchant B's transaction, settlement, case or conversation by ID (404 or 403); merchant calling approve gets 403; redaction catches OTP, PIN, card patterns and leaves normal text unchanged.
- Acceptance: all pass.

#### Antigravity lane (in parallel; use stubs where Core is not ready)

**P2-A1 `[AGY]` Route implementations**
- Read: PRD §9; frozen signatures.
- Steps: implement transaction, settlement, merchant, case list/detail/create (idempotent via `Idempotency-Key`), assign, and audit logging through `ScopedRepository`; request IDs; rate limits; CORS restricted to `FRONTEND_ORIGIN`; envelope and error codes.
- Acceptance: API tests for 400, 401, 403, 404, 409, 429; duplicate create returns the same case.

**P2-A2 `[AGY]` Frontend shell**
- Read: PRD §6.
- Steps: demo login (merchant and support), merchant dashboard, chat workspace shell with language selector, `SourceBadge` component (`PAYTM_STAGING` / `SYNTHETIC_DEMO` / `MOCK`), generated API types from the OpenAPI file; loading, empty and error states.
- Acceptance: login works; dashboard shows seeded data with source badges.

**P2-A3 `[AGY]` Agent graph skeleton**
- Read: PRD §7.2.
- Steps: LangGraph with every node from §7.2 as a stub; Postgres checkpointer; tool wrapper that writes each call to `tool_executions`; mock LLM returning schema-valid output; Pydantic validation of tool arguments with one repair retry.
- Acceptance: a chat message goes through the graph and returns a stub reply; trace rows are written.

**P2-A4 `[AGY]` SSE trace endpoint**
- Read: PRD §9 (agent runs events).
- Steps: `GET /api/v1/agent/runs/{id}/events` streams node and tool events, scoped to the merchant's own runs.
- Acceptance: the UI receives events in order; another merchant's run ID is rejected.

**P2-H1 `[HUMAN]` Gate 2 check (target Sat 00:00)**
- [ ] Codex tests green; guard passes.
- [ ] IDOR test passes on case, transaction and settlement routes.
- [ ] A chat message reaches the graph and replies with a stub; trace visible.
- [ ] Seed scenario still exact.
- Then: merge both lanes, run the full suite, `git tag gate-2`. If late, stop and sleep; fatigue costs more than an hour.

---

### Phase 3: Golden path end to end (Sat 08:00-13:00)

Goal: complaint to verified resolution works by hand.

**P3-C1 `[CODEX]` Approval resume checks**
- Read: PRD §5.3, §11; `domain/approvals.py`.
- Files: `domain/approvals.py` and tests.
- Steps: `validate_resume` re-checks reviewer role, current `case.version`, `action_hash` (hash of action type plus parameters) and current policy; mismatch gives `CONFLICT`; wrong role gives `FORBIDDEN`.
- Tests: approve with the right role passes; merchant role fails; case changed after the request gives `CONFLICT`; action parameters changed gives `CONFLICT`; policy now DENY gives `FORBIDDEN`.
- Acceptance: all pass.

**P3-C2 `[CODEX]` Independent verification service** (after P3-C1)
- Read: PRD §7.5, §10; `domain/verification.py`.
- Files: `domain/verification.py` and tests.
- Steps: `verify_resolution` uses the read-only verifier session; fetches fresh records (no cached objects); compares to the recorded before-state; returns PASS or FAIL with before, after and evidence timestamp.
- Tests: PASS only when observed equals expected; FAIL while the ledger is unchanged; the premature-close test (resolve attempt without PASS is rejected); verifier session cannot write; verification does not reuse in-memory results.
- Acceptance: all pass.

**P3-A1 `[AGY]` Investigation wiring**
- Read: PRD §4 (FR-02 to FR-06), §7.2, §7.3.
- Steps: connect `find_transactions`, `get_settlement_entries` and `calculate_discrepancy` to `ScopedRepository` and Codex's `reconcile`; the LLM extracts category, amount, date and reference and asks for what is missing (never invents); sanitize input with `redact` before any LLM call; fixed system prompt, allowlisted tools.
- Acceptance: "My ₹6,000 payment is missing" yields an evidence summary with ₹15,000 / ₹9,000 / ₹6,000, `OVERDUE`, and source labels; every figure comes from a tool result.

**P3-A2 `[AGY]` Evidence and investigation panel**
- Steps: records checked, calculation trace, reason code, source badges, limitations, next action; live trace from SSE.
- Acceptance: panel matches the tool results exactly.

**P3-A3 `[AGY]` Policy, case creation and re-sync tool**
- Read: PRD §7.3, §11, FR-08, FR-19.
- Steps: the graph calls policy; creates exactly one case (idempotency key), assigns Settlement Operations, writes timeline events and a merchant-visible message; `request_settlement_resync` calls the mock Settlement Ops adapter with an idempotency key and stores a `resync_requests` row; above the threshold it creates an approval (storing case version and action hash) and pauses on the checkpoint.
- Acceptance: one case per complaint even on retry; the ₹6,000 re-sync waits for approval; no money-moving path exists.

**P3-A4 `[AGY]` Approval UI and ops console**
- Read: PRD §6.
- Steps: approval modal (action, policy reason, evidence, case version, approve, reject with required reason); operations console with queue, filters, approvals, assign, escalate, audit events, and the **Simulate bank settlement** button (demo mode only, audited, labelled as a demo simulation).
- Acceptance: a support user can approve; a merchant user cannot reach the console; the button writes the missing ₹6,000 as `SYNTHETIC_DEMO`.

**P3-A5 `[AGY]` Verification, timeline and case detail**
- Steps: wire `POST /cases/{id}/verify` to Codex's service; verification panel shows before and after diff, timestamp and the verifier label; case detail with timeline hiding internal notes from merchants; `RESOLVED` only via verification PASS.
- Acceptance: the golden run in `scripts/golden_run.md` passes by hand.

**P3-H1 `[HUMAN]` Gate 3 check (target Sat 13:00)**
- [ ] Run the golden run by hand: complaint, investigation, case, approval, re-sync, simulate settlement, verify, `RESOLVED`.
- [ ] Try to resolve before simulating the settlement: blocked.
- [ ] Try approval after changing the case: 409.
- [ ] Merchant A cannot see merchant B.
- [ ] No amount appears in a reply that is not in a tool result.
- Then: `git tag gate-3`. If this fails, nothing after matters; fix first.

---

### Phase 4: Voice, integrations and remaining P1 features (Sat 13:00-18:30)

Each integration is built behind its adapter with its fallback first, then the real provider is wired in. After each one, re-run the golden run.

**P4-A1 `[AGY]` Browser voice and channel continuity**
- Read: PRD §5.2, FR-11, FR-12.
- Steps: mic permission, visible recording state, transcript preview, submit to `/voice/transcriptions` in the same conversation; spoken reply with browser synthesis; typed fallback when permission is denied; AI-identity disclosure recorded at `/voice/sessions`.
- Acceptance: start in chat and continue in voice with the same case; permission denied shows text input immediately.

**P4-A2 `[AGY]` Gemini adapter and deterministic mode**
- Read: PRD §12.2, §12.3.
- Steps: structured output with schemas, bounded retry; fallback chain LLM, then `llm_cache`, then mock; `DEMO_DETERMINISTIC` sets temperature 0, caches by request hash, replays the golden scenario in all three languages; UI shows a "replay mode" badge when serving from cache.
- Acceptance: with the API key removed, the golden run still works in replay mode.

**P4-A3 `[AGY]` Sarvam STT/TTS adapters** (if key available; otherwise leave the mock and browser fallback)
- Steps: Sarvam as the primary voice provider for English, Hindi and Marathi; automatic fallback to browser speech, then text.
- Acceptance: disabling the Sarvam key falls back without breaking the flow.

**P4-A4 `[AGY]` Multilingual replies**
- Read: PRD §12.4, FR-17.
- Steps: detect language; store it on the conversation; localized merchant-visible templates in en, hi, mr; amounts, IDs, dates and case numbers inserted from backend values, never retranslated.
- Acceptance: the same case answered in English and Hindi or Marathi shows identical numbers.

**P4-A5 `[AGY]` Paytm staging adapter** (if credentials work)
- Steps: transaction status lookup behind `PaymentProvider`; if staging is unavailable, show "integration unavailable" and use labelled fixtures; never silently mix sources.
- Acceptance: source badge always reflects the real origin.

**P4-C1 `[CODEX]` Webhook signature and dedupe**
- Read: PRD §13; Paytm callback and webhook docs (the human pastes the checksum section into the task if the doc is needed); `core/webhook.py`.
- Files: `core/webhook.py`, webhook handler logic for dedupe, tests.
- Steps: validate the documented checksum; deduplicate by event ID and payload hash; idempotent processing.
- Tests: valid signature accepted; invalid rejected; duplicate processed once; replay does not double-apply.
- Acceptance: all pass.

**P4-A6 `[AGY]` Webhook endpoint wiring**
- Steps: `POST /api/v1/webhooks/paytm` calls Codex's validator and dedupe; expose through the tunnel; send a staging test event if credentials exist.
- Acceptance: a test event is stored once with `signature_valid` recorded.

**P4-A7 `[AGY]` Follow-up worker**
- Read: PRD FR-13, §12.
- Steps: worker claims jobs with `SELECT ... FOR UPDATE SKIP LOCKED`; re-checks status; notifies only on meaningful change; `POST /cases/{id}/followup/run` manual trigger.
- Acceptance: two workers never run the same job; the manual trigger works.

**P4-A8 `[AGY]` Metrics and integration health**
- Read: PRD FR-20, §6.
- Steps: `GET /api/v1/metrics` computes time to first response, time to verified resolution, handled vs escalated, repeat explanations avoided from `case_events`; metrics tile; integration health screen showing provider status and active provider, never secrets.
- Acceptance: tile updates after the golden run; health screen shows fallbacks correctly.

**P4-A9 `[AGY]` Failure drills**
- Read: PRD §14.
- Steps: script and run each: LLM key removed; Sarvam off; DB stopped; duplicate webhook; microphone denied; re-sync timeout; stale approval. Fix what breaks.
- Acceptance: every row in the §14 table behaves as written; case access stays usable.

**P4-H1 `[HUMAN]` Gate 4 check (target Sat 18:30)**
- [x] Golden run passes with every integration on.
- [x] Golden run passes with each integration off (LLM, Sarvam, Paytm).
- [x] Chat to voice continuity works; language switch works.
- [x] Metrics tile shows numbers.
- Then: `git tag gate-4`.

---

### Phase 5: Hardening and audit (Sat 18:30-23:30)

**P5-C1 `[CODEX]` Security test suite**
- Read: PRD §13, §15; `AGENTS.md` section 8.
- Files: `tests/security/` only.
- Steps: write tests for cross-merchant IDOR on every route; direct-API approve by an unauthorized role; no `merchant_id` in any tool schema; verifier role cannot write; no OTP, PIN, CVV or card collection or logging; prompt-injection sample strings in merchant text and transaction notes do not change tool calls; secret-leak scan of the repo and logs.
- Acceptance: tests exist and run; any failure is reported with the failing route or file, not silently fixed in another lane.

**P5-A1 `[AGY]` Playwright end-to-end**
- Steps: automate `scripts/golden_run.md`; chat to voice switch; language switch; premature close blocked; approval then verification.
- Acceptance: passes twice in a row from a clean reset.

**P5-A2 `[AGY]` API and resilience tests**
- Steps: 400, 401, 403, 404, 409, 429, 503 tests; retry without duplicate write; duplicate webhook.
- Acceptance: pass.

**P5-C2 `[CODEX]` Final audit** (after P5-C1, P5-A1, P5-A2)
- Read: the git diff since `gate-1`; PRD §15.1 checklist; PRD Appendix C; `AGENTS.md`.
- Files: none edited. Output a report only.
- Steps: check the diff against every unchecked item in §15.1 and every trust rule in `AGENTS.md`; list violations with file and line, ranked by severity; do not fix anything.
- Acceptance: a short ranked list. Fixes go back to the owning lane or the Codex reserve.

**P5-A3 `[AGY]` Fix audit findings in its own lanes.** **P5-C3 `[CODEX]`** fixes findings in Core files, using the reserve.

**P5-A4 `[AGY]` Pitch deck, runbook and README**
- Read: PRD §16.
- Steps: deck and `docs/DEMO_RUNBOOK.md` following the 4 to 5 minute script. Label simulated parts honestly: synthetic settlement ledger, mock Settlement Ops, in-app voice (not phone calls), replay mode when used. No claim of official Paytm endorsement.
- Acceptance: every claim in the deck is traceable to something implemented or labelled future.

**P5-A5 `[AGY]` Optional deployment preview.** Local Docker is the finale fallback; a preview is a bonus.

**P5-H1 `[HUMAN]` Gate 5 check and feature freeze (target Sat 23:30)**
- [x] All of PRD §15.1 is ticked.
- [x] Audit findings fixed or explicitly accepted in writing.
- [x] Guard script, full backend suite, frontend tests and Playwright pass.
- [x] No keys in the repo (secret scan clean); rotate any key that was ever exposed.
- Then: `git tag gate-5`. **From now on, bug fixes only. No new features.**

---

### Phase 6: Rehearsal and finale (Sun 15 Nov)

**P6-H1 `[HUMAN]`** Morning of the finale:
1. Clean-machine setup test: fresh clone, `.env` from `.env.example`, `docker compose up`, reset, golden run. Do it twice.
2. Time the 4 to 5 minute walkthrough. Assign who talks and who clicks.
3. Record a backup screen capture of the full golden run.
4. Test the local Docker version with wifi off (replay mode on).
5. Check keys: provider tests live, or note the fallbacks you will use and say so in the demo.
6. Pack: charged laptop, charger, hotspot, backup video, a copy of the repo on a USB drive.
7. At the venue: connect, run reset, run the golden run once before judging.

**P6-H2 `[HUMAN]` If something breaks on stage:** switch on replay mode, say so honestly, and continue with the local seeded demo. Never improvise a live fix in front of judges.

---

## 6. Dependency map (who waits for whom)

```
P0 (keys, human) ---------------------------------------------> used in P4
P1-A1 -> P1-A2 -> P1-A5 -> [Codex tasks can start]
P1-A1 -> P1-A3, P1-A4, P1-A6, P1-A7, P1-A8 (parallel)
Gate 1
P2-C1 -> P2-C2 -> P2-C3          (Codex, sequential)
P2-A1, P2-A2, P2-A3, P2-A4       (Antigravity, parallel; stubs for Core)
Gate 2
P3-C1 -> P3-C2                   (Codex)
P3-A1 -> P3-A2, P3-A3 -> P3-A4 -> P3-A5   (Antigravity)
Gate 3  (golden path by hand)
P4-A1..A9 and P4-C1 -> P4-A6
Gate 4
P5-C1, P5-A1, P5-A2 -> P5-C2 -> fixes -> P5-A4
Gate 5 (freeze)
P6 (rehearsal and finale)
```

## 7. Progress tracker (tick as you go)

- [ ] P0-H1 Provider access
- [ ] P0-H2 Machine and repo
- [ ] P0-H3 Decisions confirmed
- [ ] P1-A1 to P1-A8 done, **Gate 1**
- [ ] P2-C1, P2-C2, P2-C3 done
- [ ] P2-A1 to P2-A4 done, **Gate 2**
- [ ] P3-C1, P3-C2 done
- [ ] P3-A1 to P3-A5 done, **Gate 3**
- [x] P4-A1 to P4-A9 and P4-C1 done, **Gate 4**
- [x] P5-C1, P5-A1, P5-A2, P5-C2, fixes, P5-A4 done, **Gate 5 (freeze)**
- [ ] P6 rehearsal complete, backups ready

## 8. If you fall behind

Keep the order of value: the trust logic and golden path (Phases 1 to 3) come first, then the P1 features in this order: Sarvam voice, SSE trace, multilingual, metrics, Paytm staging and webhook, replay mode, follow-up worker. Do not skip Phase 5 testing or the Codex audit. An honest, smaller demo that passes its own acceptance checklist beats a broad one that does not (PRD Appendix C). If you drop a feature, label it "future" in the deck and the UI rather than faking it.
