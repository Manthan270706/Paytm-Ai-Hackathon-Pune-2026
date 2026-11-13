#!/usr/bin/env python3
"""scripts/rehearse_finale.py: Finale & Rehearsal Verification Runner.

PRD §16, BUILD_PLAN §Phase 6.
Executes the entire verification pipeline before the live judging finale:
1. Security & Integrity Guard (scripts/guard.py)
2. Python Code Quality & Type Check (ruff, mypy)
3. Full Backend & Security Suite (pytest 169 tests)
4. Reliability & Failure Drills (PRD §14 table)
5. Web App Lint & Production Build (ESLint, TypeScript, Vite)
6. Playwright End-to-End Automation (scripts/golden_run.md)
7. Seed Scenario Reset & Ledger Verification
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def print_header(title: str) -> None:
    print("\n" + "=" * 78)
    print(f" {title}")
    print("=" * 78)


def run_step(
    step_num: int, name: str, cmd: list[str], cwd: Path | None = None
) -> tuple[bool, float, str]:
    print(f"\n[{step_num}/7] Running: {name}...")
    start = time.perf_counter()
    res = subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
    )
    elapsed = time.perf_counter() - start
    passed = res.returncode == 0
    status_str = "PASS" if passed else "FAIL"
    print(f"       -> [{status_str}] completed in {elapsed:.2f}s")
    if not passed:
        print("\n--- Output on failure ---")
        print(res.stdout[-1500:] if len(res.stdout) > 1500 else res.stdout)
        print(res.stderr[-1500:] if len(res.stderr) > 1500 else res.stderr)
        print("-------------------------")
    return passed, elapsed, res.stdout


def main() -> int:
    print_header("OpsSaathi AI - Phase 6 Finale & Rehearsal Verification Suite")
    print("Verifying complete system readiness for live judging demo...")

    total_start = time.perf_counter()
    steps_results: list[tuple[str, bool, float]] = []

    # 1. Guard check
    p1, t1, _ = run_step(
        1,
        "Repository Security & Invariant Guard (scripts/guard.py)",
        [sys.executable, "scripts/guard.py"],
    )
    steps_results.append(("Security & Invariant Guard", p1, t1))

    # 2. Linter & Mypy
    p2a, t2a, _ = run_step(
        2,
        "Backend Linter (ruff check)",
        [sys.executable, "-m", "ruff", "check", "services/api/app", "scripts"],
    )
    p2b, t2b, _ = run_step(
        2,
        "Type Invariants (mypy)",
        [
            sys.executable,
            "-m",
            "mypy",
            "services/api/app/tools",
            "services/api/app/agents",
            "services/api/app/integrations",
            "services/api/app/workers",
        ],
    )
    steps_results.append(("Code Quality (Ruff & Mypy)", p2a and p2b, t2a + t2b))

    # 3. Full pytest suite
    p3, t3, _ = run_step(
        3,
        "Backend & Security Test Suite (169 tests)",
        [sys.executable, "-m", "pytest", "services/api/app/tests", "-q"],
    )
    steps_results.append(("Backend Test Suite (169 tests)", p3, t3))

    # 4. Failure drills
    p4, t4, _ = run_step(
        4,
        "PRD §14 Reliability & Failure Drills",
        [sys.executable, "scripts/run_failure_drills.py"],
    )
    steps_results.append(("Reliability & Failure Drills", p4, t4))

    # 5. Web lint and build
    web_dir = REPO_ROOT / "apps" / "web"
    is_win = sys.platform == "win32"
    npm_cmd = "npm.cmd" if is_win else "npm"

    p5a, t5a, _ = run_step(
        5,
        "Frontend Linter (eslint)",
        [npm_cmd, "run", "lint"],
        cwd=web_dir,
    )
    p5b, t5b, _ = run_step(
        5,
        "Frontend Production Build (tsc && vite build)",
        [npm_cmd, "run", "build"],
        cwd=web_dir,
    )
    steps_results.append(("Frontend Lint & Build", p5a and p5b, t5a + t5b))

    # 6. Playwright E2E
    p6, t6, _ = run_step(
        6,
        "Playwright Golden Run E2E (scripts/golden_run.md)",
        [npm_cmd, "run", "test:e2e"],
        cwd=web_dir,
    )
    steps_results.append(("Playwright E2E Golden Run", p6, t6))

    # 7. Seed demo verification
    p7, t7, out7 = run_step(
        7,
        "Seeded Demo State & Scenario Reset",
        [sys.executable, "scripts/seed_demo.py", "--sqlite"],
    )
    steps_results.append(("Demo Scenario Reset", p7, t7))

    total_elapsed = time.perf_counter() - total_start

    print_header("Finale Rehearsal Summary & Judging Checklist")
    print("| # | Verification Step | Status | Duration |")
    print("|---|-------------------|--------|----------|")
    for i, (name, passed, elapsed) in enumerate(steps_results, 1):
        status = "[PASS]" if passed else "[FAIL]"
        print(f"| {i:02d} | {name:<35} | {status} | {elapsed:>6.2f}s |")

    all_passed = all(p for _, p, _ in steps_results)
    print("-" * 78)
    print(f"Total Rehearsal Duration: {total_elapsed:.2f}s")
    if all_passed:
        print("\n [SUCCESS] ALL SYSTEMS GO FOR LIVE FINALE DEMO!")
        print("  - Presentation Deck: docs/PITCH_DECK.md (10 Judging Slides)")
        print("  - Live Walkthrough:   docs/DEMO_RUNBOOK.md (4-5 Minute Script)")
        print("  - Fallback Protocol:  DEMO_DETERMINISTIC=true (Wifi-off Replay)")
        print("=" * 78 + "\n")
        return 0
    else:
        print("\n [WARNING] Rehearsal detected failures. Review output above before stage.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
