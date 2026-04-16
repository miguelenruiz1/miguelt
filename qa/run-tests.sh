#!/usr/bin/env bash
# Run Phase 1 unit tests across the 3 prioritized services.
#
# Usage:
#   bash qa/run-tests.sh            # unit tests only (fast, no DB)
#   bash qa/run-tests.sh all        # unit + integration (in-memory SQLite for subscription)
#
# Requires pytest / pytest-asyncio / aiosqlite installed in the active venv
# (see <service>/requirements-test.txt).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-unit}"

run() {
  local svc="$1"
  local target="$2"
  echo ""
  echo "=============================================================="
  echo "  $svc  ::  $target"
  echo "=============================================================="
  (cd "$ROOT/$svc" && python -m pytest "$target" -x --tb=short)
}

case "$MODE" in
  unit)
    run inventory-service    tests/unit
    run subscription-service tests/unit
    run trace-service        tests/unit
    run user-service         tests/unit
    ;;
  all)
    run inventory-service    tests/unit
    run subscription-service "tests/unit tests/integration"
    run trace-service        tests/unit
    run user-service         tests/unit
    ;;
  *)
    echo "Unknown mode: $MODE (expected: unit | all)" >&2
    exit 2
    ;;
esac

echo ""
echo "All green."
