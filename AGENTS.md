# Ralph Method - Agent Reference

Setup assistant for configuring autonomous coding using the Ralph Wiggum loop.

## What You're Setting Up

The Ralph method wraps an agent CLI in a bash loop that:
1. Runs the agent with a prompt file
2. Blocks exit via stop hook if task incomplete
3. Re-injects the same prompt (files persist, context resets)
4. Continues until completion promise is found or max iterations hit

## Before You Start

Ask the user for:
1. **Target project path** - absolute path to the repo to configure
2. **Agent harness** - which CLI to use (claude, codex, amp, opencode, droid)
3. **Task description** - what the autonomous session should accomplish
4. **Max iterations** - safety limit (recommend 20-50 for most tasks)

## The Flow

```
SPEC ──▶ PLAN ──▶ CHUNK ──▶ RUN
(you)   (agent+you) (agent)  (loop)
```

1. **SPEC** - Your detailed specification (already exists)
2. **PLAN** - Deep planning mode → `IMPLEMENTATION_PLAN.md` (60-70 lines)
3. **CHUNK** - Break into `chunks.json` based on plan
4. **RUN** - Execute loop, mark chunks as passed, repeat

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

After all chunks pass, the loop runs hooks for automation:

```
.ralph/
├── hooks/
│   ├── post-sprint.sh      # Orchestrator (runs all hooks)
│   ├── review.sh           # Codex code review + auto-fix ALL issues
│   ├── document.sh         # Hybrid: sprint summary + update main docs
│   └── test.sh             # Test suite → backend/tests/sprint/
└── prompts/
    ├── review.md           # Code review prompt template
    ├── document.md         # Documentation prompt template
    └── test.md             # Test generation prompt template
```

**Manifest tracking**: Each sprint gets `manifest.json` tracking start/end commits, timestamps, and per-chunk commits for review/docs/tests.

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
5. Loop validates state-delta (chunk count must increase) before accepting
6. Loop auto-continues to next chunk (fresh context window per iteration)
7. Loop exits when: all chunks pass, agent blocked, or max iterations reached
8. Post-sprint hooks run automatically (review, docs, tests)

**CLI flags**: `--resume` (continue from last iteration), `--force-hooks` (re-run completed hooks)

**Auto-continue**: No manual intervention between chunks. Each chunk gets fresh context. Agent updates chunks.json itself.

## Git Commits

**Agent commits after each chunk** with a descriptive message, then outputs RALPH_COMPLETE. The loop has backup commits but they become no-ops if agent already committed.

**Completion sequence**:
1. Complete chunk's acceptance criteria
2. `git add -A && git commit -m "Add X feature"` (descriptive message)
3. Update chunks.json: set `passes: true`
4. Output: `<promise>RALPH_CHUNK_COMPLETE</promise>`

**Scoped markers**: `RALPH_CHUNK_COMPLETE` (chunk done), `RALPH_SPRINT_COMPLETE` (all chunks done), `RALPH_COMPLETE` (legacy, still recognized as chunk-level).

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

## Documentation

- `docs/sprint-structure.md` - How to organize sprints and chunks
- `templates/` - Loop script, hooks, and prompt templates

## References

- [frankbria/ralph-claude-code](https://github.com/frankbria/ralph-claude-code)
- [vercel-labs/ralph-loop-agent](https://github.com/vercel-labs/ralph-loop-agent)

## Repository Structure

This repo tracks Ralph method tooling only. Project repos (like `blackbird/`) are cloned here for autonomous coding but tracked in their own git repos.

**Tracked**: `docs/`, `templates/`, `CLAUDE.md`, `AGENTS.md`, `README.md`
**Ignored**: All project folders, logs, notes

---

Keep `AGENTS.md` and `CLAUDE.md` in sync.
