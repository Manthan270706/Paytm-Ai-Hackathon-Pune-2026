# TOOL_ROUTING.md: using Codex, Antigravity and Cursor together

Adds a third tool to `docs/BUILD_PLAN.md` and `docs/UPSCALE_PLAN.md`. Same rules (`AGENTS.md`), same task IDs, same gates. This file only changes **who does what, in what order, and what to do when a tool runs out of limit**.

Written Sun 15 Nov 2026, 12:50 IST.

---

## 0. Naming (avoid confusion)

| Name in these docs | What it is |
| --- | --- |
| **Cursor (Grok 4.7)** | The Cursor editor using Cursor's first-party Grok 4.7 model (or whichever Grok model your picker shows; the free plan may be on 4.6). This is a coding tool for building the project. |
| **Groq Cloud** | The inference service the app itself calls at run time (the `groq` tier in the LLM cascade). Not a coding tool. |
| **Codex / Antigravity** | The other two coding tools, as before. |

Never write "Groq" for the Cursor model, and never configure the app to use the Cursor model; the app uses Ollama, Groq Cloud, replay cache and mock.

## 1. Role of each tool

| Tool | Best at | Limit situation | Use it for | Do not use it for |
| --- | --- | --- | --- | --- |
| **Codex** | Precise, test-backed code | Limited weekly credits | Trust-critical logic (U2-C1 to C3, U3-C1), final audit, review of risky diffs | Anything else |
| **Antigravity** (Pro) | Large builds, parallel agents, many files | Plenty | Big features and screens, adapters, workers, eval harness, hosting, E2E | Trust-critical files |
| **Cursor (Grok 4.7)** | Interactive multi-file edits and multi-step coding inside the editor; the vendor describes it as strong on long tasks but it can be token-hungry | Free plan: usage is limited and the exact numbers are not published | Bounded medium tasks, UI polish, copy, tests for non-risky code, scenario writing, a second-opinion review | Long unattended agent runs; trust-critical code; whole-repo scans |

The vendor's own benchmark claims for Grok 4.7 are self-reported, so treat its output like any other tool's: tests and the guard script decide, not the model's confidence.

## 2. Updated lanes and file ownership

| Lane | Owner | Files |
| --- | --- | --- |
| Core trust logic | Codex | `domain/`, `ScopedRepository`, `core/auth*`, `core/redaction*`, `core/webhook*`, audit chain, approvals, action ledger |
| Backend, agent, integrations, workers, E2E, hosting | Antigravity | `api/v1/`, `db/` models and migrations, `agents/`, `tools/`, `integrations/`, `workers/`, Playwright |
| Frontend polish, copy, locale strings, scenario files, docs text | Cursor | `apps/web/src/components/**` (assigned ones), `apps/web/src/locales/**`, `tests/eval/scenarios/**`, `docs/**` text |
| Review (second key) | Cursor reviews Codex diffs; Codex reviews Antigravity and Cursor diffs in risky areas; human has the final say | read-only |

Two tools must never edit the same file at the same time. Each task has one owner and one branch (`upscale/<task-id>`).

## 3. Routing for remaining tasks

Order follows `UPSCALE_PLAN.md` section 1. "Chunk" means split the task into sessions that each finish within one small Cursor request budget.

### Phase U6 Frontend redesign (highest priority)

| Task | Owner | Notes |
| --- | --- | --- |
| U6-H1 references | Human | |
| U6-A1 design audit with screenshots | Antigravity | It can drive a browser and capture screens |
| U6-A2 DESIGN.md and tokens | Antigravity | One file set; everything else depends on it |
| U6-A3 primitives, chunk 1: Button, Input, Card, ListRow, StatusChip | **Cursor** | Small and well defined |
| U6-A3 primitives, chunk 2: Stepper, BottomNav, Sidebar, DataTable | **Cursor** (second session) | If limit hit, move to Antigravity |
| U6-A3 primitives, chunk 3: Modal, Toast, Skeleton, EmptyState, ErrorState | Antigravity | |
| U6-A4 merchant mobile app | Antigravity | Own worktree |
| U6-A5 operations console | Antigravity | Own worktree, in parallel with A4 |
| U6-A6 copy and agent tone, locale files | **Cursor** | Text-heavy, low risk |
| U6-A7 accessibility fixes | **Cursor** (fixes) after Antigravity runs axe and Lighthouse | |
| U6-A8 visual QA and Playwright | Antigravity | Cursor fixes small visual bugs it lists |
| U6-H2 review | Human | |

### Other phases

| Task | Owner |
| --- | --- |
| U1-A1 to A4 Ollama | Antigravity (A4 benchmark table text: Cursor) |
| U2-C1, C2, C3 | Codex |
| U2-A1 schema and endpoints | Antigravity |
| U2-A2 trust UI buttons | **Cursor** |
| U2-A3 Postgres verifier role test | Antigravity |
| U2-A4 claim-language pass | **Cursor** (grep and replace across docs and UI strings) |
| U2 review of Codex diffs | **Cursor** (second key), then human |
| U3-C1 | Codex |
| U3-A1 proactive scanner | Antigravity |
| U3-A2 agent assist panel | **Cursor** |
| U3-A3 simulated Soundbox | Antigravity |
| U3-A4 WhatsApp-style simulation | **Cursor** |
| U4-A1 eval harness | Antigravity |
| U4-A2 scenario set (50 to 60) | **Cursor** (writing scenario files is cheap and text-based) |
| U4-A3 adversarial suite | Antigravity writes; Cursor adds multilingual variants |
| U4-C1 expectations review | Codex (short, read-only) |
| U4-A4 results and fixes | Antigravity; Core fixes to Codex |
| U5-H1 to A3 | Antigravity |
| U5-C1 | Codex (read-only) |
| U7-A1 impact calculator | Antigravity |
| U7-A2 deck text | **Cursor** drafts; human edits |
| U8-A1, A2 hosting | Antigravity |
| U9-C1 final audit | Codex |
| U9-A1 fixes | Antigravity or Cursor, by file ownership |
| U9-C2 Core fixes | Codex (reserve) |
| U9-H1 rehearsal | Human |

## 4. Parallel schedule

Run these at the same time on separate worktrees. Merge one branch at a time and rerun the gate after each (`UPSCALE_PLAN.md` section 11).

| Stream | Tool | Work |
| --- | --- | --- |
| A | Antigravity | U6-A1, A2, then A4 and A5 |
| B | Cursor | U6-A3 chunks, then A6 and A7 |
| C | Codex | U2-C1, C2, C3 (then U3-C1) |
| D | Antigravity (second agent) | U1 Ollama, U4-A1 harness |
| E | Human | tag `demo-final`, references, hosting checks, native-speaker review |

If only one Antigravity agent is practical, do stream D after stream A.

## 5. Stretching limits without lowering quality

1. **One task per session.** Start a fresh session for each task ID. Long chats cost more and drift.
2. **Reference, do not paste.** Tell the tool the file paths and PRD section numbers. Do not paste whole files or the whole repo.
3. **No exploration.** Name the files up front; forbid repo-wide scans and re-reads.
4. **Humans and scripts do mechanical work.** Run tests, lint, screenshots and the guard script yourself instead of asking an agent to loop on them.
5. **Cheapest sufficient tool.** Text, copy and small component work go to Cursor; large builds go to Antigravity; only trust-critical code goes to Codex.
6. **Use editor completion for typing-heavy edits** in Cursor instead of agent requests where it is enough.
7. **Short reports.** Ask every tool for a report of 10 lines or fewer.
8. **Check usage before you start a big task.** Look at each tool's usage page and pick the task that fits the remaining budget. Cursor does not publish exact free-tier numbers, so watch your dashboard instead of assuming.

## 6. Multiple accounts

- Plan for each person's **own** accounts only. Do not share logins or API keys, and never paste keys into any tool or chat.
- Do not create extra accounts just to get around free-tier limits. Many providers prohibit that in their terms and can suspend the accounts, which would hurt you on the day. Check each provider's terms before relying on a second account.
- If you and your teammate each have your own accounts, assign work by person: each person runs their own tool sessions on their own worktrees and pushes branches. The repo, `AGENTS.md` and `docs/HANDOFF.md` keep everyone consistent.
- Whatever the account situation, the plan must still work if one tool is unavailable. Section 7 says how.

## 7. When a tool hits its limit

1. **Stop at a clean point.** Ask the tool for a handoff note (template in section 9) and commit what passes tests on the task branch. Do not leave half-edited files.
2. **Pick the fallback by task type:**

| Stuck tool | Task type | Move to |
| --- | --- | --- |
| Codex | Trust-critical code, not finished | Wait for its weekly reset if the finale allows; otherwise the human implements the smallest safe version using the written tests, and Cursor reviews it. Never hand trust-critical code to a tool without a test-first spec. |
| Codex | Audit or review | Cursor does a first-pass review; the human does the final check against the PRD §15.1 checklist. |
| Antigravity | Large builds | Split into smaller chunks and give them to Cursor in order; drop optional items first (see section 8). |
| Cursor | Medium tasks | Antigravity takes them. |
| Cursor | Small edits | Do by hand with editor completion, or defer. |

3. **Never lower the gates.** If the tool that normally reviews risky code is out of limit, the human reviews it and runs the guard script, tests and golden run before merging.

## 8. What to drop first if limits bite

Drop in this order (lowest value first), and label dropped items "roadmap" in the deck:
1. U3-A4 WhatsApp-style simulation
2. U3-A3 Soundbox simulation
3. U8-A2 judge sandbox (keep a single shared reset button)
4. U5-A1 to A3 live staging (keep the synthetic fixtures)
5. U3-A2 agent assist panel
6. U2-C3 compensation ledger

Never drop: the redesign's golden-run compatibility, the adversarial suite, U2-C1 and U2-C2 if the "tamper-evident" and "signed" wording stays in the deck (otherwise remove that wording), the claim-language pass, or the final audit.

## 9. Handoff note

Every tool writes or updates `docs/HANDOFF.md` after each task (append a section; do not rewrite old ones). A tool that picks up the work reads only this section plus the task text.

```markdown
## <task-id>: <title>  (<tool>, <date time>)
- Status: done | partial | blocked
- Branch: upscale/<task-id>   Last commit: <hash>
- Files changed: <list>
- Tests run and result: <commands and pass/fail counts>
- Acceptance criteria: <each one, met or not>
- Left to do: <short list, in order>
- Gotchas: <anything the next tool must know>
- Trust-rule check: no float money, no merchant_id in tool schemas, no secrets, scoped queries only
```

## 10. Cursor setup and prompt

**Setup (human, 5 minutes)**
1. Open the repo folder in Cursor. Cursor reads project rules from its own rules folder; if it does not pick up `AGENTS.md` by itself, add `.cursor/rules/opssaathi.mdc` containing one instruction: "Read AGENTS.md and docs/PRD.md before any task and follow them."
2. In the model picker, select the strongest Cursor model your plan allows. Note which Grok version it shows.
3. Work on a git worktree or branch per task, like the other tools.
4. Turn off any setting that lets the agent run indefinitely or auto-approve commands; this keeps token use and risk low.

**Prompt to paste at the start of every Cursor session**

```text
You are working on the OpsSaathi AI repo. Read AGENTS.md first, then only the files and PRD or plan sections named in my task. My free-tier usage is limited, so be economical.

RULES
- Do only the task ID I give you, in its file list. Do not scan the repo, refactor, rename, or start the next task.
- Follow AGENTS.md trust rules exactly. Never edit domain/, ScopedRepository, core/auth, core/redaction, core/webhook, the audit chain, approvals or verification code. If the task seems to need that, stop and tell me.
- Do not change the OpenAPI contract, adapter interfaces or tool signatures.
- No new dependencies unless the task says so. No secrets in files. Colours, spacing and fonts come from the design tokens only (docs/design/DESIGN.md), never hard-coded.
- Keep every existing data-testid unless I say otherwise.
- If you have written code, run only the targeted tests and the lint for the files you touched, then scripts/guard once. If the same check fails twice for the same reason, stop and report.
- Stop as soon as the acceptance criteria pass.

FINAL REPORT (10 lines or fewer), in the HANDOFF.md format: status, branch and commit, files changed, tests and result, acceptance criteria, what is left, gotchas.
```

**Cursor as the second-key reviewer (read-only prompt)**

```text
Review-only task. Read the diff of branch <codex-branch> against main, plus AGENTS.md section 2 (trust rules). Do not edit files and do not run the full suite. List any place where: money uses float; a tool schema takes merchant_id; a query is not scoped; RESOLVED is reachable without a verifier PASS; an approval can resume without role, version, hash and signature checks; a secret or raw sensitive input could be logged. Give file and line for each finding, or say "no findings". 15 lines max.
```

A review by a different model family is useful, but it does not replace tests or the human check.

## 11. Gate reminder

Each branch must pass before merging: guard, backend and frontend tests, lint, golden run from reset, seed numbers unchanged, premature RESOLVED blocked, stale approval 409, cross-merchant 404, replay mode works. `demo-final` stays the fallback.
