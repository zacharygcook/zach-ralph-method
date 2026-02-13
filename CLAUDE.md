# Ralph Method - Setup Assistant

You are a setup assistant for configuring autonomous coding using the Ralph Wiggum loop.

## What You're Setting Up

The Ralph method wraps an agent CLI in a bash loop that:
1. Runs the agent with a prompt file
2. Blocks exit via stop hook if task incomplete
3. Re-injects the same prompt (files persist, context resets)
4. Continues until completion promise is found or max iterations hit

## Before You Start

Ask the user for:
1. **Target project path** - absolute path to the repo to configure
2. **Mode** - monorepo (single repo) or multi-repo (API + frontend)
3. **Agent harness** - which CLI to use (claude, codex, amp, opencode, droid)
4. **Task description** - what the autonomous session should accomplish
5. **Max iterations** - safety limit (recommend 20-50 for most tasks)

## Template Modes

| Mode | Use Case | Templates |
|------|----------|-----------|
| **monorepo** | Single git repo | `templates/monorepo/` |
| **multi-repo** | API + Frontend (separate repos) | `templates/multi-repo/` |

Shared formatters live in `templates/shared/`.

## The Flow

```
SPEC/GOAL ──▶ PLAN ──▶ CHUNK ──▶ RUN
  (you)    (agent+you) (agent)  (loop)
```

1. **SPEC/GOAL** - Your specification or goal definition
2. **PLAN** - Deep planning mode → `IMPLEMENTATION_PLAN.md` (60-70 lines)
3. **CHUNK** - Break into `chunks.json` based on plan
4. **RUN** - Execute loop, mark chunks as passed, repeat

### Input Types

| File | Use Case |
|------|----------|
| `SPEC.md` | Full MVP specification (greenfield) |
| `GOAL.md` | Single goal (bugfix, feature, refactor) |
| `GOALS.md` | Multiple related goals in one sprint |

See `templates/GOAL.md.template` and `templates/GOALS.md.template` for formats.

## Directory Structure

```
<project>/.ralph/
├── config.env                  # Agent, iterations, CURRENT_SPRINT, timeouts
├── loop.sh                     # Bash loop script
├── status.sh                   # Operator status command
├── lib/
│   └── ralph-common.sh         # Shared helpers (locking, heartbeat, events)
├── format-stream.py            # Output formatter (Claude)
├── format-codex-stream.py      # Output formatter (Codex)
├── hooks/
│   ├── post-sprint.sh          # Hook orchestrator (state files, lock recovery)
│   ├── review.sh               # Code review (preflight, events)
│   ├── document.sh             # Documentation (preflight, events)
│   └── test.sh                 # Test suite (phase-aware, resumable)
├── prompts/
│   ├── review.md               # Code review prompt template
│   ├── document.md             # Documentation prompt template
│   └── test.md                 # Test generation prompt template
├── logs/
│   └── <sprint>/run-<timestamp>/
│       ├── orchestrator.log        # Timestamped orchestrator events
│       ├── events.jsonl            # Structured event stream
│       ├── iteration-N.log         # Full JSON log
│       └── iteration-N.summary.log # Human-readable summary
└── sprints/
    └── 1-sprint-name/
        ├── prompt.md           # Sprint-specific prompt
        ├── README.md           # Sprint goal (3-4 lines)
        ├── IMPLEMENTATION_PLAN.md
        ├── relevant-specs.md
        ├── chunks.json
        └── manifest.json       # Sprint tracking (phase, hooks, commits)
```

Set `CURRENT_SPRINT=1-sprint-name` in config.env to select active sprint.

## Post-Sprint Hooks

After all chunks pass, the loop runs hooks for automation. Each hook has:
- **Dependency preflight** - checks required commands exist before running
- **Lock-protected manifest** - prevents concurrent writes from corrupting state
- **State files** - `.hook-<name>.state.json` tracks pid, status, heartbeat
- **Stale recovery** - auto-detects interrupted hooks stuck in "running" state
- **Heartbeat monitoring** - periodic event logging during execution
- **Marker idempotency** - `.hook-<name>.done` files prevent re-running completed hooks

**Test hook phases** (each resumable independently):
1. `generate_tests` - Agent creates test files
2. `verify_backend_tests` - Runs generated tests
3. `run_e2e` - Playwright e2e (auto-skipped when no frontend artifacts)

**Manifest tracking**: Each sprint gets `manifest.json` tracking phase, hooks status/reason, test phases, commits, and timestamps.

## Key Concepts

**IMPLEMENTATION_PLAN.md** - Created in planning mode before chunking:
- Execution order and why
- Dependencies between pieces
- Patterns to follow
- Risks/gotchas

**chunks.json** - Sequenced tasks with acceptance criteria, each completable in one context window.

See `docs/sprint-structure.md` for ASCII diagrams and full details.

## Execution Workflow

1. Enter planning mode → create `IMPLEMENTATION_PLAN.md`
2. Create `chunks.json` based on plan
3. Run `./.ralph/loop.sh` (or `./loop.sh --resume` to continue from last iteration)
4. Agent completes chunk → commits → sets `passes: true` → outputs `RALPH_CHUNK_COMPLETE`
5. Loop validates state-delta (chunk count must actually increase) before accepting
6. Loop auto-continues to next chunk (fresh context window per iteration)
7. Loop exits when: all chunks pass, agent blocked, or max iterations reached
8. Post-sprint hooks run automatically (review, docs, tests)

**CLI flags**:
- `--resume` - Continue from last completed iteration (reads from manifest)
- `--force-hooks` - Re-run post-sprint hooks even if already completed

**Auto-continue**: No manual intervention between chunks. Each chunk gets fresh context. Agent updates chunks.json itself.

## Git Commits

**Agent commits after each chunk** with a descriptive message, then outputs the completion marker. The loop has backup commits but they become no-ops if agent already committed.

**Completion sequence**:
1. Complete chunk's acceptance criteria
2. `git add -A && git commit -m "Add X feature"` (descriptive message)
3. Update chunks.json: set `passes: true`
4. Output: `<promise>RALPH_CHUNK_COMPLETE</promise>`

**Scoped completion markers**:
- `RALPH_CHUNK_COMPLETE` - Current chunk is done (normal case)
- `RALPH_SPRINT_COMPLETE` - ALL chunks are done, sprint finished
- `RALPH_COMPLETE` - Legacy marker (treated as chunk-level, still recognized)

**State-delta validation**: The loop checks that the passed chunk count actually increased before accepting a marker-based completion signal. This prevents false positives from marker-only emissions.

**Commit rules for prompts**:
- No "Generated with Claude Code" lines
- No "Co-Authored-By" lines
- Clean, descriptive messages only

## Agent Flags

| Agent | Autonomous Flag |
|-------|-----------------|
| claude | `--dangerously-skip-permissions` (sandbox!) |
| codex | `exec --yolo` (max autonomy, no sandbox) |
| amp | `--autonomous` |
| opencode | `--auto` |
| droid | `exec --auto high` |

**Codex notes:**
- Must use `codex exec` subcommand for non-interactive operation (`codex` alone needs TTY)
- `--yolo` (alias: `--dangerously-bypass-approvals-and-sandbox`) = no sandbox, no approvals
- `--full-auto` = workspace-write sandbox + on-request approvals (less autonomous)
- Prompts passed as argument or via stdin with `-`, not `--prompt-file`

## Claude Code: Real-Time Output

The `-p` flag puts Claude in non-interactive mode (no TUI). Use `--output-format=stream-json` for real-time visibility:

```bash
claude --dangerously-skip-permissions -p "$(cat prompt.md)" \
  --output-format=stream-json --include-partial-messages --verbose 2>&1 \
  | tee "$LOG_FILE" | python3 format-stream.py
```

- `--output-format=stream-json` - Streams JSON events (tool calls, text)
- `--include-partial-messages` - Shows text token-by-token
- `--verbose` - Required for stream-json

Pipe through `format-stream.py` (in templates/) for colored output. Log file gets raw JSON (grep still works).

## Heartbeat & Monitoring

The loop uses heartbeat-first orchestration — long-running operations are allowed by default, with optional idle timeouts for safety.

**Event log**: Each run produces `events.jsonl` with structured JSON events (heartbeats, completions, failures, timeouts).

**Orchestrator log**: Human-readable timestamped log at `orchestrator.log`.

**Status command**: Check sprint state at any time:
```bash
.ralph/status.sh                    # Uses CURRENT_SPRINT from config.env
.ralph/status.sh 3-api-integration  # Specific sprint
```

Shows: manifest phase, iteration count, hook statuses, test phases, latest run info, heartbeat age, hook pid liveness.

**Signal handling**: INT/TERM signals trigger clean reconciliation — manifest is finalized and hooks run if chunks are complete.

## Idle Timeout Rollout

All idle timeouts default to disabled (`0`). Enable them in stages via `config.env`:

| Stage | What's Protected | Key Setting |
|-------|-----------------|-------------|
| 1 (baseline) | Nothing - heartbeats only | All `*_TIMEOUT_SEC=0` |
| 2 | Hooks only | `HOOK_IDLE_TIMEOUT_SEC=7200` |
| 3 | + Backend tests | `BACKEND_TEST_IDLE_TIMEOUT_SEC=3600` |
| 4 | + E2E tests | `E2E_IDLE_TIMEOUT_SEC=10800` |
| 5 | + Agent iterations | `AGENT_IDLE_TIMEOUT_SEC=14400` |

Keep `AGENT_IDLE_TIMEOUT_SEC=0` unless you hit "result printed but loop stuck" failures.

## Common Gotchas

**Docker + node_modules**: Stop containers before `yarn install` - containers create root-owned dirs.
```bash
docker compose down
sudo rm -rf node_modules */node_modules packages/*/node_modules
yarn install
docker compose up -d
```

**Environment setup**: Verify `.env` vars match what code expects (check validation files).

## Setup Checklist

- [ ] Git initialized, on experiment branch
- [ ] `.env` configured (check against validation file)
- [ ] Docker services running
- [ ] Dependencies installed
- [ ] Created `.ralph/sprints/` structure
- [ ] Created `IMPLEMENTATION_PLAN.md` (planning mode)
- [ ] Created `chunks.json` based on plan
- [ ] Curated context in `relevant-specs.md`
- [ ] Tested one manual iteration

## Multi-Repo Mode

For projects with separate API and Frontend repos:

```
project-parent/
├── .ralph/           # Ralph lives here (no .git)
│   ├── config.env    # REPOS="api frontend"
│   └── sprints/
├── api/              # Separate git repo
│   └── CLAUDE.md
└── frontend/         # Separate git repo
    └── CLAUDE.md
```

**Key differences from monorepo:**
- Git commands must `cd` into each repo
- Manifest tracks commits per-repo
- Chunks have `"repo": "api|frontend|both"` field
- Hooks aggregate across repos

Use `templates/multi-repo/` for these projects.

## Documentation

- `docs/sprint-structure.md` - How to organize sprints and chunks
- `templates/monorepo/` - Single-repo templates
- `templates/multi-repo/` - Multi-repo templates
- `templates/shared/` - Formatters and shared library (used by both modes)
- `templates/GOAL.md.template` - Single goal format
- `templates/GOALS.md.template` - Multiple goals format

## References

- [frankbria/ralph-claude-code](https://github.com/frankbria/ralph-claude-code)
- [vercel-labs/ralph-loop-agent](https://github.com/vercel-labs/ralph-loop-agent)

## Repository Structure

This repo tracks Ralph method tooling only. Project repos (like `blackbird/`) are cloned here for autonomous coding but tracked in their own git repos.

**Tracked**: `docs/`, `templates/`, `CLAUDE.md`, `AGENTS.md`, `README.md`
**Ignored**: All project folders, logs, notes

---

Keep `CLAUDE.md` and `AGENTS.md` in sync.
