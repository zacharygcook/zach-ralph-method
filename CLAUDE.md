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
├── config.env                  # Agent, iterations, CURRENT_SPRINT
├── loop.sh                     # Bash loop script
├── logs/
│   └── <sprint>/run-<timestamp>/   # Logs per sprint per run
└── sprints/
    └── 1-sprint-name/          # Each sprint gets numbered folder
        ├── prompt.md           # Sprint-specific prompt
        ├── README.md           # Sprint goal (3-4 lines)
        ├── IMPLEMENTATION_PLAN.md
        ├── relevant-specs.md
        └── chunks.json
```

Set `CURRENT_SPRINT=1-sprint-name` in config.env to select active sprint.

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
3. Run `./.ralph/loop.sh`
4. Agent completes chunk → commits → sets `passes: true` → outputs RALPH_COMPLETE
5. Loop auto-continues to next chunk
6. Exits when ALL chunks pass or agent is blocked

**Auto-continue**: No manual intervention between chunks. Agent updates chunks.json itself.

## Git Commits

**Agent commits after each chunk** with a descriptive message, then outputs RALPH_COMPLETE. The loop has backup commits but they become no-ops if agent already committed.

**Completion sequence**:
1. Complete chunk's acceptance criteria
2. `git add -A && git commit -m "Add X feature"` (descriptive message)
3. Update chunks.json: set `passes: true`
4. Output: `<promise>RALPH_COMPLETE</promise>`

**Commit rules for prompts**:
- No "Generated with Claude Code" lines
- No "Co-Authored-By" lines
- Clean, descriptive messages only

## Agent Flags

| Agent | Autonomous Flag |
|-------|-----------------|
| claude | `--dangerously-skip-permissions` (sandbox!) |
| codex | `--auto-approve` |
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
- `templates/` - Loop script and config templates

## References

- [frankbria/ralph-claude-code](https://github.com/frankbria/ralph-claude-code)
- [vercel-labs/ralph-loop-agent](https://github.com/vercel-labs/ralph-loop-agent)

## Repository Structure

This repo tracks Ralph method tooling only. Project repos (like `blackbird/`) are cloned here for autonomous coding but tracked in their own git repos.

**Tracked**: `docs/`, `templates/`, `CLAUDE.md`, `AGENTS.md`, `README.md`
**Ignored**: All project folders, logs, notes

---

Keep `CLAUDE.md` and `AGENTS.md` in sync.
