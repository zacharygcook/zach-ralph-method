#!/usr/bin/env bash

set -euo pipefail

SPRINT_DIR="${1:?Usage: test.sh <sprint-dir>}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RALPH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$RALPH_DIR/.." && pwd)"
source "$RALPH_DIR/config.env"
source "$RALPH_DIR/lib/ralph-common.sh"

if [[ "${RALPH_TESTS_ENABLED:-true}" != "true" ]]; then
  echo "Test hook disabled explicitly by RALPH_TESTS_ENABLED=false"
  exit 20
fi

if [[ -z "${RALPH_TEST_COMMAND:-}" ]]; then
  echo "RALPH_TEST_COMMAND is required while the test hook is enabled"
  exit 12
fi

export RALPH_PROJECT_ROOT="$PROJECT_ROOT"
export RALPH_SPRINT_DIR="$SPRINT_DIR"
echo "Running configured test command: $RALPH_TEST_COMMAND"
(cd "$PROJECT_ROOT" && bash -lc "$RALPH_TEST_COMMAND")

if [[ -n "${RALPH_E2E_COMMAND:-}" ]]; then
  echo "Running configured E2E command: $RALPH_E2E_COMMAND"
  (cd "$PROJECT_ROOT" && bash -lc "$RALPH_E2E_COMMAND")
fi
