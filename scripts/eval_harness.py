#!/usr/bin/env python3
"""CLI runner for OpsSaathi AI Evaluation and Adversarial Testing Harness.

Usage:
    python scripts/eval_harness.py
"""

import json
import os
import sys

# Add services/api to sys.path so app imports resolve smoothly
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_DIR = os.path.join(ROOT_DIR, "services", "api")
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from fastapi.testclient import TestClient

from app.main import app
from app.tests.eval.harness import EvalHarness
from app.tests.eval.scenarios import BENCHMARK_SCENARIOS


def main() -> int:
    print("============================================================")
    print("OpsSaathi AI Evaluation & Adversarial Test Harness (U4-A1)")
    print("============================================================")

    client = TestClient(app)
    harness = EvalHarness(client=client)

    print(f"Running {len(BENCHMARK_SCENARIOS)} benchmark and adversarial scenarios...")
    suite_result = harness.run_suite(BENCHMARK_SCENARIOS)

    # Print Summary Table
    print("\n------------------------------------------------------------")
    print(f"Total Scenarios: {suite_result.total_scenarios}")
    print(f"Passed:          {suite_result.passed_scenarios}")
    print(f"Failed:          {suite_result.failed_scenarios}")
    print(f"Pass Rate:       {suite_result.pass_rate_pct}%")
    print(f"p50 Latency:     {suite_result.p50_latency_ms} ms")
    print(f"p95 Latency:     {suite_result.p95_latency_ms} ms")
    print(f"Intent Accuracy: {suite_result.intent_accuracy_pct}%")
    print(f"Grounding Rate:  {suite_result.grounding_accuracy_pct}%")
    print(f"Zero Float Money:{suite_result.zero_float_compliance_pct}%")
    print(f"Adversarial Safe:{suite_result.adversarial_safety_pct}%")
    print("------------------------------------------------------------\n")

    print("Category Breakdown:")
    for cat, stats in suite_result.category_breakdown.items():
        print(f"  - {cat:<14}: {stats['passed']}/{stats['total']} passed ({stats['pass_rate_pct']}%)")

    # Save Markdown report
    docs_dir = os.path.join(ROOT_DIR, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    report_md_path = os.path.join(docs_dir, "EVAL_REPORT.md")
    md_content = harness.generate_markdown_report(suite_result)
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"\n[REPORT] Saved evaluation report to: docs/EVAL_REPORT.md")

    # Save JSON results
    json_path = os.path.join(docs_dir, "eval_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(suite_result.model_dump(), f, indent=2)
    print(f"[DATA]   Saved JSON metrics to: docs/eval_results.json")

    if suite_result.pass_rate_pct < 90.0:
        print("\n[FAIL] Evaluation suite pass rate fell below threshold (90%).")
        return 1

    print("\n[PASS] Evaluation harness completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
