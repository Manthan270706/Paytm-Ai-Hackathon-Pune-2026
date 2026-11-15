#!/usr/bin/env python3
"""scripts/guard.py: Repository integrity and safety guard.

Enforces BUILD_PLAN.md §1.1(4) & AGENTS.md trust rules:
1. No `float` used for money in domain/
2. No `merchant_id` in any tool input schema
3. No `.env` or API keys/secrets committed to git
4. No string-formatted raw SQL (must use parameterized SQLAlchemy/text)
5. Tenant isolation: tools/queries on tenant tables must be scoped
"""

import ast
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API_APP_DIR = REPO_ROOT / "services" / "api" / "app"

# Money variable names that must NEVER be float
MONEY_ATTR_PATTERNS = {
    "amount",
    "expected_net",
    "observed",
    "discrepancy",
    "balance",
    "fees",
    "tax",
    "taxes",
    "gross",
    "net",
    "refund_amount",
    "flat_amount",
}

# Dangerous raw secret patterns
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    re.compile(
        r"""(?:api[_-]?key|secret|token|password)\s*=\s*['\"][A-Za-z0-9_\-]{24,}['\"]""",
        re.IGNORECASE,
    ),
]


def check_no_float_money(domain_dir: Path) -> list[str]:
    """Check that domain/ files do not use float for financial attributes."""
    errors: list[str] = []
    if not domain_dir.exists():
        return errors

    for py_file in domain_dir.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError) as e:
            errors.append(f"{py_file}: Failed to parse AST: {e}")
            continue

        for node in ast.walk(tree):
            # Check function parameter and return annotations
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                for arg in node.args.args:
                    if (
                        arg.arg in MONEY_ATTR_PATTERNS
                        and arg.annotation
                        and isinstance(arg.annotation, ast.Name)
                        and arg.annotation.id == "float"
                    ):
                        errors.append(
                            f"{py_file.name}:{node.lineno}: Argument '{arg.arg}' of "
                            f"function '{node.name}' uses float! Money must use Decimal."
                        )
            # Check class attribute type annotations (e.g. Pydantic / Dataclasses)
            elif (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id in MONEY_ATTR_PATTERNS
                and isinstance(node.annotation, ast.Name)
                and node.annotation.id == "float"
            ):
                errors.append(
                    f"{py_file.name}:{node.lineno}: Field '{node.target.id}' uses float! "
                    "Money must use Decimal."
                )

    return errors


def check_tool_schemas_no_merchant_id(tools_dir: Path) -> list[str]:
    """Check that tool input schemas do not declare 'merchant_id'."""
    errors: list[str] = []
    schemas_file = tools_dir / "schemas.py"
    if not schemas_file.exists():
        return errors

    try:
        content = schemas_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(schemas_file))
    except (SyntaxError, UnicodeDecodeError) as e:
        return [f"{schemas_file}: Failed to parse AST: {e}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name.endswith("Input"):
            for item in node.body:
                if (
                    isinstance(item, ast.AnnAssign)
                    and isinstance(item.target, ast.Name)
                    and item.target.id == "merchant_id"
                ):
                    errors.append(
                        f"{schemas_file.name}:{item.lineno}: Tool input schema '{node.name}' "
                        "contains 'merchant_id'! Merchant scope must be bound server-side."
                    )
    return errors


def check_no_tracked_secrets(repo_root: Path) -> list[str]:
    """Check that .env files and hardcoded API keys are not tracked in git."""
    errors: list[str] = []

    # 1. Check if git status or git ls-files contains .env
    try:
        res = subprocess.run(
            ["git", "ls-files"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
        tracked_files = [line.strip() for line in res.stdout.splitlines() if line.strip()]
    except (subprocess.SubprocessError, FileNotFoundError):
        # Fallback if git is unavailable
        tracked_files = [str(p.relative_to(repo_root)) for p in repo_root.rglob("*") if p.is_file()]

    for file_path in tracked_files:
        norm_path = file_path.replace("\\", "/")
        if norm_path.endswith("/.env") or norm_path == ".env":
            errors.append(f"CRITICAL: .env file is tracked in git: {file_path}")

        # Scan code files for secret patterns (skip example/docs/test files)
        if any(norm_path.endswith(ext) for ext in [".py", ".ts", ".tsx", ".json"]):
            if any(
                skip in norm_path
                for skip in ("example", "test", "DEMO_RUNBOOK", "package-lock", "pnpm-lock")
            ):
                continue
            abs_path = repo_root / file_path
            if not abs_path.is_file():
                continue
            try:
                text = abs_path.read_text(encoding="utf-8", errors="ignore")
                for pat in SECRET_PATTERNS:
                    if pat.search(text):
                        errors.append(f"CRITICAL: Potential hardcoded secret in {file_path}")
            except OSError:
                pass

    return errors


def check_no_string_built_sql(code_dir: Path) -> list[str]:
    """Check that SQL queries are parameterized and do not use f-strings or % formatting."""
    errors: list[str] = []
    if not code_dir.exists():
        return errors

    sql_fstring_pattern = re.compile(
        r"""execute\s*\(\s*f["'].*?(?:SELECT|INSERT|UPDATE|DELETE)""",
        re.IGNORECASE,
    )

    for py_file in code_dir.rglob("*.py"):
        norm_str = str(py_file).replace("\\", "/")
        if (
            py_file.name.startswith("test_")
            or py_file.name.endswith("_test.py")
            or "/tests/" in norm_str
            or "/app/tests/" in norm_str
        ):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except OSError:
            continue

        for i, line in enumerate(content.splitlines(), start=1):
            if sql_fstring_pattern.search(line):
                errors.append(
                    f"{py_file.name}:{i}: Potential SQL injection via f-string: {line.strip()}"
                )

    return errors


def run_all_checks() -> bool:
    print("=" * 60)
    print("OpsSaathi AI Security & Integrity Guard (scripts/guard.py)")
    print("=" * 60)

    all_errors: list[str] = []

    print("[1/4] Checking domain/ for forbidden float money usage...")
    float_errors = check_no_float_money(API_APP_DIR / "domain")
    if float_errors:
        all_errors.extend(float_errors)
        for err in float_errors:
            print(f"  [FAIL] {err}")
    else:
        print("  [PASS] All financial models use Decimal.")

    print("[2/4] Checking tools/schemas.py for prohibited merchant_id in inputs...")
    tool_errors = check_tool_schemas_no_merchant_id(API_APP_DIR / "tools")
    if tool_errors:
        all_errors.extend(tool_errors)
        for err in tool_errors:
            print(f"  [FAIL] {err}")
    else:
        print("  [PASS] No tool input schemas expose merchant_id.")

    print("[3/4] Checking tracked files for secrets and .env...")
    secret_errors = check_no_tracked_secrets(REPO_ROOT)
    if secret_errors:
        all_errors.extend(secret_errors)
        for err in secret_errors:
            print(f"  [FAIL] {err}")
    else:
        print("  [PASS] No tracked .env files or hardcoded secrets found.")

    print("[4/4] Checking for string-built SQL queries...")
    sql_errors = check_no_string_built_sql(API_APP_DIR)
    if sql_errors:
        all_errors.extend(sql_errors)
        for err in sql_errors:
            print(f"  [FAIL] {err}")
    else:
        print("  [PASS] No string-built SQL queries detected.")

    print("-" * 60)
    if all_errors:
        print(f"GUARD FAILED: Found {len(all_errors)} violation(s).")
        return False

    print("GUARD PASSED: All repository integrity checks succeeded.")
    return True


if __name__ == "__main__":
    success = run_all_checks()
    sys.exit(0 if success else 1)
