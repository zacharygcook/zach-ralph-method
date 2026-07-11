#!/usr/bin/env bash
# Post-Sprint Hook Orchestrator
# Runs all post-sprint automation: review, docs, tests

set -euo pipefail

SPRINT_DIR="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RALPH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MANIFEST="$SPRINT_DIR/manifest.json"
SPRINT_NAME=$(basename "$SPRINT_DIR")

source "$RALPH_DIR/lib/ralph-common.sh"

EVENT_LOG="${RALPH_EVENT_LOG:-$SPRINT_DIR/hooks.events.jsonl}"
HOOK_HEARTBEAT_SEC="${HOOK_HEARTBEAT_SEC:-30}"
HOOK_IDLE_TIMEOUT_SEC="${HOOK_IDLE_TIMEOUT_SEC:-0}"
FORCE_HOOKS="${RALPH_FORCE_HOOKS:-0}"

EXIT_OK=0
EXIT_DEP_MISSING=12
EXIT_INTERRUPTED=13
EXIT_VALIDATION=14

if [[ -n "${RALPH_HOOK_RUNTIME_DIR:-}" ]]; then
  HOOK_RUNTIME_DIR="$RALPH_HOOK_RUNTIME_DIR"
elif [[ "$EVENT_LOG" == "$RALPH_DIR"/logs/*/events.jsonl ]]; then
  HOOK_RUNTIME_DIR="$(dirname "$EVENT_LOG")/hook-runtime"
else
  HOOK_RUNTIME_DIR="$RALPH_DIR/logs/$SPRINT_NAME/run-manual-$(date +%Y%m%d-%H%M%S)/hook-runtime"
fi
mkdir -p "$HOOK_RUNTIME_DIR"

FINAL_REVIEW_STATUS="pending"
FINAL_REVIEW_REASON="null"
FINAL_DOCUMENTATION_STATUS="pending"
FINAL_DOCUMENTATION_REASON="null"
FINAL_TESTS_STATUS="pending"
FINAL_TESTS_REASON="null"

log_event() {
  append_event "$EVENT_LOG" "$1" "$2" "$3"
}

manifest_update() {
  manifest_update_locked "$MANIFEST" "$@" >/dev/null 2>&1 || return 1
}

update_manifest_hook() {
  local hook_key="$1"
  local status="$2"
  local reason="${3:-null}"
  local now
  now=$(now_iso)

  [[ -f "$MANIFEST" ]] || return 0

  manifest_update \
    --arg key "$hook_key" \
    --arg status "$status" \
    --arg now "$now" \
    --arg reason "$reason" \
    '
      .hooks = (.hooks // {})
      | .hooks[$key] = (.hooks[$key] // {"status":"pending","completed_at":null,"reason":null})
      | .hooks[$key].status = $status
      | .hooks[$key].reason = (if $reason == "null" then null else $reason end)
      | .hooks[$key].completed_at = (if $status == "done" then $now else .hooks[$key].completed_at end)
    '
}

set_manifest_phase() {
  local phase="$1"
  [[ -f "$MANIFEST" ]] || return 0
  manifest_update --arg phase "$phase" '.phase = $phase'
}

hook_state_file() {
  local hook_key="$1"
  echo "$HOOK_RUNTIME_DIR/.hook-${hook_key}.state.json"
}

hook_lock_file() {
  local hook_key="$1"
  echo "$HOOK_RUNTIME_DIR/.hook-${hook_key}.lock"
}

manifest_hook_status() {
  local hook_key="$1"
  jq -r --arg key "$hook_key" '.hooks[$key].status // "pending"' "$MANIFEST" 2>/dev/null || echo "pending"
}

record_hook_result() {
  local hook_key="$1"
  local status="$2"
  local reason="${3:-null}"
  case "$hook_key" in
    review) FINAL_REVIEW_STATUS="$status"; FINAL_REVIEW_REASON="$reason" ;;
    documentation) FINAL_DOCUMENTATION_STATUS="$status"; FINAL_DOCUMENTATION_REASON="$reason" ;;
    tests) FINAL_TESTS_STATUS="$status"; FINAL_TESTS_REASON="$reason" ;;
    *) return "$EXIT_VALIDATION" ;;
  esac
}

persist_hook_results() {
  update_manifest_hook "review" "$FINAL_REVIEW_STATUS" "$FINAL_REVIEW_REASON"
  update_manifest_hook "documentation" "$FINAL_DOCUMENTATION_STATUS" "$FINAL_DOCUMENTATION_REASON"
  update_manifest_hook "tests" "$FINAL_TESTS_STATUS" "$FINAL_TESTS_REASON"
}

read_hook_pid_from_state() {
  local state_file="$1"
  jq -r '.pid // ""' "$state_file" 2>/dev/null || true
}

recover_stale_hook_state() {
  local hook_key="$1"
  local state_file lock_file pid
  state_file=$(hook_state_file "$hook_key")
  lock_file=$(hook_lock_file "$hook_key")
  [[ -f "$lock_file" || -f "$state_file" ]] || return 0

  if [[ -f "$state_file" ]]; then
    pid=$(read_hook_pid_from_state "$state_file")
    if [[ -n "$pid" ]] && process_alive "$pid"; then
      return 0
    fi
  fi

  rm -f "$lock_file" "$state_file"
  log_event "hook" "failed_stale" "Recovered stale running state for $hook_key"
}

normalize_exit_reason() {
  local exit_code="$1"
  case "$exit_code" in
    0) echo "ok" ;;
    10) echo "timeout" ;;
    11) echo "idle_timeout" ;;
    12) echo "dependency_missing" ;;
    13) echo "interrupted" ;;
    14) echo "validation_failed" ;;
    20) echo "disabled_by_config" ;;
    *) echo "failed" ;;
  esac
}

run_hook() {
  local ordinal="$1"
  local label="$2"
  local hook_key="$3"
  local script_path="$4"
  local hook_log="$5"

  local state_file lock_file marker_file pid exit_code reason prior_status
  state_file=$(hook_state_file "$hook_key")
  lock_file=$(hook_lock_file "$hook_key")
  marker_file="$SPRINT_DIR/.hook-${hook_key}.done"

  recover_stale_hook_state "$hook_key"

  prior_status=$(manifest_hook_status "$hook_key")
  if [[ "$FORCE_HOOKS" != "1" ]] && [[ "$prior_status" =~ ^(done|skipped)$ ]] && [[ -f "$marker_file" ]]; then
    echo "[$ordinal] Skipping $label (already completed)"
    record_hook_result "$hook_key" "done" "null"
    log_event "hook" "skipped" "$hook_key already completed"
    echo ""
    return 0
  fi

  if [[ "$FORCE_HOOKS" == "1" ]]; then
    rm -f "$marker_file"
  fi

  if [[ ! -x "$script_path" ]]; then
    echo "[$ordinal] Skipping $label ($(basename "$script_path") not found)"
    record_hook_result "$hook_key" "failed" "missing_script"
    log_event "hook" "failed" "$hook_key missing script"
    echo ""
    return "$EXIT_DEP_MISSING"
  fi

  if [[ -f "$lock_file" ]]; then
    if [[ -f "$state_file" ]]; then
      pid=$(read_hook_pid_from_state "$state_file")
      if [[ -n "$pid" ]] && process_alive "$pid"; then
        echo "[$ordinal] Skipping $label (already running: pid=$pid)"
        record_hook_result "$hook_key" "failed" "interrupted"
        log_event "hook" "running" "$hook_key already running pid=$pid"
        echo ""
        return "$EXIT_INTERRUPTED"
      fi
    fi
    rm -f "$lock_file"
  fi

  echo "[$ordinal] Running $label..."
  record_hook_result "$hook_key" "running" "null"
  log_event "hook" "running" "$hook_key started"

  : > "$lock_file"

  (
    RALPH_HOOK_KEY="$hook_key" \
      RALPH_EVENT_LOG="$EVENT_LOG" \
      RALPH_HOOK_RUNTIME_DIR="$HOOK_RUNTIME_DIR" \
      "$script_path" "$SPRINT_DIR"
  ) > "$hook_log" 2>&1 &
  pid=$!

  jq -nc --arg hook "$hook_key" --arg ts "$(now_iso)" --argjson pid "$pid" \
    '{hook:$hook,status:"running",pid:$pid,started_at:$ts,last_heartbeat:$ts}' > "$state_file" 2>/dev/null || true

  set +e
  monitor_process_with_heartbeat \
    "$pid" \
    "hook:$hook_key" \
    "$hook_log" \
    "$HOOK_HEARTBEAT_SEC" \
    "$HOOK_IDLE_TIMEOUT_SEC" \
    "$EVENT_LOG" \
    "$state_file"
  exit_code=$?
  set -e

  reason=$(normalize_exit_reason "$exit_code")
  rm -f "$lock_file"

  if [[ "$exit_code" -eq 0 ]]; then
    record_hook_result "$hook_key" "done" "null"
    touch "$marker_file"
    jq -nc --arg hook "$hook_key" --arg ts "$(now_iso)" --argjson pid "$pid" \
      '{hook:$hook,status:"done",pid:$pid,completed_at:$ts,last_heartbeat:$ts}' > "$state_file" 2>/dev/null || true
    log_event "hook" "ok" "$hook_key completed"
    echo ""
    return 0
  fi

  if [[ "$exit_code" -eq 20 ]]; then
    record_hook_result "$hook_key" "skipped" "$reason"
    touch "$marker_file"
    jq -nc --arg hook "$hook_key" --arg ts "$(now_iso)" --argjson pid "$pid" --arg reason "$reason" \
      '{hook:$hook,status:"skipped",pid:$pid,completed_at:$ts,reason:$reason,last_heartbeat:$ts}' > "$state_file" 2>/dev/null || true
    log_event "hook" "skipped" "$hook_key disabled by configuration"
    echo "[$ordinal] $label skipped by configuration"
    echo ""
    return 0
  fi

  record_hook_result "$hook_key" "failed" "$reason"
  rm -f "$marker_file"
  jq -nc --arg hook "$hook_key" --arg ts "$(now_iso)" --argjson pid "$pid" --arg reason "$reason" \
    '{hook:$hook,status:"failed",pid:$pid,failed_at:$ts,reason:$reason,last_heartbeat:$ts}' > "$state_file" 2>/dev/null || true
  log_event "hook" "failed" "$hook_key failed reason=$reason exit=$exit_code"

  echo "WARNING: $label failed (reason=$reason, exit=$exit_code), continuing..."
  echo "Hook log: $hook_log"
  tail -n 20 "$hook_log" 2>/dev/null || true
  echo ""
  return "$exit_code"
}

echo "========================================"
echo "Running post-sprint hooks for: $SPRINT_NAME"
echo "========================================"
echo ""

if [[ ! -f "$MANIFEST" ]]; then
  echo "ERROR: Missing manifest at $MANIFEST"
  exit "$EXIT_VALIDATION"
fi

HOOK_FAILURES=0
run_hook "1/3" "code review" "review" "$SCRIPT_DIR/review.sh" "$HOOK_RUNTIME_DIR/review.hook.log" || HOOK_FAILURES=$((HOOK_FAILURES + 1))
run_hook "2/3" "documentation generation" "documentation" "$SCRIPT_DIR/document.sh" "$HOOK_RUNTIME_DIR/document.hook.log" || HOOK_FAILURES=$((HOOK_FAILURES + 1))
run_hook "3/3" "test suite creation" "tests" "$SCRIPT_DIR/test.sh" "$HOOK_RUNTIME_DIR/test.hook.log" || HOOK_FAILURES=$((HOOK_FAILURES + 1))

echo "========================================"
echo "Post-sprint hooks complete!"
echo "========================================"

persist_hook_results

if [[ "$HOOK_FAILURES" -eq 0 ]]; then
  set_manifest_phase "hooks_done"
  log_event "hooks" "ok" "all hooks completed"
  exit "$EXIT_OK"
fi

set_manifest_phase "chunks_done"
log_event "hooks" "failed" "hook_failures=$HOOK_FAILURES"
exit "$EXIT_VALIDATION"
