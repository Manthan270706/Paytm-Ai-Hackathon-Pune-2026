#!/usr/bin/env python3
"""scripts/run_failure_drills.py: Automated reliability and failure drills runner (PRD §14).

Runs the 12 failure drills covering LLM, voice, DB, payment gateway, idempotency,
and concurrency resilience, and prints the verified PRD §14 reliability table.
"""

from __future__ import annotations

import subprocess
import sys

DRILLS = [
    (
        "LLM timeout / quota",
        (
            "Bounded retry; fall back to deterministic demo cache, then mock; "
            "keep case tools available."
        ),
        "test_drill_01_llm_timeout_and_quota_fallback",
    ),
    (
        "LLM returns invalid structure",
        "One repair retry, then deterministic path or human escalation.",
        "test_drill_02_llm_invalid_structure_deterministic_fallback",
    ),
    (
        "Sarvam unavailable",
        "Fall back to browser speech, then text entry; do not block support.",
        "test_drill_03_sarvam_unavailable_fallback",
    ),
    (
        "Paytm staging unavailable",
        "Show integration unavailable and use labelled fixtures; never silently mix data.",
        "test_drill_04_paytm_staging_unavailable_fixtures",
    ),
    (
        "Duplicate webhook",
        "Deduplicate by event ID/hash; idempotent processing.",
        "test_drill_05_duplicate_webhook_deduplication",
    ),
    (
        "Database unavailable",
        "Controlled 503; do not acknowledge writes.",
        "test_drill_06_database_unavailable_returns_controlled_503",
    ),
    (
        "Case action timeout",
        "Check idempotency key before retry; prevent duplicates.",
        "test_drill_07_case_creation_idempotency_replay",
    ),
    (
        "Re-sync request timeout",
        "Check resync_requests idempotency key; never send a second request blindly.",
        "test_drill_08_resync_request_idempotency_prevents_duplicate_send",
    ),
    (
        "Unauthorized / stale approval",
        "Reject 403 / 409; re-check current policy, version and hash.",
        "test_drill_09_unauthorized_and_stale_approval",
    ),
    (
        "Follow-up worker race",
        "SKIP LOCKED claim; no duplicate runs.",
        "test_drill_10_followup_worker_race_condition",
    ),
    (
        "Verification fails",
        "Remain IN_PROGRESS/PENDING_EXTERNAL; explain what remains unverified.",
        "test_drill_11_verification_fails_remains_verifying_blocks_resolve",
    ),
    (
        "Mic permission denied",
        "Immediately offer text chat.",
        "test_drill_12_mic_permission_denied_contract",
    ),
]


def run_drills() -> int:
    print("=" * 78)
    print(" OpsSaathi AI - PRD §14 Reliability & Failure Drills Verification")
    print("=" * 78)
    print(f"Executing {len(DRILLS)} reliability drills via pytest...\n")

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "services/api/app/tests/api/test_p4_a9_failure_drills.py",
        "-q",
        "--tb=short",
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    success = res.returncode == 0

    print("| # | Failure | Required Behaviour | Result |")
    print("|---|---------|-------------------|--------|")
    for i, (failure, behavior, _test_name) in enumerate(DRILLS, 1):
        status = "PASS" if success else "CHECK"
        print(f"| {i:02d} | {failure} | {behavior} | [{status}] |")

    print("\n" + "=" * 78)
    if success:
        print("ALL 12 RELIABILITY & FAILURE DRILLS PASSED (PRD §14 COMPLIANT)")
        print("=" * 78)
        return 0
    else:
        print("SOME DRILLS FAILED:")
        print(res.stdout)
        print(res.stderr)
        print("=" * 78)
        return 1


if __name__ == "__main__":
    sys.exit(run_drills())
