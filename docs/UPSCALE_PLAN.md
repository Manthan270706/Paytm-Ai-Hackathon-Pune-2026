# UPSCALE_PLAN.md: OpsSaathi AI (post-build upgrades)

Continues `docs/BUILD_PLAN.md`. Read with `AGENTS.md` and `docs/PRD.md`. The same rules, task format, owners and prompts apply (BUILD_PLAN sections 0 to 3). Task IDs here start with `U`, for example `U2-C1` (Phase U2, Codex task 1) or `U6-A4` (Phase U6, Antigravity task 4).

Written Sun 15 Nov 2026, 12:40 IST, from `PROJECT_REPORT.md`.

---

## 0. Safety first: protect the working demo

Everything here is optional upside. The existing demo already passes its acceptance checklist, and nothing below may put it at risk.

1. **Tag the safe build now.** `[HUMAN]` On a clean `main` where the golden run passes: `git tag demo-final`. Keep a second copy of the repo folder and a screen recording of the golden run.
2. **Branch rule.** Every task works on `upscale/<task-id>` in its own worktree. Nothing merges to `main` unless its gate (section 11) is green.
3. **Demo-freeze time.** `[HUMAN]` Check your judging slot. Set the freeze at least 2 hours before it. After the freeze, no merges. If anything on `main` is unstable at the freeze, demo from `demo-final`.
4. **Seed scenario is frozen.** ₹15,000 expected, ₹9,000 observed, ₹6,000 discrepancy, ₹5,000 threshold. No task may change it.
5. **All trust rules in `AGENTS.md` still apply.** In particular: no float money, no `merchant_id` in tool schemas, `RESOLVED` only through the read-only verifier, no secrets in files or logs.
6. **Two-key rule.** Codex owns hash chaining, signatures, compensation logic and policy additions. Antigravity owns everything else. Codex reviews Antigravity's changes in risky areas, as before.

---

## 1. Priority order

Ordered by what judges see and how much it protects the trust story. Do top to bottom; skip down only if blocked.

| Rank | Phase | Why it matters | Main owner |
| 1 | U6 Frontend redesign | First impression; Paytm-like and clean beats a busy "AI look" | Antigravity + Cursor |
| 2 | U4 Evaluation and adversarial suite | Proves it works beyond one scripted path | Antigravity + Cursor (+ small Codex review) |
| 3 | U1 Ollama local LLM | Offline reliability; data never leaves the machine | Antigravity |
| 4 | U2 Trust claims made true | Backs the words "immutable" and "signed" with code | Codex (+ Cursor UI & review) |
| 5 | U3 Teammate features | Track 3: acts first, helps staff, speaks where merchants listen | Antigravity + Cursor |
| 6 | U5 Live Paytm staging | Real payments plus simulated settlement is a stronger, honest story | Antigravity |
| 7 | U7 Business case and deck | Track 3 asks for measurable outcomes | Cursor + Antigravity + human |
| 8 | U8 Public link and QR | Judges try it themselves | Antigravity |
| 9 | U9 Final audit and rehearsal | Last safety net | Codex + human |

Codex credit order if credits run short: U9-C1 (audit), then U2-C1, U2-C2, then U3-C1, U4-C1, U5-C1, then U2-C3. Use the credit-discipline prompt in BUILD_PLAN section 2.1 for every Codex session.

---

## 2. Phase U1: Ollama local LLM (remaining item)

Goal: the agent works fully offline with a local model, and the provider cascade is configurable and observable. The report lists the cascade as Ollama, then Groq, then replay cache, then mock.

**Recommendation on order.** Make the order configurable with `LLM_CASCADE`. Use `groq,ollama,cache,mock` when online (faster, stronger on Hindi and Marathi) and `ollama,cache,mock` in "offline mode". A 3B local model is weaker at structured output and Indic languages than a cloud model, so test before choosing a default.

**U1-H1 `[HUMAN]` Machine check**
1. Install Ollama; pull `qwen2.5:3b` (already used in the report). If the machine has enough RAM or a GPU, also try a larger model and compare latency.
2. Note the hardware and the time to first token for each model.
- Acceptance: `ollama run <model>` responds; numbers written in `docs/PROVIDER_MATRIX.md`.

**U1-A1 `[AGY]` Ollama adapter**
- Read: PRD §12.1, §12.2; `integrations/` provider interfaces; existing Groq adapter.
- Steps: implement `LLMProvider` for Ollama over its local HTTP API (default `http://localhost:11434`); structured output through JSON-schema constrained responses where supported; temperature 0 in deterministic mode; request timeout and one bounded retry; no vendor code outside `integrations/ollama/`.
- Acceptance: schema-valid output for intent extraction and reply generation on the seed scenario; mock-based unit tests plus one live test marked skippable.

**U1-A2 `[AGY]` Cascade configuration and health**
- Steps: `LLM_CASCADE` env var parsed into an ordered list; each failure moves to the next tier and is recorded as a failed tool event; integration health screen shows the active tier and why earlier tiers were skipped; startup warm-up call so the first demo request is not slow.
- Acceptance: stopping Ollama, removing the Groq key, and cutting the network each fall to the next tier without breaking the golden run.

**U1-A3 `[AGY]` Make the small model safe**
- Steps: keep the control flow deterministic (the graph decides which tool runs next); use the LLM only for field extraction, language detection and wording; validate every output with Pydantic and make one repair retry; for merchant-visible Hindi and Marathi status messages, use the localized templates when the local model's output fails validation; amounts, IDs and dates always come from backend values.
- Acceptance: on 20 seed prompts, the local model never produces an amount, status or ID that is absent from tool results (checked by the eval harness once U4 exists; until then by a manual list).

**U1-A4 `[AGY]` Provider benchmark**
- Steps: run the golden run and 10 extra prompts on each tier; record success rate, valid-JSON rate, p50 and p95 latency, and cost where relevant; write `docs/PROVIDER_MATRIX.md` and a slide-ready table (Cursor formats final table text).
- Acceptance: table committed; the report's claims (for example "~1,000 tok/sec") are replaced by your measured numbers or marked as vendor claims.

---

## 3. Phase U2: Make the trust claims literally true

**U2-C1 `[CODEX]` Hash-chained audit log**
- Read: PRD §8 (`audit_events`, `case_events`), §13; `AGENTS.md`.
- Files: `domain/audit_chain.py`, tests; a migration only if the plan says so (Antigravity adds the columns in U2-A1).
- Steps: each audit event stores `prev_hash` and `event_hash` (SHA-256 over canonical JSON of the event plus `prev_hash`); a pure function `verify_chain(events)` returns OK or the first broken index; chain is per merchant plus a global chain for system events (state the choice in the code comment).
- Tests: valid chain passes; edited event, deleted event and reordered events are detected; genesis handling; concurrent appends do not fork the chain (use a lock or a serialized append).
- Acceptance: tests pass; guard passes.

**U2-C2 `[CODEX]` Signed approvals** (after U2-C1)
- Files: `domain/approvals.py` (extend), tests.
- Steps: the approval record carries an HMAC-SHA256 signature over reviewer ID, role, action hash, case version, decision and timestamp, using a server-side key (`APPROVAL_SIGNING_KEY`); `validate_resume` verifies the signature and the existing role, version, hash and policy checks; key rotation noted in a comment, not built.
- Tests: valid signature accepted; any altered field rejected; missing key fails closed; old unsigned approvals are rejected on resume.
- Acceptance: pass. Describe this in the deck as "integrity-bound approvals", not as public-key signatures.

**U2-C3 `[CODEX]` Action ledger with compensation**
- Files: `domain/action_ledger.py`, tests.
- Steps: every external action (re-sync, merchant notification) records forward action, parameters hash, idempotency key and a declared compensating action; `compensate(action_id)` is idempotent and only allowed once; compensation of a re-sync cancels the request in the mock adapter; no money-moving path exists.
- Tests: compensation runs once; double compensation is a no-op; compensating a never-executed action is rejected; every action row has a compensator.
- Acceptance: pass.

**U2-A1 `[AGY]` Schema and endpoints**
- Steps: migration for `prev_hash`, `event_hash`, `signature`, and an `action_ledger` table; append through the Codex functions; `GET /api/v1/audit/verify` (support role) returns chain status; `POST /api/v1/actions/{id}/compensate` (supervisor role, audited, demo-mode only for the mock adapter).
- Acceptance: API tests; chain verification works over the seeded history.

**U2-A2 `[CURSOR]` Visible trust UI**
- Steps: "Verify audit chain" button in the ops console showing OK or the first broken event; approval modal shows the signed-approval status; action history list with a "Reverse" action for supervisors.
- Acceptance: tamper with one row in the demo database and the button turns red (include this as a rehearsed demo step).

**U2-A3 `[AGY]` Postgres verifier role in the demo**
- Steps: confirm the demo can run on Postgres with the real read-only `opssaathi_verifier` role (SQLite `PRAGMA query_only` is a weaker connection flag); add a test that the role cannot INSERT, UPDATE or DELETE; keep SQLite as the offline fallback and say so in the docs.
- Acceptance: test passes on Postgres.

**U2-A4 `[CURSOR]` Claim language pass**
- Steps: in the report, README, deck and UI copy, replace: "production-grade" with "production-minded prototype"; "cryptographic approval" with "integrity-bound approval" (or "signed approval" once U2-C2 ships); "immutable" with "tamper-evident" (once U2-C1 ships); "AES/HMAC webhook validation" with "Paytm's documented checksum validation"; label seeded Cases 2 to 5 as "seeded history".
- Acceptance: grep for the old phrases returns nothing.

**U2-R1 `[CURSOR]` Review of Codex U2 diffs (read-only)**
- Steps: read-only second-key review of `upscale/u2-c1`, `u2-c2`, and `u2-c3` against `AGENTS.md` using the review prompt in `TOOL_ROUTING.md` §10.
- Acceptance: review note appended in `docs/HANDOFF.md`.

---

## 4. Phase U3: A more proactive teammate

**U3-C1 `[CODEX]` Policy rows for proactive messaging**
- Files: `domain/policy.py` (extend), tests.
- Steps: add actions `PROACTIVE_MERCHANT_MESSAGE` and `SOUNDBOX_ANNOUNCEMENT`: ALLOW only when the merchant has a consent flag, the message uses an approved template, and it contains no sensitive data; otherwise DENY with a reason code; rate limit per merchant per day, read from config.
- Tests: consent missing, free-text message, over the daily limit and sensitive data all give DENY.
- Acceptance: pass.

**U3-A1 `[AGY]` Proactive overdue scanner**
- Steps: worker scans settlement batches whose reconciliation reason code is `OVERDUE` and with no open case; checks consent and policy; opens a case through the normal path; sends a templated message in the merchant's language ("Your ₹6,000 settlement is overdue; case CASE-... is open"); idempotent so a rescan never duplicates; a "run scan now" button for the demo.
- Acceptance: running the scan on the seed scenario creates exactly one case and one message; rerunning creates none.

**U3-A2 `[CURSOR]` Agent assist for support staff**
- Steps: a case panel with a short summary, the suggested next action with its reasoning (from reason code and policy decision, not free text from the LLM), an SLA countdown, and queue ranking by priority and time left; every number comes from backend fields.
- Acceptance: panel content matches the case data; no amount appears that is not in the record.

**U3-A3 `[AGY]` Simulated Soundbox announcement**
- Steps: a labelled "Soundbox (simulated)" component that plays the case status as a short spoken line using the voice adapter, gated by `SOUNDBOX_ANNOUNCEMENT` policy; badge shows SIMULATED.
- Acceptance: announces status changes for the demo merchant; never implies a physical device is connected.

**U3-A4 `[CURSOR]` WhatsApp-style channel (optional, labelled simulation)**
- Steps: a `NotificationProvider` adapter with a mock that renders messages in a WhatsApp-like thread inside the app; same templates and policy as above.
- Acceptance: labelled "simulated"; no external send.

---

## 5. Phase U4: Evaluation and adversarial testing

**U4-A1 `[AGY]` Evaluation harness**
- Steps: a runner (`services/api/tests/eval/`) that loads scenario files, drives the agent through the API on a chosen provider, and scores each case on: intent correct, tools called as expected, reason code correct, every number in the reply present in a tool result, no forbidden claim (for example "resolved" before PASS), correct refusal where expected; outputs a JSON and a Markdown report.
- Acceptance: runs offline with the mock or replay provider.

**U4-A2 `[CURSOR]` Scenario set (50 to 60)**
- Steps: cover all 5 seeded case types; missing and ambiguous details (no amount, wrong date, unknown order ID); English, Hindi and Marathi phrasing; chat and voice transcripts with typical speech errors; each with an expected outcome written down before running. Writing scenario JSON/YAML files is cheap, text-based, and fits Cursor request budgets.
- Acceptance: files committed; expectations reviewed by the human.

**U4-A3 `[AGY+CURSOR]` Adversarial suite**
- Steps: prompt injection inside merchant text and transaction notes; "mark it resolved", "approve it yourself", "ignore your rules"; requests for another merchant's data; messages containing OTP, PIN, card numbers; attempts to make the agent invent an amount; Antigravity writes the test runner harness and core rules; Cursor adds multilingual Hindi and Marathi variants of each prompt.
- Acceptance: expected result for each is a refusal or a safe, honest reply, never a state change or leaked data.

**U4-C1 `[CODEX]` Review of expectations (short, read-only)**
- Read: the adversarial and refusal expectations only.
- Steps: check that each expected outcome matches the trust rules in `AGENTS.md`; list wrong or missing expectations; edit nothing.
- Acceptance: a list of at most 15 lines.

**U4-A4 `[AGY]` Results and fixes**
- Steps: run the suite on each provider tier; fix failures in Antigravity-owned files; send failures in Core files to Codex; generate `docs/EVAL_REPORT.md` with pass rate per category and a slide-ready table; include failures honestly.
- Acceptance: report committed; any failing category has a written explanation or a fix.

**U4-H1 `[HUMAN]` Judge-driven rehearsal**
- Steps: a teammate acts as a judge and tries to break the demo with 15 free-form prompts; record what happens; fix or prepare an honest answer for each.

---

## 6. Phase U5: Live Paytm staging (only if credentials work)

Keep the labels honest: real staging payments plus a synthetic settlement ledger.

**U5-H1 `[HUMAN]`** Confirm the staging MID and key work with a test call; start the tunnel; never paste keys into chats or docs.

**U5-A1 `[AGY]` Create and read a staging payment**
- Steps: through `PaymentProvider`, initiate a test transaction using Paytm's documented staging flow, then look up its status through the status API; store it with `source_type=PAYTM_STAGING`; never copy a staging record into the synthetic ledger.
- Acceptance: one real staging transaction visible in the UI with the right badge.

**U5-A2 `[AGY]` Webhook live test**
- Steps: expose `POST /api/v1/webhooks/paytm` through the tunnel; trigger a staging event; show `signature_valid` and the dedupe result in the integration health screen.
- Acceptance: the event is stored once and processed once.

**U5-A3 `[AGY]` Side-by-side view**
- Steps: in the investigation panel show the staging payment (`PAYTM_STAGING`) and the settlement ledger (`SYNTHETIC_DEMO`) in separate labelled sections with a one-line note: "Settlement API is production-only on Paytm, so settlement is simulated."
- Acceptance: no screen mixes the two sources without labels.

**U5-C1 `[CODEX]` Review of the webhook path (read-only)**
- Steps: confirm checksum validation cannot be bypassed in any mode, rows are labelled correctly, and dedupe works; list issues with file and line.

---

## 7. Phase U6: Frontend redesign (Paytm-like, plain, less "AI look")

### 7.1 Design direction (what to match, what not to copy)

- **Palette.** Paytm's brand blues are published on brand-colour reference sites: a cyan around `#00BAF2` (some sources list `#00B9F1`) and a dark navy `#002E6E`. Use these as the accent and heading colours on a white and light-grey base. Sample against the live Paytm for Business site or app and confirm the final hex values before locking tokens.
- **Layout patterns to borrow.** The Paytm for Business app has a settlement summary with available balance, a payments list, a Settlements tab, and a support screen organised by categories. Mirror those patterns: home summary card, list rows with amount right-aligned, status chips, and "Help" organised by category chips. For the support console use a left sidebar, a top search bar, a filterable table and a split detail view, as in standard payments dashboards.
- **Do not use Paytm's logo or marks.** The Paytm logo is a registered trademark. Use an own OpsSaathi wordmark, and keep the footer line "Hackathon prototype for the Paytm Build for India AI Hackathon; not affiliated with or endorsed by Paytm" (PRD §2.2).
- **Language.** Paytm's help centre offers Hindi and Marathi, so the UI should look natural in those scripts. Use a font stack that renders Devanagari well (for example Noto Sans Devanagari with a clean Latin sans).

### 7.2 "AI slop" checklist (remove all of these)

- Purple or neon gradients, glassmorphism, glowing borders and animated blobs.
- Emoji as headings or bullets; icon-in-a-circle cards repeated everywhere.
- Hero text like "Your autonomous AI teammate" with no concrete action; jargon such as "cryptographic", "LangGraph", "autonomous" in merchant-facing screens.
- Decorative stats and charts with no real data behind them.
- Walls of text in chat replies; filler such as "I'd be happy to help!".
- Too many badges, tooltips, tabs and animations on one screen.
- Inconsistent spacing, radius, font sizes and colours between screens.

### 7.3 Principles

- One primary action per screen, in plain words ("Check my settlement", "Talk to us").
- Real data first: amounts, dates, status, next step. Technical evidence (trace, hashes) goes behind a clearly labelled "Details" expander for judges and staff.
- Merchant app is mobile-first at 390px; the ops console is desktop-first at 1440px.
- Plain-language copy, short sentences, vernacular first; amounts always in ₹ with Indian digit grouping.
- Accessible: text at least 16px on mobile, touch targets at least 48px, contrast at least WCAG AA, visible focus, reduced-motion respected.
- Calm motion only (state transitions, skeleton loading); nothing decorative.

### 7.4 Tasks

**U6-H1 `[HUMAN]` References**
- Collect screenshots of the Paytm for Business app and dashboard (public store listing, public pages) into `docs/design/refs/`. They are for studying layout only; do not copy assets.

**U6-A1 `[AGY]` Design audit of the current UI**
- Steps: capture every screen at 390px and 1440px into `docs/design/before/`; write `docs/design/AUDIT.md` listing every item from the slop checklist found, per screen, plus usability problems (too many steps, unclear labels, dead ends).
- Acceptance: audit committed.

**U6-A2 `[AGY]` DESIGN.md and tokens**
- Steps: write `docs/design/DESIGN.md` with: colour tokens (navy `#002E6E`, cyan `#00BAF2`, neutrals, success, warning, error, and status chip colours for each case state), type scale, spacing scale, radius, elevation (minimal), icon set (one set only), component inventory, and do/don't examples; implement as Tailwind theme tokens; load the Devanagari font.
- Acceptance: tokens are the only source of colour and spacing in code (no hard-coded hex values in components).

**U6-A3 Chunk 1 `[CURSOR]` Component primitives: Base Controls**
- Steps: Button, Input, Card, ListRow (title, subtitle, right-aligned amount), StatusChip. Each component uses only tokens from `docs/design/DESIGN.md`, includes keyboard support, and has a small component test.
- Acceptance: components render from tokens with 100% test coverage.

**U6-A3 Chunk 2 `[CURSOR]` Component primitives: Layout & Navigation**
- Steps: Stepper (case progress), BottomNav, Sidebar, DataTable. Implement in a second Cursor session.
- Acceptance: renders correctly at 390px and 1440px using design tokens.

**U6-A3 Chunk 3 `[AGY]` Component primitives: Overlays & Feedback**
- Steps: Modal, Toast, Skeleton, EmptyState, ErrorState, SourceBadge (restyled).
- Acceptance: components render from tokens; one demo/catalog page showcases all primitives.

**U6-A4 `[AGY]` Merchant mobile app**
- Steps:
  - Bottom navigation: Home, Payments, Settlements, Help.
  - Home: merchant name, settlement summary card (expected, received, pending), open-case banner, one big "Ask OpsSaathi" action.
  - Payments and Settlements: list rows with amount, date, status chip and source badge.
  - Help: category chips (Settlement delay, Refund, Fees, Device, Other) that start the chat; typing and mic side by side; language switcher in plain script names (English, हिंदी, मराठी).
  - Chat: short bubbles, an evidence card with three numbers (expected, received, difference), "Details" expander for the calculation and trace.
  - Case tracking: Stepper (Reported, Checking, With support, Verified, Resolved) with the next update time.
- Acceptance: the whole golden path works at 390px with one thumb; no horizontal scrolling.

**U6-A5 `[AGY]` Operations console**
- Steps: left sidebar (Queue, Approvals, Metrics, Audit, Health); top search; filterable case table with priority, SLA time left and status chips; split case detail (summary and timeline left, evidence, assist panel and actions right); approval modal showing action, amount, reason and signed status; verification card with before and after and PASS or FAIL; metrics as four plain numbers, not decorative charts.
- Acceptance: a support user can approve and verify without scrolling past the fold on a 1440px screen.

**U6-A6 `[CURSOR]` Copy and agent tone**
- Steps: rewrite UI strings in plain English, Hindi and Marathi; set the agent's reply style: at most three short sentences plus an evidence card, no filler, no jargon, one clear next step, amounts and IDs from backend values; keep strings in locale files (`apps/web/src/locales/`), not inline.
- Acceptance: a checklist review of every screen; no banned words ("cryptographic", "autonomous", "LangGraph") on merchant screens.

**U6-A7 `[CURSOR]` Accessibility and low bandwidth fixes**
- Steps: after Antigravity runs axe and Lighthouse, implement fixes for contrast, focus rings, ARIA labels and semantic landmarks; reduced-motion support; skeleton loading; low data mode.
- Acceptance: no critical axe issues; Lighthouse accessibility score > 90.

**U6-A8 `[AGY]` Visual QA and regression**
- Steps: Playwright screenshots at 390px and 1440px into `docs/design/after/`; keep every existing `data-testid` or update tests deliberately; the full Playwright golden run must pass; write a before and after contact sheet for the deck; Cursor fixes small visual bugs listed.
- Acceptance: E2E passes twice from a clean reset.

**U6-H2 `[HUMAN]` Review**
- Steps: compare before and after; have a Hindi or Marathi speaker read the translated strings; check the footer disclaimer and that no Paytm logo is used.

---

## 8. Phase U7: Business case and deck

**U7-H1 `[HUMAN]` Source the problem numbers**
- Find and cite real figures for merchant support volume and settlement-related contacts from public sources; if you cannot source a number, do not state it as fact.

**U7-A1 `[AGY]` Impact calculator**
- Steps: a small page or sheet where inputs are editable and every assumption is labelled: cases per month, minutes per manual case, share handled without a human, LLM and infra cost per case, repeat-contact reduction; outputs savings with the formula visible; defaults are clearly marked "illustrative"; where possible, pull measured values (time to first response, time to verified resolution, handled vs escalated) from the metrics endpoint.
- Acceptance: no hard-coded claim without an "assumption" label.

**U7-A2 `[CURSOR]` Deck update**
- Steps: add slides for: the problem with sourced numbers; the live flow; trust moments (cross-merchant 404, OTP refusal, failing verify, audit-chain verify); evaluation results; provider matrix; a "real vs simulated" table (real: staging payments if enabled, webhook validation, policy, verification logic; simulated: settlement ledger, Settlement Ops, Soundbox, WhatsApp, hardware telemetry); roadmap (authorized production settlement access, queue between agent and settlement pipeline, security review, multi-tenant onboarding). Cursor drafts deck content; human reviews.
- Acceptance: every claim maps to something implemented or labelled future.

---

## 9. Phase U8: Public link and access for judges

**U8-A1 `[AGY]` Hosted demo**
- Steps: expose the demo through a Cloudflare Tunnel or a hosted preview; generate a QR code; verify it does not sleep (free tiers may); demo login only; demo-mode data only; rate limits on; CORS set to the public origin; no keys, no real data.
- Acceptance: a phone on mobile data can open the link and complete the merchant flow.

**U8-A2 `[AGY]` Judge sandbox safety**
- Steps: every judge session works on its own reset copy of the demo merchant (or a visible shared reset button); demo endpoints stay behind the support role and `DEMO_DATA_MODE`; add an uptime and health badge for yourselves.
- Acceptance: two simultaneous sessions do not corrupt each other's case.

---

## 10. Phase U9: Final audit and rehearsal

**U9-C1 `[CODEX]` Final read-only audit**
- Read: the diff since the `demo-final` tag, PRD §15.1, `AGENTS.md`.
- Steps: list violations with file and line, ranked by severity; edit nothing.

**U9-A1 `[AGY]` Fix findings** in Antigravity-owned files; **U9-C2 `[CODEX]`** fixes findings in Core files (use the reserve).

**U9-H1 `[HUMAN]` Rehearsal**
1. Clean-machine setup test twice; golden run twice from reset.
2. Run the judge-driven rehearsal again on the final build.
3. Time the walkthrough to the slot; assign speaker and operator.
4. Record a new backup video of the final build.
5. Test offline mode (Ollama, then replay) with Wi-Fi off.
6. Rotate or check every key; confirm `.env` is not in Git.

---

## 11. Gates for merging to `main`

Run in this order for every phase before merging its branch.

- [ ] `scripts/guard` passes.
- [ ] Backend suite, frontend tests and lint pass.
- [ ] Golden run passes by hand and by Playwright, from a clean reset.
- [ ] Seed numbers unchanged.
- [ ] Premature `RESOLVED` is still blocked; a stale approval still returns 409; cross-merchant access is still 404.
- [ ] The diff touches only the task's files; risky areas were reviewed by the other tool or the human.
- [ ] The demo still works with the LLM tier removed (replay mode).

If any item fails, do not merge. Fix on the branch or drop it. `demo-final` is always the fallback.

---

## 12. Dependency map

```
tag demo-final (now)
U1-H1 -> U1-A1 -> U1-A2 -> U1-A3 -> U1-A4
U2-C1 -> U2-C2 -> U2-C3        (Codex, sequential)  -> U2-A1 -> U2-A2;  U2-A3, U2-A4 anytime
U3-C1 -> U3-A1 -> U3-A2, U3-A3, U3-A4
U4-A1 -> U4-A2, U4-A3 -> U4-C1 -> U4-A4 -> U4-H1      (needs U1 for the local-model column)
U5-H1 -> U5-A1 -> U5-A2 -> U5-A3 -> U5-C1
U6-H1 -> U6-A1 -> U6-A2 -> U6-A3 -> U6-A4, U6-A5 -> U6-A6 -> U6-A7 -> U6-A8 -> U6-H2
          (U2-A2 and U3-A2 add UI; build them on the new components if U6 is done first)
U7 after U4 and U6 (needs eval results and screenshots)
U8 after U6 (public build should be the redesigned one)
U9 last
```

Phases U1, U2, U3, U5 and U6 can run in parallel on separate branches because they touch different areas. Merge them one at a time and rerun the gate after each.

## 13. Progress tracker

- [ ] `demo-final` tagged and backed up
- [ ] U1 Ollama (H1, A1 to A4)
- [ ] U2 Trust claims (C1 to C3, A1 to A4)
- [ ] U3 Teammate features (C1, A1 to A4)
- [ ] U4 Evaluation (A1 to A4, C1, H1)
- [ ] U5 Live Paytm staging (H1, A1 to A3, C1)
- [ ] U6 Frontend redesign (H1, A1 to A8, H2)
- [ ] U7 Business case and deck (H1, A1, A2)
- [ ] U8 Public link (A1, A2)
- [ ] U9 Final audit and rehearsal (C1, A1, C2, H1)

## 14. If time runs out

Merge only what has passed its gate and demo from there; everything else stays on its branch for after the finale. The best partial results, in order: the frontend redesign (U6), the adversarial results (U4), the Ollama fallback (U1), the audit-chain verify button (U2-C1, A1, A2). Do not present unfinished work as done; label it "roadmap".
