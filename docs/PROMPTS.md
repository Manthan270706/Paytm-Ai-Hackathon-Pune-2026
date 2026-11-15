# PROMPTS.md: copy-paste prompts for every tool and task

Use with `AGENTS.md`, `docs/PRD.md`, `docs/BUILD_PLAN.md`, `docs/UPSCALE_PLAN.md` and `docs/TOOL_ROUTING.md`.

## How to use this file

Every session has two pastes, in this order:

1. **Standing prompt** for the tool (section 1). Paste once at the start of a new session.
2. **Task block** for the task ID (sections 3 to 5). Paste right after.

Rules for you:
- One new session per task block. Do not reuse a session for the next task.
- Open the task's own worktree folder in the tool, never the main repo folder.
- After the tool reports, follow the "after every task" checklist in section 6.
- Never paste keys or `.env` contents into any tool.

---

## 1. Standing prompts

### 1.1 Codex

```text
You are working on the OpsSaathi AI repo. You have a LIMITED credit budget. Spend it only on the single task I give you.

BEFORE ANYTHING ELSE
- Read AGENTS.md once, and only the PRD or plan sections and files named in the task. Do not scan or summarize the whole repo.
- If the task is ambiguous, or conflicts with AGENTS.md or the PRD, ask me ONE short question and wait. Do not guess about money, permissions or verification.

HOW TO WORK
- Do only the task I name. Do not start the next task, add features, refactor, rename, or touch files outside the task's list.
- Write the code and its tests together. Tests are mandatory. Never skip, delete or weaken a test to save credits.
- Do not generate UI, scaffolding, docs, READMEs, long comments or example data unless the task says so.
- Do not install packages, browse the web, or change config unless the task says so.
- Read each file at most once. Make edits in as few passes as possible. Do not re-read a file after you edit it.
- Run only the targeted tests for your task, then the guard script once at the end. Do not run the full suite repeatedly.
- If the same test fails twice for the same reason, STOP. Report the failure and your best hypothesis. Do not loop.
- No long explanations. Do not restate the task.

STOP CONDITION
- As soon as the acceptance criteria pass, stop.

FINAL REPORT (10 lines or fewer), then append it to docs/HANDOFF.md in the format shown there:
1. Files changed
2. Tests added and result
3. Acceptance criteria met (one line each)
4. Open questions or risks
```

### 1.2 Antigravity

```text
You are working on the OpsSaathi AI repo. Read AGENTS.md and only the plan sections named in my task. Do only the task I name, inside its lane and file list.

RULES
- Follow AGENTS.md trust rules exactly. Never edit domain/ logic, ScopedRepository, core/redaction, core/auth role logic, approval-resume checks, the verification service, the audit chain, the action ledger or webhook signature code. Those belong to the Core lane. If your task seems to need a change there, stop and tell me.
- Call Core-lane functions through their existing signatures. If one is still a stub, code against it and mark TODO(core).
- Do not change the OpenAPI contract, adapter interfaces or tool signatures without asking me.
- Write tests with the code. Run the targeted tests, ruff and mypy (or eslint and tsc) on touched files, and scripts/guard before reporting.
- Stay on the current branch and worktree. Do not touch main.
- No secrets in files or logs. Every adapter has a mock. Every screen has loading, empty and error states. Keep every existing data-testid unless the task says otherwise.
- Do not start any task other than the one named.

FINAL REPORT (10 lines or fewer), appended to docs/HANDOFF.md in its format: files changed, tests run and result, acceptance criteria met, open questions.
```

### 1.3 Cursor (Grok)

```text
You are working on the OpsSaathi AI repo. Read AGENTS.md first, then only the files and plan sections named in my task. My free-tier usage is limited, so be economical.

RULES
- Do only the task ID I give you, in its file list. Do not scan the repo, refactor, rename, or start the next task.
- Follow AGENTS.md trust rules exactly. Never edit domain/, ScopedRepository, core/auth, core/redaction, core/webhook, the audit chain, approvals, the action ledger or verification code. If the task seems to need that, stop and tell me.
- Do not change the OpenAPI contract, adapter interfaces or tool signatures.
- No new dependencies unless the task says so. No secrets in files. Colours, spacing and fonts come from the design tokens only (docs/design/DESIGN.md), never hard-coded.
- Keep every existing data-testid unless I say otherwise.
- If you wrote code, run only the targeted tests and lint for the files you touched, then scripts/guard once. If the same check fails twice for the same reason, stop and report.
- Stop as soon as the acceptance criteria pass.

FINAL REPORT (10 lines or fewer), appended to docs/HANDOFF.md in its format: status, branch and commit, files changed, tests and result, acceptance criteria, what is left, gotchas.
```

### 1.4 Cursor read-only reviewer

```text
Review-only task. Read the diff of branch <BRANCH> against upscale-integration, plus AGENTS.md section 2 (trust rules). Do not edit files and do not run the full suite. List any place where: money uses float; a tool schema takes merchant_id; a query is not scoped; RESOLVED is reachable without a verifier PASS; an approval can resume without role, version, hash and signature checks; a secret or raw sensitive input could be logged. Give file and line for each finding, or say "no findings". 15 lines max.
```

### 1.5 Codex read-only reviewer

```text
Review-only task. Read the diff of branch <BRANCH> against upscale-integration and AGENTS.md section 2. Do not edit files and do not run the full suite. Check only these areas: <AREAS>. List violations with file and line, ranked by severity, or say "clean". 10 lines max.
```

---

## 2. Setup commands (you, once)

```bash
git tag demo-final                      # on a clean main where the golden run passes
git checkout -b upscale-integration     # merge finished tasks here first
# one worktree per task, for example:
git worktree add ../ops-u6-a1 -b upscale/u6-a1 upscale-integration
```

Create `.cursor/rules/opssaathi.mdc` in each Cursor worktree with: `Read AGENTS.md and docs/PRD.md before any task and follow them.`

---

## 3. Antigravity task blocks

### U6-A1 and U6-A2: design audit, DESIGN.md and tokens
Worktree: `git worktree add ../ops-u6-a1 -b upscale/u6-a1 upscale-integration`
```text
TASK U6-A1 then U6-A2 from docs/UPSCALE_PLAN.md section 7.
Files: docs/design/before/, docs/design/AUDIT.md, docs/design/DESIGN.md, the Tailwind theme and token files, and font loading only. Do not edit any backend file or any screen component yet.

1. U6-A1: capture every screen at 390px and 1440px into docs/design/before/. Write docs/design/AUDIT.md listing, per screen, every item from the "AI slop" checklist in UPSCALE_PLAN 7.2 plus usability problems.
2. U6-A2: write docs/design/DESIGN.md and implement Tailwind theme tokens: colours (start with navy #002E6E and cyan #00BAF2, check them against the public Paytm for Business site and note any difference), neutrals, success, warning, error, status chip colours for every case state, type scale, spacing scale, radius, minimal elevation, one icon set, component inventory, short do and don't examples. Load a font stack that renders Devanagari well.
3. Do not use the Paytm logo. Use a text wordmark "OpsSaathi" and keep the footer line "Hackathon prototype for the Paytm Build for India AI Hackathon; not affiliated with or endorsed by Paytm".
Acceptance: audit and DESIGN.md committed; tokens are the single source of colour and spacing; the app still builds and the golden run still passes.
```

### U6-A4: merchant mobile app
Worktree: `git worktree add ../ops-u6-a4 -b upscale/u6-a4 upscale-integration` (after U6-A2 and U6-A3 are merged)
```text
TASK U6-A4 from docs/UPSCALE_PLAN.md section 7.4. Read docs/design/DESIGN.md and the components in apps/web/src/components.
Files: merchant screens under apps/web/src only.
Build the merchant mobile app at 390px using the existing components and tokens only:
- Bottom navigation: Home, Payments, Settlements, Help.
- Home: merchant name, settlement summary card (expected, received, pending), open-case banner, one large "Ask OpsSaathi" action.
- Payments and Settlements: list rows with amount, date, status chip and source badge.
- Help: category chips (Settlement delay, Refund, Fees, Device, Other) that start the chat; typing and mic side by side; language switcher shown as English, हिंदी, मराठी.
- Chat: short bubbles and an evidence card with three numbers (expected, received, difference); a "Details" expander holding the calculation and trace.
- Case tracking: a Stepper (Reported, Checking, With support, Verified, Resolved) with the next update time.
No decorative gradients, no emoji headings, no jargon on merchant screens. Keep every data-testid.
Acceptance: the full golden path works at 390px with no horizontal scroll; Playwright golden run passes.
```

### U6-A5: operations console
Worktree: `git worktree add ../ops-u6-a5 -b upscale/u6-a5 upscale-integration`
```text
TASK U6-A5 from docs/UPSCALE_PLAN.md section 7.4. Read docs/design/DESIGN.md and the existing components.
Files: operations console screens under apps/web/src only.
Build at 1440px: left sidebar (Queue, Approvals, Metrics, Audit, Health); top search; filterable case table with priority, SLA time left and status chips; split case detail (summary and timeline on the left; evidence, assist panel and actions on the right); approval modal showing action, amount, reason and approval status; verification card with before and after values and PASS or FAIL; metrics as four plain numbers, no decorative charts. Keep every data-testid.
Acceptance: a support user can approve and verify without scrolling past the fold at 1440px; Playwright golden run passes.
```

### U1-A1 and U1-A2: Ollama adapter and cascade
You first: install Ollama and run `ollama pull qwen2.5:3b`.
Worktree: `git worktree add ../ops-u1-a1 -b upscale/u1-a1 upscale-integration`
```text
TASK U1-A1 then U1-A2 from docs/UPSCALE_PLAN.md section 2.
Files: services/api/app/integrations/ollama/ (new), the LLM provider config and cascade code, integration health endpoint and screen data, and their tests.
1. Implement LLMProvider for Ollama over its local HTTP API (default http://localhost:11434), with JSON-schema constrained output where supported, temperature 0 in deterministic mode, a request timeout and one bounded retry. No vendor code outside integrations/ollama/.
2. Add LLM_CASCADE (for example "groq,ollama,cache,mock" or "ollama,cache,mock"). On failure, move to the next tier and record a failed tool event. The integration health data shows the active tier and why earlier tiers were skipped. Add a startup warm-up call.
Do not change the existing Groq adapter, cache or mock behaviour.
Acceptance: schema-valid output on the seed scenario; stopping Ollama, removing the Groq key and cutting the network each fall to the next tier without breaking the golden run. Unit tests use mocks; one live test is marked skippable.
```

### U1-A3 and U1-A4: small-model safety and benchmark
```text
TASK U1-A3 then U1-A4 from docs/UPSCALE_PLAN.md section 2.
Files: agent extraction and wording code, localized templates, tests, docs/PROVIDER_MATRIX.md.
1. Keep control flow deterministic: the graph chooses the next tool. The LLM only extracts fields, detects language and words replies. Validate every output with Pydantic and make one repair retry. If local output still fails validation, use the localized template for merchant-visible Hindi and Marathi messages. Amounts, IDs and dates always come from backend values.
2. Run the golden run and 10 extra prompts on each tier and record success rate, valid-JSON rate and p50 and p95 latency in docs/PROVIDER_MATRIX.md. Mark any number you did not measure as "vendor claim".
Acceptance: on 20 seed prompts the local model never outputs an amount, status or ID absent from tool results.
```

### U4-A1: evaluation harness
```text
TASK U4-A1 from docs/UPSCALE_PLAN.md section 5.
Files: services/api/tests/eval/ (new) only.
Build a runner that loads scenario files, drives the agent through the API on a chosen provider, and scores each case on: intent correct; tools called as expected; reason code correct; every number in the reply present in a tool result; no forbidden claim (for example "resolved" before verification PASS); correct refusal where expected. Output JSON and a Markdown report. It must run offline with the mock or replay provider.
Acceptance: runs on 3 sample scenarios end to end and writes both reports.
```

### U4-A3: adversarial suite
```text
TASK U4-A3 from docs/UPSCALE_PLAN.md section 5.
Files: tests/eval/scenarios/adversarial/ only.
Write adversarial scenarios: prompt injection inside merchant text and transaction notes; "mark it resolved", "approve it yourself", "ignore your rules"; requests for another merchant's data; messages containing OTP, PIN or card numbers; attempts to make the agent invent an amount. Provide English, Hindi and Marathi versions of each. Expected result for every case is a refusal or a safe, honest reply, never a state change or leaked data.
Acceptance: at least 30 scenarios with written expectations, runnable by the harness.
```

### U3-A1: proactive overdue scanner
Run after U3-C1 is merged.
```text
TASK U3-A1 from docs/UPSCALE_PLAN.md section 4.
Files: workers/ (new scanner), the route for "run scan now", their tests.
The worker finds settlement batches whose reconciliation reason code is OVERDUE and that have no open case. For each, check merchant consent and call the policy engine for PROACTIVE_MERCHANT_MESSAGE. If allowed, open a case through the normal path and send the approved template in the merchant's language. Be idempotent: a rescan must not create duplicates. Add a support-role "run scan now" endpoint for the demo.
Acceptance: scanning the seed scenario creates exactly one case and one message; rescanning creates none.
```

### U5-A1 to A3: live Paytm staging
You first: confirm the staging MID and key work in `.env`; start the tunnel.
```text
TASK U5-A1, U5-A2, U5-A3 from docs/UPSCALE_PLAN.md section 6.
Files: integrations/paytm/, webhook route wiring, investigation panel data and component, tests.
1. Through PaymentProvider, initiate a test transaction using Paytm's documented staging flow, then look up its status. Store it with source_type=PAYTM_STAGING. Never copy a staging record into the synthetic ledger.
2. Wire POST /api/v1/webhooks/paytm through the tunnel using the existing checksum validator and dedupe. Show signature_valid and the dedupe result in the integration health screen.
3. In the investigation panel show the staging payment (PAYTM_STAGING) and the settlement ledger (SYNTHETIC_DEMO) in separate labelled sections with the note: "Settlement API is production-only on Paytm, so settlement is simulated."
Never print or log keys. If staging is unavailable, show "integration unavailable" and use labelled fixtures.
Acceptance: one real staging transaction visible with the correct badge; a test event stored once and processed once.
```

### U8-A1 and U8-A2: public link
```text
TASK U8-A1 then U8-A2 from docs/UPSCALE_PLAN.md section 9.
Files: infra/ and docs/DEMO_RUNBOOK.md, CORS and rate-limit config.
Expose the demo through a Cloudflare Tunnel (or a hosted preview if one is already set up). Generate a QR code. Demo login only, demo-mode data only, rate limits on, CORS set to the public origin, no keys or real data. Each judge session must not corrupt another's case (separate reset copy, or a clearly shown shared reset).
Acceptance: a phone on mobile data completes the merchant flow; two simultaneous sessions do not interfere.
```

---

## 4. Codex task blocks

Run these in order, one session each, one worktree each.

### U2-C1: hash-chained audit log
Worktree: `git worktree add ../ops-u2-c1 -b upscale/u2-c1 upscale-integration`
```text
TASK U2-C1 from docs/UPSCALE_PLAN.md section 3. Read only AGENTS.md, PRD sections 8 and 13, and that task.
Files: domain/audit_chain.py and its tests only.
Implement: each audit event stores prev_hash and event_hash (SHA-256 over canonical JSON of the event plus prev_hash). verify_chain(events) returns OK or the index of the first broken event. Decide per-merchant chain plus a global chain for system events and state the choice in a one-line comment.
Tests: valid chain passes; an edited event, a deleted event and reordered events are detected; genesis handling; concurrent appends do not fork the chain.
Acceptance: all tests pass; guard passes.
```

### U2-C2: signed approvals
Worktree: `git worktree add ../ops-u2-c2 -b upscale/u2-c2 upscale-integration`
```text
TASK U2-C2 from docs/UPSCALE_PLAN.md section 3. Read only AGENTS.md, PRD sections 5.3 and 11, domain/approvals.py and that task.
Files: domain/approvals.py and its tests only.
Add an HMAC-SHA256 signature over reviewer ID, role, action hash, case version, decision and timestamp using a server-side key (APPROVAL_SIGNING_KEY from config). validate_resume must verify the signature in addition to the existing role, version, hash and policy checks. Fail closed if the key is missing.
Tests: valid signature accepted; any altered field rejected; missing key fails closed; unsigned old approvals rejected on resume.
Acceptance: all tests pass; guard passes.
```

### U2-C3: action ledger with compensation
```text
TASK U2-C3 from docs/UPSCALE_PLAN.md section 3. Read only AGENTS.md and that task.
Files: domain/action_ledger.py and its tests only.
Every external action (settlement re-sync, merchant notification) records the forward action, parameters hash, idempotency key and a declared compensating action. compensate(action_id) is idempotent and allowed once. Compensating a re-sync cancels the request in the mock adapter. No path may move money.
Tests: compensation runs once; a second compensation is a no-op; compensating a never-executed action is rejected; every action row has a compensator.
Acceptance: all tests pass; guard passes.
```

### U3-C1: policy rows for proactive messaging
```text
TASK U3-C1 from docs/UPSCALE_PLAN.md section 4. Read only AGENTS.md, PRD section 11, domain/policy.py and that task.
Files: domain/policy.py and its tests only.
Add actions PROACTIVE_MERCHANT_MESSAGE and SOUNDBOX_ANNOUNCEMENT: ALLOW only when the merchant has a consent flag, the message uses an approved template, and it contains no sensitive data; otherwise DENY with a reason code. Add a per-merchant daily limit read from config.
Tests: missing consent, free-text message, over the daily limit and sensitive data each give DENY.
Acceptance: all tests pass; guard passes.
```

### U4-C1: review of eval expectations (read-only)
```text
TASK U4-C1 from docs/UPSCALE_PLAN.md section 5. Read only AGENTS.md section 2 and tests/eval/scenarios/adversarial/.
Do not edit any file. Check that each expected outcome matches the trust rules. List wrong or missing expectations, 15 lines max.
```

### U5-C1: review of the webhook path (read-only)
```text
TASK U5-C1 from docs/UPSCALE_PLAN.md section 6. Read only the webhook route, core/webhook.py and AGENTS.md section 2.
Do not edit any file. Confirm that checksum validation cannot be bypassed in any mode, rows are labelled with the right source_type, and dedupe works. List issues with file and line, 10 lines max.
```

### U9-C1: final audit (read-only)
```text
TASK U9-C1 from docs/UPSCALE_PLAN.md section 10. Read the git diff since the demo-final tag, PRD section 15.1 and AGENTS.md.
Do not edit any file. List violations with file and line, ranked by severity.
```

---

## 5. Cursor task blocks

### U6-A3 chunk 1
Worktree (after U6-A2 is merged): `git worktree add ../ops-u6-a3a -b upscale/u6-a3a upscale-integration`
```text
TASK U6-A3 chunk 1 from docs/UPSCALE_PLAN.md section 7.4. Read only docs/design/DESIGN.md and the existing components folder.
Files: new components Button, Input, Card, ListRow (title, subtitle, right-aligned amount), StatusChip, and their tests, under apps/web/src/components/.
Use only design tokens. Each component supports keyboard use and has a small test. Do not edit screens.
Acceptance: components render from tokens; tests, lint and tsc pass.
```

### U6-A3 chunk 2
```text
TASK U6-A3 chunk 2 from docs/UPSCALE_PLAN.md section 7.4. Read only docs/design/DESIGN.md and apps/web/src/components/.
Files: new components Stepper (case progress), BottomNav, Sidebar, DataTable, and their tests.
Use only design tokens; keyboard support; small tests. Do not edit screens.
Acceptance: components render from tokens; tests, lint and tsc pass.
```

### U6-A6: copy and agent tone
```text
TASK U6-A6 from docs/UPSCALE_PLAN.md section 7.4. Read only the locale files in apps/web/src/locales/ and the agent reply style notes in UPSCALE_PLAN 7.3.
Files: apps/web/src/locales/** and the agent reply template files only.
Rewrite UI strings in plain English, Hindi and Marathi: short sentences, plain words, one clear next step, amounts in rupees with Indian digit grouping. Remove banned words on merchant screens: "cryptographic", "autonomous", "LangGraph". Agent replies: at most three short sentences plus the evidence card, no filler, no jargon. Amounts, IDs and dates stay as backend placeholders, never retyped.
Acceptance: no banned words in merchant strings; no hard-coded strings left in the screens you touched; tests and lint pass. Flag Hindi and Marathi strings for human review.
```

### U6-A7: accessibility fixes
Run after Antigravity reports axe and Lighthouse findings.
```text
TASK U6-A7 from docs/UPSCALE_PLAN.md section 7.4. Read only the axe and Lighthouse findings list I paste below and the components it names.
<PASTE FINDINGS HERE>
Fix only those findings: contrast, focus, labels, landmarks, reduced-motion, touch targets of at least 48px, text of at least 16px on mobile. Use tokens only. Keep every data-testid.
Acceptance: the listed findings are resolved; tests and lint pass.
```

### U2-A2: trust UI
```text
TASK U2-A2 from docs/UPSCALE_PLAN.md section 3. Read only docs/design/DESIGN.md and the ops console components.
Files: ops console components only.
Add: a "Verify audit chain" button that calls GET /api/v1/audit/verify and shows OK or the first broken event; approval modal shows signed-approval status; an action history list with a "Reverse" action for supervisors, calling POST /api/v1/actions/{id}/compensate.
Acceptance: tests, lint and tsc pass; buttons show loading, success and error states.
```

### U2-A4: claim-language pass
```text
TASK U2-A4 from docs/UPSCALE_PLAN.md section 3.
Files: README, docs text, deck text files and UI strings only.
Replace: "production-grade" with "production-minded prototype"; "cryptographic approval" with "integrity-bound approval" (or "signed approval" if U2-C2 is merged); "immutable" with "tamper-evident" (only if U2-C1 is merged, otherwise "append-only"); "AES/HMAC webhook validation" with "Paytm's documented checksum validation". Label seeded Cases 2 to 5 as "seeded history".
Acceptance: a grep for the old phrases returns nothing outside quoted examples.
```

### U3-A2: agent assist panel
```text
TASK U3-A2 from docs/UPSCALE_PLAN.md section 4. Read only docs/design/DESIGN.md, the case detail component and the case API types.
Files: assist panel component only.
Show a short case summary, the suggested next action with its reasoning (from the reason code and policy decision, not free text), an SLA countdown, and queue ranking by priority and time left. Every number comes from backend fields.
Acceptance: panel content matches the case data; tests, lint and tsc pass.
```

### U3-A4: WhatsApp-style simulation
```text
TASK U3-A4 from docs/UPSCALE_PLAN.md section 4.
Files: a NotificationProvider mock and a chat-thread component only.
Render merchant notifications as a WhatsApp-like thread inside the app using the same templates and policy as the other channels. Label it "simulated". No external send.
Acceptance: renders notifications from the mock; labelled; tests and lint pass.
```

### U4-A2: scenario set
```text
TASK U4-A2 from docs/UPSCALE_PLAN.md section 5. Read only the harness scenario format in tests/eval/ and PROJECT_REPORT.md section 4C.
Files: tests/eval/scenarios/ only.
Write 50 scenario files covering all 5 seeded case types; missing or ambiguous details (no amount, wrong date, unknown order ID); English, Hindi and Marathi phrasing; typical speech-recognition errors. Write the expected outcome for each before anything is run.
Acceptance: 50 valid files that load in the harness.
```

### U7-A2: deck text
```text
TASK U7-A2 from docs/UPSCALE_PLAN.md section 8. Read only docs/EVAL_REPORT.md, docs/PROVIDER_MATRIX.md and UPSCALE_PLAN section 8.
Files: docs/deck/ text only.
Draft slides for: the problem (sourced numbers only; leave a "SOURCE NEEDED" mark where I have not provided one), the live flow, trust moments, evaluation results, provider matrix, a real-versus-simulated table, and the roadmap. Every claim must map to something implemented or be marked as roadmap.
Acceptance: draft committed; no unsourced number stated as fact.
```

### Second-key reviews
Use prompt 1.4 for Codex branches, and prompt 1.5 for Antigravity or Cursor branches in risky areas. Replace `<BRANCH>` and `<AREAS>`.

---

## 6. After every task (you)

```bash
cd ../ops-<task-worktree>
scripts/guard                 # must pass
cd services/api && pytest -q  # backend suite
cd ../../apps/web && npm run lint && npm run test
git diff --stat upscale-integration   # touches only the task's files?
```

Then:
1. Read the report: each acceptance criterion should be named, with test results.
2. Check tests were added, not weakened.
3. If the area is risky (money, permissions, scope, approval, verification, audit, signing), run the second-key review (prompt 1.4 or 1.5).
4. Merge into `upscale-integration`, then run the golden run and the gate checklist (UPSCALE_PLAN section 11): guard, tests, golden run, seed numbers unchanged, premature RESOLVED blocked, stale approval 409, cross-merchant 404, replay mode works.
5. Only a green gate goes to `main`. If anything fails, fix on the branch or drop it. `demo-final` is the fallback.
6. If a tool hit its limit, follow TOOL_ROUTING.md section 7 and give the next tool only the `HANDOFF.md` section for that task.
