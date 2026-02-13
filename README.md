# The Ralph Method

```
                          "I'm helping!"
                               |
    ┌──────────────────────────┴──────────────────────────┐
    │                                                      │
    │      ┌─────────┐      ┌─────────┐      ┌─────────┐  │
    │      │  SPEC   │ ───▶ │  PLAN   │ ───▶ │  CHUNK  │  │
    │      │ (you)   │      │(agent+u)│      │ (agent) │  │
    │      └─────────┘      └─────────┘      └─────────┘  │
    │                                              │       │
    │                                              ▼       │
    │   ╔═══════════════════════════════════════════════╗   │
    │   ║               THE LOOP                        ║   │
    │   ║  ┌────────────────────────────────────────┐   ║   │
    │   ║  │                                        │   ║   │
    │   ║  │   prompt ──▶ agent ──▶ check ──┐       │   ║   │
    │   ║  │      ▲                         │       │   ║   │
    │   ║  │      │    CHUNK_COMPLETE?      │       │   ║   │
    │   ║  │      │                         │       │   ║   │
    │   ║  │      │   NO ◄─────────────┘    │       ║   │
    │   ║  │      │   (fresh context)       │       ║   │
    │   ║  │      └─────────────────────────┘       ║   │
    │   ║  │              YES ▼                     │   ║   │
    │   ║  │       ┌──────────────────┐             │   ║   │
    │   ║  │       │  state-delta ok? │             │   ║   │
    │   ║  │       └────────┬─────────┘             │   ║   │
    │   ║  │            YES ▼                       │   ║   │
    │   ║  │     more chunks? ──NO──▶ HOOKS ──▶ ✓  │   ║   │
    │   ║  │         │                              │   ║   │
    │   ║  │        YES (next chunk, fresh ctx)     │   ║   │
    │   ║  └────────────────────────────────────────┘   ║   │
    │   ╚═══════════════════════════════════════════════╝   │
    │                                                      │
    └──────────────────────────────────────────────────────┘
```

## What is the Ralph Method?

A bash loop that wraps an AI coding agent, re-prompting until the task is complete. Named after Ralph Wiggum's relentless optimism - the agent keeps trying until it succeeds.

**The core insight**: Files persist between iterations, but context resets. Progress accumulates in code and git commits while each iteration starts fresh with full context capacity.

## Why It Works

```
Iteration 1: Agent reads codebase, implements chunk 1, commits
             → outputs RALPH_CHUNK_COMPLETE → state-delta validated
Iteration 2: Fresh context, reads codebase, implements chunk 2, commits
             → outputs RALPH_CHUNK_COMPLETE → state-delta validated
Iteration 3: Fresh context, implements chunk 3, commits
             → outputs RALPH_CHUNK_COMPLETE + RALPH_SPRINT_COMPLETE
             → post-sprint hooks run (review, docs, tests)
```

Each iteration:
- Starts with a clean context window (fresh agent process)
- Reads the current state from files (not memory)
- Makes progress on the next incomplete chunk
- Commits, marks chunk as passed, outputs completion marker
- Loop validates state actually changed, then continues

## Quick Start

1. Clone this repo
2. In your target project, run `/ralph-init` (or manually copy templates)
3. Create `IMPLEMENTATION_PLAN.md` in planning mode
4. Create `chunks.json` based on plan
5. Run `.ralph/loop.sh`

See `docs/` for detailed setup and `templates/` for starter files.

## Supported Agents

| Agent | Command | Autonomous Flag |
|-------|---------|-----------------|
| Claude Code | `claude` | `--dangerously-skip-permissions` |
| OpenAI Codex | `codex` | `exec --yolo` |
| Amp | `amp` | `--autonomous` |
| OpenCode | `opencode` | `--auto` |
| Droid (Factory) | `droid` | `exec --auto high` |

## The Hardened Loop

The loop does more than just re-prompt. It's a production-grade orchestrator:

```
┌──────────────────────────────────────────────────────────────┐
│                     LOOP ARCHITECTURE                         │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  config.env ──▶ loop.sh ◄── lib/ralph-common.sh              │
│                    │                                          │
│    ┌───────────────┼───────────────┐                          │
│    ▼               ▼               ▼                          │
│  AGENT          WATCHDOG       SIGNALS                        │
│  process        ├ heartbeat    ├ INT/TERM → reconcile         │
│  (claude,       ├ idle check   └ EXIT → finalize manifest     │
│   codex, ...)   └ events.jsonl                                │
│    │                                                          │
│    ▼                                                          │
│  COMPLETION DETECTION                                         │
│  ├ RALPH_CHUNK_COMPLETE  → validate state-delta → continue    │
│  ├ RALPH_SPRINT_COMPLETE → skip validation → hooks            │
│  ├ RALPH_COMPLETE        → (legacy, same as chunk)            │
│  └ <blocked>             → exit for human                     │
│                                                               │
│  ALL CHUNKS PASS                                              │
│    │                                                          │
│    ▼                                                          │
│  POST-SPRINT HOOKS (sequential, resumable)                    │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐                  │
│  │  review  │──▶│   docs   │──▶│  tests   │                  │
│  │ (codex)  │   │ (claude) │   │ (claude) │                  │
│  └──────────┘   └──────────┘   └──────────┘                  │
│  Each hook: preflight → lock → execute → state file → commit  │
│                                                               │
│  CLI: --resume (continue last run)                            │
│       --force-hooks (re-run completed hooks)                  │
│  Status: .ralph/status.sh                                     │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Key Features

- **State-delta validation** — Loop verifies chunk pass count actually increased before accepting a completion signal. Prevents false positives.
- **Heartbeat monitoring** — Periodic events prove the agent is alive. Optional idle timeout kills stuck processes.
- **Signal traps** — INT/TERM/EXIT trigger reconciliation: manifest finalized, hooks run if chunks complete.
- **Lock-protected manifests** — `mkdir`-based locking prevents concurrent jq corruption.
- **Stale hook recovery** — Detects hooks stuck in "running" after crashes, auto-marks as failed.
- **Resumable test phases** — Test hook runs 3 independent phases: generate, verify backend, run e2e.

## Post-Sprint Pipeline

```
┌─────────────────────────────────────────────────────────┐
│              POST-SPRINT HOOKS                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────┐                  │
│  │ 1. REVIEW (codex)                 │                  │
│  │    git diff start..end            │                  │
│  │    → fix ALL issues               │                  │
│  │    → REVIEW.md + commit           │                  │
│  └──────────────┬─────────────────────┘                  │
│                 ▼                                        │
│  ┌────────────────────────────────────┐                  │
│  │ 2. DOCUMENT (claude)              │                  │
│  │    Read chunks + artifacts        │                  │
│  │    → Sprint summary               │                  │
│  │    → Update main docs             │                  │
│  │    → commit                       │                  │
│  └──────────────┬─────────────────────┘                  │
│                 ▼                                        │
│  ┌────────────────────────────────────┐                  │
│  │ 3. TEST (claude) — 3 phases       │                  │
│  │    ┌─────────────────────────┐    │                  │
│  │    │ a. generate_tests       │    │                  │
│  │    │ b. verify_backend_tests │    │                  │
│  │    │ c. run_e2e              │    │                  │
│  │    └─────────────────────────┘    │                  │
│  │    Each phase: resumable,         │                  │
│  │    tracked in manifest            │                  │
│  └────────────────────────────────────┘                  │
│                                                          │
│  State tracking per hook:                                │
│  ├ .hook-<name>.state.json (pid, status, heartbeat)      │
│  ├ Lock files prevent double-runs                        │
│  └ Stale "running" auto-recovered on restart             │
│                                                          │
│  manifest.json phases:                                   │
│    running → chunks_done → hooks_done                    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Completion Markers

The loop recognizes three scoped markers (checked in priority order):

| Marker | Scope | State-Delta | When to Use |
|--------|-------|-------------|-------------|
| `RALPH_SPRINT_COMPLETE` | Sprint | Skipped | All chunks pass |
| `RALPH_CHUNK_COMPLETE` | Chunk | Required | Standard chunk completion |
| `RALPH_COMPLETE` | Chunk (legacy) | Required | Backward compat only |

```
<promise>RALPH_CHUNK_COMPLETE</promise>    ← after each chunk
<promise>RALPH_SPRINT_COMPLETE</promise>   ← when ALL chunks pass
<blocked>Reason here</blocked>             ← need human help
```

## Real-Time Visibility

Claude Code's `-p` flag enables non-interactive mode. Add `--output-format=stream-json` for real-time streaming:

```bash
claude --dangerously-skip-permissions -p "$(cat prompt.md)" \
  --output-format=stream-json --verbose 2>&1 \
  | tee "$LOG_FILE" | python3 format-stream.py
```

See `templates/shared/format-stream.py` for colored terminal output while preserving full logs.

## Repository Structure

```
ralph-method/
├── README.md                    # You are here
├── CLAUDE.md                    # Context for Claude Code
├── AGENTS.md                    # Context for other agents
├── docs/
│   ├── sprint-structure.md      # Workflow and ASCII diagrams
│   ├── definition-of-terms.md   # Precise definitions
│   ├── multi-repo-setup.md      # Multi-repo guide
│   └── migration-report.md      # Hardening changelog
└── templates/
    ├── shared/
    │   ├── ralph-common.sh.template    # Shared library (locking, heartbeat, events)
    │   ├── format-stream.py            # Claude stream formatter
    │   └── format-codex-stream.py      # Codex stream formatter
    ├── monorepo/
    │   ├── config.env.template
    │   ├── loop.sh.template
    │   ├── status.sh.template
    │   ├── prompt.md.template
    │   ├── hooks/                      # post-sprint, review, document, test
    │   └── prompts/                    # review, document, test prompts
    ├── multi-repo/
    │   ├── (same as monorepo + CLAUDE.md.parent.template)
    │   └── (hooks adapted for per-repo git operations)
    ├── GOAL.md.template
    └── GOALS.md.template
```

Project repos (like `blackbird/`) are cloned here but tracked in their own git repos.

## Idle Timeout Rollout

All timeouts disabled by default (heartbeat-first: observe, then opt-in kill):

| Stage | Setting | Effect |
|-------|---------|--------|
| 0 | `AGENT_IDLE_TIMEOUT_SEC=0` | Observe only (heartbeat logs) |
| 1 | `AGENT_IDLE_TIMEOUT_SEC=600` | Kill agent after 10min idle |
| 2 | `HOOK_IDLE_TIMEOUT_SEC=300` | Kill hooks after 5min idle |
| 3 | `BACKEND_TEST_IDLE_TIMEOUT_SEC=180` | Kill test runs after 3min idle |
| 4 | `E2E_IDLE_TIMEOUT_SEC=300` | Kill e2e tests after 5min idle |

## Credits & References

- [frankbria/ralph-claude-code](https://github.com/frankbria/ralph-claude-code) - Original inspiration
- [vercel-labs/ralph-loop-agent](https://github.com/vercel-labs/ralph-loop-agent) - Vercel's implementation
- [Geoffrey Huntley's technique](https://ghuntley.com/ralph/) - The OG Ralph method

---

*This is a living document, refined through real autonomous coding sessions.*
