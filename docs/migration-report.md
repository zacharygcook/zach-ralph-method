# Migration Report: Blackbird Hardening → Canonical Templates

## v0.5.0 — Evidence-gated completion

- Adds required `RALPH_CHUNK_VALIDATION_COMMAND` and final `RALPH_SPRINT_VALIDATION_COMMAND` gates.
- Accepts only one next sequential chunk transition per iteration and rejects/resets invalid claims.
- Requires commit evidence from the chunk-owned repository, or every repository for `all`/`both`.
- Records validation attempts, exit codes, timestamps, and logs; failures feed the next context through `SCRATCHPAD.md`.
- Replaces fictional test-generation phases with an honest final `validation` hook while migrating old `hooks.tests` state.
- Keeps `RALPH_TEST_COMMAND` as a deprecated sprint-validation fallback; it never silently becomes a per-chunk gate.
- Makes failed final validation return nonzero while preserving resumable `chunks_done` state.

**Date**: 2026-02-12
**Source**: `blackbird/.ralph/` (production-hardened loop)
**Target**: `zach-ralph-method/templates/` (canonical templates)

---

## What Changed

### 1. New Files Created

| File | Purpose |
|------|---------|
| `templates/shared/ralph-common.sh.template` | Shared library: locking, heartbeat, event logging, manifest helpers, process monitoring |
| `templates/monorepo/status.sh.template` | Operator status command (manifest phase, hooks, heartbeat age, events) |
| `templates/multi-repo/status.sh.template` | Multi-repo status command (adds per-repo commit range display) |

### 2. Templates Rewritten (Major)

| Template | Key Changes |
|----------|-------------|
| `monorepo/loop.sh.template` | Sources `ralph-common.sh`, heartbeat watchdog, scoped completion detection, state-delta validation, signal traps with reconciliation, `--resume`/`--force-hooks` flags, structured event logging, orchestrator log |
| `multi-repo/loop.sh.template` | Same as monorepo + per-repo commit tracking, `backup_commit_all_repos()`, `finalize_manifest_repos()` |
| `monorepo/hooks/post-sprint.sh.template` | Lock-protected manifest, per-hook state files, stale recovery, heartbeat monitoring, normalized exit reasons, `FORCE_HOOKS` support |
| `multi-repo/hooks/post-sprint.sh.template` | Same as monorepo |
| `monorepo/hooks/test.sh.template` | 3-phase model (generate_tests, verify_backend_tests, run_e2e), per-phase manifest tracking, monitored commands with idle timeouts, e2e auto-skip |
| `multi-repo/hooks/test.sh.template` | Same phases + per-repo test verification, multi-repo e2e detection |
| `monorepo/hooks/review.sh.template` | Sources `ralph-common.sh`, dependency preflight, structured event logging, end_commit fallback |
| `multi-repo/hooks/review.sh.template` | Same + multi-repo diff range |
| `monorepo/hooks/document.sh.template` | Sources `ralph-common.sh`, dependency preflight, structured event logging |
| `multi-repo/hooks/document.sh.template` | Same + multi-repo awareness |

### 3. Templates Updated (Minor)

| Template | Changes |
|----------|---------|
| `monorepo/config.env.template` | Added: `HEARTBEAT_SEC`, `AGENT_IDLE_TIMEOUT_SEC`, `HOOK_HEARTBEAT_SEC`, `HOOK_IDLE_TIMEOUT_SEC`, `BACKEND_TEST_IDLE_TIMEOUT_SEC`, `E2E_IDLE_TIMEOUT_SEC`, `RALPH_INTERACTIVE`, `RALPH_INTERACTIVE_TIMEOUT_SEC` |
| `multi-repo/config.env.template` | Same additions |
| `monorepo/prompt.md.template` | `RALPH_COMPLETE` → `RALPH_CHUNK_COMPLETE`, added scoped marker documentation |
| `multi-repo/prompt.md.template` | Same changes |

### 4. Docs Updated

| File | Changes |
|------|---------|
| `CLAUDE.md` | Directory structure, post-sprint hooks, execution workflow, git commits (scoped markers), new "Heartbeat & Monitoring" section, new "Idle Timeout Rollout" section |
| `AGENTS.md` | Directory structure, execution workflow, completion sequence, and historical Codex adapter guidance later superseded by v0.6 harness tests |
| `docs/sprint-structure.md` | `RALPH_COMPLETE` → `RALPH_CHUNK_COMPLETE`, scoped markers note, state-delta validation, updated directory structure |
| `docs/definition-of-terms.md` | Three scoped marker subsections, new terms: Heartbeat, Idle Timeout, Manifest Phase, State-Delta Validation, Reconciliation |

### 5. Skills Updated (external: `~/sync/claude-config/`)

| Skill/Command | Changes |
|---------------|---------|
| `ralph-init` | Updated structure to include `lib/ralph-common.sh`, `status.sh`; v2→v3 hardening section with all new patterns |
| `ralph-sprint` | `RALPH_COMPLETE` → `RALPH_CHUNK_COMPLETE` everywhere; removed SCRATCHPAD references; updated completion protocol with `RALPH_SPRINT_COMPLETE`; v3 hardening section |
| `ralph-status` | Added manifest/hook/test-phase display; hook state file checks (pid liveness); v2→v3 hardening section with events.jsonl |
| `ralph-chunk` | Added completion markers section (scoped markers, state-delta); removed SCRATCHPAD reference |
| `ralph-spec-breakdown` | Updated post-sprint automation section; added completion markers section; removed SCRATCHPAD reference |
| `ralph-review-sprint` | Removed SCRATCHPAD check; added scoped marker verification; expanded hardened orchestration checks to v3 (state files, test phases, shared library, status.sh) |

---

## What Was Intentionally NOT Ported

| Item | Reason |
|------|--------|
| `SCRATCHPAD.md` per-sprint files | Removed in commit 5b88f83 as unnecessary overhead. Git history and chunk descriptions provide sufficient cross-iteration context. |
| Project-specific test paths (e.g., `backend/tests/sprint/`) | Templates use generic `tests/sprint/` pattern. Project-specific paths belong in project config, not canonical templates. |
| Blackbird's hardcoded repo names (`api`, `frontend`) | Multi-repo templates use `REPOS` env var from config.env. |
| `format-stream.py` / `format-codex-stream.py` updates | These formatters were already present in `templates/shared/` and didn't need hardening changes. |
| Codex-specific `--model` flag | Historical `exec --yolo` behavior from `bcbd9d0` was superseded in v0.6 by an explicit model and the current documented bypass flag. |
| Blackbird's `docs/ralph-orchestrator-hardening-summary.md` | This was project-specific documentation. The patterns it describes are now encoded in the canonical templates and docs. |

---

## Compatibility Notes

### For Existing Ralph Setups

1. **Backward compatible**: Legacy `RALPH_COMPLETE` marker is still recognized (treated as chunk-level with state-delta validation). No existing prompts need immediate changes.

2. **New dependency**: All templates now source `lib/ralph-common.sh`. Existing setups must create `.ralph/lib/ralph-common.sh` from the shared template, or loop.sh will fail at startup.

3. **Config.env additions**: New env vars default to safe values (all timeouts disabled = `0`). Existing config.env files work without changes, but won't benefit from new features until vars are added.

4. **Hook state files**: Hooks now use `.hook-<name>.state.json` instead of `.hook-<name>.done` marker files. Old marker files are ignored. Hooks will re-run on first execution after migration, which is safe (they're idempotent).

5. **Manifest schema expansion**: `manifest.json` now expects `hooks.tests.phases` for test phase tracking. Existing manifests without this field work fine — phases default to `pending`.

### Migration Path

For projects already using Ralph:

```bash
# 1. Copy shared library
mkdir -p .ralph/lib
cp ~/Personal/zach-ralph-method/templates/shared/ralph-common.sh.template .ralph/lib/ralph-common.sh

# 2. Copy status command (pick your mode)
cp ~/Personal/zach-ralph-method/templates/monorepo/status.sh.template .ralph/status.sh
# OR
cp ~/Personal/zach-ralph-method/templates/multi-repo/status.sh.template .ralph/status.sh

# 3. Make executable
chmod +x .ralph/lib/ralph-common.sh .ralph/status.sh

# 4. Add new env vars to config.env (all optional, safe defaults)
cat >> .ralph/config.env << 'EOF'

# Heartbeat & monitoring (added v3)
HEARTBEAT_SEC=30
AGENT_IDLE_TIMEOUT_SEC=0
HOOK_HEARTBEAT_SEC=30
HOOK_IDLE_TIMEOUT_SEC=0
BACKEND_TEST_IDLE_TIMEOUT_SEC=0
E2E_IDLE_TIMEOUT_SEC=0
RALPH_INTERACTIVE=false
RALPH_INTERACTIVE_TIMEOUT_SEC=30
EOF

# 5. Update loop.sh and hooks from latest templates
# (diff first to check for project-specific customizations)
```

### Idle Timeout Rollout Stages

| Stage | Setting | Behavior |
|-------|---------|----------|
| 0 (default) | `AGENT_IDLE_TIMEOUT_SEC=0` | Observe only (heartbeat logs, no kills) |
| 1 | `AGENT_IDLE_TIMEOUT_SEC=600` | Kill agent after 10min idle |
| 2 | `HOOK_IDLE_TIMEOUT_SEC=300` | Also kill hooks after 5min idle |
| 3 | `BACKEND_TEST_IDLE_TIMEOUT_SEC=180` | Kill test runs after 3min idle |
| 4 | `E2E_IDLE_TIMEOUT_SEC=300` | Kill e2e tests after 5min idle |

---

## Audit Checklist

| # | Item | Status |
|---|------|--------|
| 1 | Scoped completion markers (RALPH_CHUNK_COMPLETE, RALPH_SPRINT_COMPLETE, legacy RALPH_COMPLETE) | Ported |
| 2 | State-delta validation (chunk pass count must increase) | Ported |
| 3 | Heartbeat-first orchestration with structured event logs | Ported |
| 4 | Stale "running" hook recovery | Ported |
| 5 | Lock-protected manifest updates (mkdir-based locking) | Ported |
| 6 | Explicit test-hook phases with resumability | Ported |
| 7 | Interactive prompt gating with timeout | Ported |
| 8 | `--resume` and `--force-hooks` CLI flags | Ported |
| 9 | Operator `status` command | Ported |
| 10 | Idle timeout env vars (disabled by default) | Ported |
| 11 | Shared library (`ralph-common.sh`) for code reuse | Created |
| 12 | Signal traps (INT/TERM/EXIT) with reconciliation | Ported |
| 13 | Process monitoring (`monitor_process_with_heartbeat`) | Ported |
| 14 | Zombie-safe process check (`jobs -pr` on macOS) | Ported |
| 15 | Orchestrator log with timestamps | Ported |
| 16 | Per-hook state files with pid tracking | Ported |
| 17 | `ralph-init` skill updated | Audited |
| 18 | `ralph-sprint` skill updated | Audited |
| 19 | `ralph-status` skill updated | Audited |
| 20 | `ralph-chunk` skill updated | Audited |
| 21 | `ralph-spec-breakdown` skill updated | Audited |
| 22 | `ralph-review-sprint` command updated | Audited |
| 23 | CLAUDE.md updated | Audited |
| 24 | AGENTS.md updated | Audited |
| 25 | docs/sprint-structure.md updated | Audited |
| 26 | docs/definition-of-terms.md updated | Audited |
| 27 | SCRATCHPAD.md references removed (per commit 5b88f83) | Cleaned |
| 28 | Codex flag corrected to `exec --yolo` at the time; superseded by v0.6 adapter validation | Historical |
