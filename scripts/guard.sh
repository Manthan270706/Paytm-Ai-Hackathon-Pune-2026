#!/usr/bin/env bash
# scripts/guard.sh: Run repository integrity checks
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Executing OpsSaathi guard checks..."
python3 "${SCRIPT_DIR}/guard.py" || python "${SCRIPT_DIR}/guard.py"
