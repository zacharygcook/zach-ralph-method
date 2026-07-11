#!/usr/bin/env bash
# Ralph Wiggum Loop - Autonomous Agent Runner

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.env"
source "$SCRIPT_DIR/lib/ralph-common.sh"

PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MAX_ITERATIONS="${MAX_ITERATIONS:-30}"
AGENT="${RALPH_AGENT:-${AGENT:-}}"
CURRENT_SPRINT="${CURRENT_SPRINT:-}"
HEARTBEAT_SEC="${HEARTBEAT_SEC:-30}"
AGENT_IDLE_TIMEOUT_SEC="${AGENT_IDLE_TIMEOUT_SEC:-0}"
POST_RESULT_IDLE_SEC="${POST_RESULT_IDLE_SEC:-45}"
RALPH_INTERACTIVE="${RALPH_INTERACTIVE:-false}"
RALPH_INTERACTIVE_TIMEOUT_SEC="${RALPH_INTERACTIVE_TIMEOUT_SEC:-20}"

missing=$(require_commands bash git jq python3 || true)
if [[ -n "$missing" ]]; then
  echo "$missing"
  exit 12
fi
if [[ "${RALPH_UNATTENDED_APPROVED:-false}" != "true" ]]; then
  echo "Refusing autonomous execution until RALPH_UNATTENDED_APPROVED=true in .ralph/config.env"
  exit 14
fi

RESUME=false
FORCE_HOOKS=false
for arg in "$@"; do
  case "$arg" in
    --resume) RESUME=true ;;
    --force-hooks) FORCE_HOOKS=true ;;
    *)
      echo "Unknown option: $arg"
      echo "Usage: ./loop.sh [--resume] [--force-hooks]"
      exit 1
      ;;
  esac
done

SPRINT_DIR="$SCRIPT_DIR/sprints/$CURRENT_SPRINT"
PROMPT_FILE="$SPRINT_DIR/prompt.md"
CHUNKS_FILE="$SPRINT_DIR/chunks.json"
MANIFEST_FILE="$SPRINT_DIR/manifest.json"

if [[ -z "$CURRENT_SPRINT" ]] || [[ ! -d "$SPRINT_DIR" ]]; then
  echo "Error: CURRENT_SPRINT not set or sprint folder not found"
  echo "Set CURRENT_SPRINT in config.env (e.g., CURRENT_SPRINT=1-scaffold-foundation)"
  exit 1
fi

RUN_ID=$(date +%Y%m%d-%H%M%S)
LOG_DIR="$SCRIPT_DIR/logs/$CURRENT_SPRINT/run-$RUN_ID"
mkdir -p "$LOG_DIR"

START_COMMIT=$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")
START_TIME=$(now_iso)
ORCHESTRATOR_LOG="$LOG_DIR/orchestrator.log"
EVENT_LOG="$LOG_DIR/events.jsonl"

log_orchestrator() {
  local msg="$1"
  local ts
  ts=$(now_iso)
  echo "[$ts] $msg" | tee -a "$ORCHESTRATOR_LOG"
}

log_event() {
  append_event "$EVENT_LOG" "$1" "$2" "$3"
}

if [[ ! -f "$MANIFEST_FILE" ]] || ! jq -e '.start_commit' "$MANIFEST_FILE" >/dev/null 2>&1; then
  cat > "$MANIFEST_FILE" <<EOF_MANIFEST
{
  "sprint": "$CURRENT_SPRINT",
  "start_commit": "$START_COMMIT",
  "started_at": "$START_TIME",
  "end_commit": null,
  "completed_at": null,
  "iterations": 0,
  "commits": [],
  "phase": "running",
  "hooks": {
    "review": {"status": "pending", "completed_at": null, "reason": null},
    "documentation": {"status": "pending", "completed_at": null, "reason": null},
    "tests": {
      "status": "pending",
      "completed_at": null,
      "reason": null,
      "phases": {
        "generate_tests": {"status": "pending", "completed_at": null, "reason": null},
        "verify_tests": {"status": "pending", "completed_at": null, "reason": null},
        "run_e2e": {"status": "pending", "completed_at": null, "reason": null}
      }
    }
  }
}
EOF_MANIFEST
fi

ensure_manifest_schema() {
  manifest_update_locked "$MANIFEST_FILE" '
    .phase = (.phase // "running")
    | .hooks = (.hooks // {})
    | .hooks.review = (.hooks.review // {"status":"pending","completed_at":null,"reason":null})
    | .hooks.documentation = (.hooks.documentation // {"status":"pending","completed_at":null,"reason":null})
    | .hooks.tests = (.hooks.tests // {"status":"pending","completed_at":null,"reason":null,"phases":{}})
    | .hooks.tests.reason = (.hooks.tests.reason // null)
    | .hooks.tests.phases = (.hooks.tests.phases // {})
    | .hooks.tests.phases.generate_tests = (.hooks.tests.phases.generate_tests // {"status":"pending","completed_at":null,"reason":null})
    | .hooks.tests.phases.verify_tests = (.hooks.tests.phases.verify_tests // .hooks.tests.phases.verify_backend_tests // {"status":"pending","completed_at":null,"reason":null})
    | del(.hooks.tests.phases.verify_backend_tests)
    | .hooks.tests.phases.run_e2e = (.hooks.tests.phases.run_e2e // {"status":"pending","completed_at":null,"reason":null})
  ' || {
    log_orchestrator "ERROR: Failed to normalize manifest schema: $MANIFEST_FILE"
    return 1
  }
}

manifest_update() {
  manifest_update_locked "$MANIFEST_FILE" "$@" || {
    log_orchestrator "ERROR: Manifest update failed"
    return 1
  }
}

finalize_manifest_chunks_done() {
  local end_commit end_time
  end_commit=$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")
  end_time=$(now_iso)
  manifest_update \
    --arg end "$end_commit" --arg time "$end_time" \
    '.end_commit = ($end // .end_commit)
      | .completed_at = ($time // .completed_at)
      | .phase = "chunks_done"' || return 1
  log_orchestrator "manifest_updated: end_commit=$end_commit completed_at=$end_time phase=chunks_done"
  log_event "manifest" "ok" "phase=chunks_done"
}

hooks_completed() {
  [[ "$(jq -r '.phase // ""' "$MANIFEST_FILE" 2>/dev/null || echo "")" == "hooks_done" ]]
}

mark_hooks_phase_done() {
  local now
  now=$(now_iso)
  manifest_update \
    --arg now "$now" \
    '.phase = "hooks_done"
      | .hooks.review.status = (if .hooks.review.status == "done" then "done" else .hooks.review.status end)
      | .hooks.documentation.status = (if .hooks.documentation.status == "done" then "done" else .hooks.documentation.status end)
      | .hooks.tests.status = (if .hooks.tests.status == "done" then "done" else .hooks.tests.status end)
      | .hooks.review.completed_at = (if .hooks.review.status == "done" and .hooks.review.completed_at == null then $now else .hooks.review.completed_at end)
      | .hooks.documentation.completed_at = (if .hooks.documentation.status == "done" and .hooks.documentation.completed_at == null then $now else .hooks.documentation.completed_at end)
      | .hooks.tests.completed_at = (if .hooks.tests.status == "done" and .hooks.tests.completed_at == null then $now else .hooks.tests.completed_at end)' || return 1
  log_orchestrator "manifest_updated: phase=hooks_done"
  log_event "manifest" "ok" "phase=hooks_done"
}

all_chunks_pass_fn() {
  all_chunks_pass "$CHUNKS_FILE"
}

passed_chunk_count() {
  count_passed_chunks "$CHUNKS_FILE"
}

get_next_sprint() {
  local current_num next_num candidate
  current_num=$(echo "$CURRENT_SPRINT" | grep -oE '^[0-9]+' || echo "")
  [[ -z "$current_num" ]] && return 0
  next_num=$((current_num + 1))
  for candidate in "$SCRIPT_DIR/sprints/${next_num}-"*; do
    if [[ -d "$candidate" ]]; then
      basename "$candidate"
      return 0
    fi
  done
  return 0
}

offer_next_sprint_prompt() {
  local next_sprint="$1"

  echo ""
  echo "Next sprint available: $next_sprint"
  echo "To start: Update CURRENT_SPRINT=$next_sprint in config.env and run ./loop.sh"
  echo ""

  if [[ "$RALPH_INTERACTIVE" == "true" ]] && [[ -t 0 ]]; then
    if read -r -t "$RALPH_INTERACTIVE_TIMEOUT_SEC" -p "Auto-update config and continue? [y/N] " REPLY; then
      echo
      if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Set CURRENT_SPRINT=$next_sprint in $SCRIPT_DIR/config.env, then run ./loop.sh again."
      fi
    else
      echo
      echo "Skipping prompt after timeout (${RALPH_INTERACTIVE_TIMEOUT_SEC}s)."
    fi
  fi
}

run_post_sprint_hooks() {
  if [[ ! -x "$SCRIPT_DIR/hooks/post-sprint.sh" ]]; then
    log_orchestrator "hooks_missing: $SCRIPT_DIR/hooks/post-sprint.sh"
    return 1
  fi

  log_orchestrator "hooks_started"
  log_event "hooks" "running" "post-sprint start"

  if RALPH_EVENT_LOG="$EVENT_LOG" RALPH_FORCE_HOOKS="$([[ "$FORCE_HOOKS" == "true" ]] && echo 1 || echo 0)" \
    "$SCRIPT_DIR/hooks/post-sprint.sh" "$SPRINT_DIR"; then
    log_orchestrator "hooks_finished: success"
    log_event "hooks" "ok" "post-sprint success"
  else
    log_orchestrator "hooks_finished: partial_or_failed"
    log_event "hooks" "failed" "post-sprint partial_or_failed"
    return 1
  fi
}

RECONCILIATION_DONE=false
reconcile_completion_state() {
  if [[ "$RECONCILIATION_DONE" == "true" ]]; then
    return 0
  fi
  RECONCILIATION_DONE=true

  ensure_manifest_schema || true

  if ! all_chunks_pass_fn; then
    log_orchestrator "reconcile_skip: chunks_incomplete"
    log_event "reconcile" "skipped" "chunks_incomplete"
    return 0
  fi

  if [[ "$(jq -r '.end_commit // "null"' "$MANIFEST_FILE" 2>/dev/null || echo "null")" == "null" ]]; then
    finalize_manifest_chunks_done || true
  fi

  if hooks_completed && [[ "$FORCE_HOOKS" != "true" ]]; then
    log_orchestrator "reconcile_skip: hooks_already_done"
    log_event "reconcile" "skipped" "hooks_already_done"
    return 0
  fi

  echo ""
  echo "Running post-sprint hooks..."
  run_post_sprint_hooks || true

  if jq -e '([.hooks.review.status, .hooks.documentation.status, .hooks.tests.status] | all(. == "done" or . == "skipped"))' "$MANIFEST_FILE" >/dev/null 2>&1; then
    mark_hooks_phase_done || true
  fi
}

trap 'log_orchestrator "signal_received: INT"; log_event "signal" "int" "INT received"; reconcile_completion_state; exit 130' INT
trap 'log_orchestrator "signal_received: TERM"; log_event "signal" "term" "TERM received"; reconcile_completion_state; exit 143' TERM
trap 'reconcile_completion_state' EXIT

start_stream_sidecar() {
  local formatter_path="${1:-}"
  touch "$LOG_FILE"

  if [[ -n "$formatter_path" ]]; then
    (
      tail -n +1 -f "$LOG_FILE" 2>/dev/null | python3 "$formatter_path"
    ) &
  else
    (
      tail -n +1 -f "$LOG_FILE" 2>/dev/null
    ) &
  fi

  STARTED_SIDECAR_PID="$!"
}

stop_stream_sidecar() {
  local sidecar_pid="${1:-}"
  STOPPED_SIDECAR_EXIT=0
  [[ -z "$sidecar_pid" ]] && return 0

  kill_process_tree "$sidecar_pid"
  # Sidecar termination is expected after agent completion/kill.
  # Keep this function non-fatal under `set -e` and expose exit via variable.
  set +e
  wait "$sidecar_pid" 2>/dev/null
  STOPPED_SIDECAR_EXIT=$?
  set -e
  return 0
}

start_agent_iteration() {
  local formatter_path=""
  local sidecar_pid agent_pid agent_pgid
  : > "$LOG_FILE"

  case "$AGENT" in
    claude)
      formatter_path="$SCRIPT_DIR/format-stream.py"
      ;;
    codex)
      formatter_path="$SCRIPT_DIR/format-codex-stream.py"
      ;;
    amp|opencode|droid)
      formatter_path=""
      ;;
    *) formatter_path="" ;;
  esac

  start_stream_sidecar "$formatter_path"
  sidecar_pid="$STARTED_SIDECAR_PID"

  run_agent "$AGENT" "$PROMPT_FILE" "$PROJECT_ROOT" >"$LOG_FILE" 2>&1 &
  agent_pid=$!
  agent_pgid=$(process_pgid "$agent_pid")

  AGENT_PID="$agent_pid"
  AGENT_PGID="$agent_pgid"
  SIDECAR_PID="$sidecar_pid"

  log_orchestrator "agent_spawned: iteration=$CURRENT_ITERATION agent=$AGENT pid=$AGENT_PID pgid=${AGENT_PGID:-unknown} sidecar_pid=$SIDECAR_PID log=$LOG_FILE"
  log_event "process" "spawned" "iteration=$CURRENT_ITERATION agent_pid=$AGENT_PID agent_pgid=${AGENT_PGID:-unknown} sidecar_pid=$SIDECAR_PID"
}

run_agent_with_watchdog() {
  local agent_exit sidecar_exit

  start_agent_iteration || return $?

  agent_exit=0
  monitor_process_with_heartbeat \
    "$AGENT_PID" \
    "agent iteration=$CURRENT_ITERATION agent=$AGENT" \
    "$LOG_FILE" \
    "$HEARTBEAT_SEC" \
    "$AGENT_IDLE_TIMEOUT_SEC" \
    "$EVENT_LOG" \
    "" \
    "$POST_RESULT_IDLE_SEC" \
    "$AGENT_PID,$SIDECAR_PID" || agent_exit=$?
  stop_stream_sidecar "$SIDECAR_PID"
  sidecar_exit="${STOPPED_SIDECAR_EXIT:-0}"

  if (( sidecar_exit != 0 )); then
    log_orchestrator "sidecar_nonzero_exit: iteration=$CURRENT_ITERATION sidecar_pid=$SIDECAR_PID exit=$sidecar_exit"
    log_event "process" "warning" "iteration=$CURRENT_ITERATION sidecar_pid=$SIDECAR_PID sidecar_exit=$sidecar_exit"
  fi

  log_orchestrator "agent_stream_closed: iteration=$CURRENT_ITERATION agent_pid=$AGENT_PID sidecar_pid=$SIDECAR_PID sidecar_exit=$sidecar_exit"
  log_event "process" "closed" "iteration=$CURRENT_ITERATION agent_pid=$AGENT_PID sidecar_pid=$SIDECAR_PID sidecar_exit=$sidecar_exit"

  return "$agent_exit"
}

echo "Starting Ralph loop: agent=$AGENT, max=$MAX_ITERATIONS"
echo "Sprint: $CURRENT_SPRINT"
echo "Logs: $LOG_DIR"
echo "---"
log_orchestrator "loop_started: agent=$AGENT sprint=$CURRENT_SPRINT max_iterations=$MAX_ITERATIONS resume=$RESUME force_hooks=$FORCE_HOOKS"
log_event "loop" "started" "agent=$AGENT sprint=$CURRENT_SPRINT"

ensure_manifest_schema

if all_chunks_pass_fn; then
  echo "All chunks already complete! Skipping to post-sprint hooks..."
  echo ""
  log_orchestrator "precheck: all_chunks_pass=true"
  log_event "precheck" "ok" "all_chunks_pass=true"

  reconcile_completion_state

  NEXT_SPRINT=$(get_next_sprint)
  if [[ -n "$NEXT_SPRINT" ]]; then
    offer_next_sprint_prompt "$NEXT_SPRINT"
  else
    echo "No next sprint found. Create one with /ralph-sprint"
  fi

  exit 0
fi

START_ITERATION=1
if [[ "$RESUME" == "true" ]]; then
  LAST_ITER=$(jq -r '.iterations // 0' "$MANIFEST_FILE" 2>/dev/null || echo 0)
  if [[ "$LAST_ITER" =~ ^[0-9]+$ ]] && (( LAST_ITER >= 1 )); then
    START_ITERATION=$((LAST_ITER + 1))
  fi
  if (( START_ITERATION > MAX_ITERATIONS )); then
    START_ITERATION=$MAX_ITERATIONS
  fi
fi

for i in $(seq "$START_ITERATION" "$MAX_ITERATIONS"); do
  CURRENT_ITERATION="$i"
  echo "[Iteration $i/$MAX_ITERATIONS]"
  log_orchestrator "iteration_started: $i"
  log_event "iteration" "started" "iteration=$i"

  LOG_FILE="$LOG_DIR/iteration-$i.log"
  SUMMARY_LOG="$LOG_DIR/iteration-$i.summary.log"
  export SUMMARY_LOG

  BEFORE_PASS_COUNT=$(passed_chunk_count)

  set +e
  run_agent_with_watchdog
  AGENT_EXIT=$?
  set -e

  log_orchestrator "agent_done: iteration=$i log=$LOG_FILE exit=$AGENT_EXIT"
  log_event "iteration" "agent_done" "iteration=$i exit=$AGENT_EXIT"

  AFTER_PASS_COUNT=$(passed_chunk_count)
  PASS_DELTA=$((AFTER_PASS_COUNT - BEFORE_PASS_COUNT))

  COMPLETION_SCOPE=$(detect_completion_scope "$LOG_FILE")
  COMPLETION_SIGNAL=false

  if all_chunks_pass_fn; then
    COMPLETION_SIGNAL=true
    log_orchestrator "completion_signal_detected: iteration=$i source=chunks_state"
  elif [[ "$COMPLETION_SCOPE" == "sprint" ]]; then
    COMPLETION_SIGNAL=true
    log_orchestrator "completion_signal_detected: iteration=$i source=marker scope=sprint"
  elif [[ "$COMPLETION_SCOPE" == "chunk" ]] || [[ "$COMPLETION_SCOPE" == "legacy_chunk" ]]; then
    if (( PASS_DELTA > 0 )); then
      COMPLETION_SIGNAL=true
      log_orchestrator "completion_signal_detected: iteration=$i source=marker scope=$COMPLETION_SCOPE delta=$PASS_DELTA"
    else
      log_orchestrator "completion_signal_ignored: iteration=$i source=marker scope=$COMPLETION_SCOPE delta=$PASS_DELTA"
      log_event "completion" "ignored" "iteration=$i scope=$COMPLETION_SCOPE delta=$PASS_DELTA"
    fi
  fi

  if [[ "$COMPLETION_SIGNAL" == "true" ]]; then
    echo ""
    echo "=========================================="
    echo "Chunk completed in iteration $i"
    echo "=========================================="

    if [[ "${RALPH_AUTO_COMMIT:-false}" == "true" ]] && git -C "$PROJECT_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
      echo "Refusing RALPH_AUTO_COMMIT=true; use RALPH_AUTO_COMMIT=I_ACCEPT_GIT_ADD_ALL to acknowledge broad staging"
      exit 14
    fi
    if [[ "${RALPH_AUTO_COMMIT:-false}" == "I_ACCEPT_GIT_ADD_ALL" ]] && git -C "$PROJECT_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
      git -C "$PROJECT_ROOT" add -A
      git -C "$PROJECT_ROOT" commit -m "ralph: chunk completed (iteration $i)" -q 2>/dev/null || true
    fi

    LAST_COMMIT=$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")
    LAST_MSG=$(git -C "$PROJECT_ROOT" log -1 --format="%s" 2>/dev/null || echo "unknown")
    CHUNK_ID="$AFTER_PASS_COUNT"
    manifest_update \
      --arg hash "$LAST_COMMIT" --arg msg "$LAST_MSG" --argjson chunk "$CHUNK_ID" --argjson iter "$i" \
      '.commits += [{"hash": $hash, "message": $msg, "chunk_id": $chunk, "iteration": $iter}] | .iterations = $iter' \
      || true

    if all_chunks_pass_fn; then
      echo "All chunks complete! Sprint finished."
      echo ""
      log_orchestrator "sprint_chunks_complete: iteration=$i"
      log_event "sprint" "chunks_done" "iteration=$i"

      reconcile_completion_state

      NEXT_SPRINT=$(get_next_sprint)
      if [[ -n "$NEXT_SPRINT" ]]; then
        offer_next_sprint_prompt "$NEXT_SPRINT"
      else
        echo "No next sprint found. Create one with /ralph-sprint"
      fi

      trap - EXIT
      exit 0
    fi

    echo "Chunk done. Continuing to next chunk with fresh context..."
    sleep 2
    continue
  fi

  if grep -q "<blocked>" "$LOG_FILE"; then
    REASON=$(sed -n 's/.*<blocked>\(.*\)<\/blocked>.*/\1/p' "$LOG_FILE" | head -1)
    REASON="${REASON:-unknown}"
    echo "Agent blocked: $REASON"
    log_orchestrator "blocked: iteration=$i reason=$REASON"
    log_event "iteration" "blocked" "iteration=$i reason=$REASON"
    exit 14
  fi

  manifest_update --argjson iter "$i" '.iterations = (if (.iterations // 0) < $iter then $iter else .iterations end)' || true

  if [[ "${RALPH_AUTO_COMMIT:-false}" == "I_ACCEPT_GIT_ADD_ALL" ]] && git -C "$PROJECT_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
    git -C "$PROJECT_ROOT" add -A
    git -C "$PROJECT_ROOT" commit -m "ralph: iteration $i" --allow-empty -q 2>/dev/null || true
  fi

  echo "Iteration $i complete, continuing..."
  log_orchestrator "iteration_complete: $i"
  log_event "iteration" "complete" "iteration=$i"
  sleep 2
done

echo "Max iterations ($MAX_ITERATIONS) reached without completion"
log_orchestrator "max_iterations_reached: $MAX_ITERATIONS"
log_event "loop" "max_iterations_reached" "max=$MAX_ITERATIONS"
exit 2
