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
    │   ╔═══════════════════════════════════════════════╗ │
    │   ║               THE LOOP                        ║ │
    │   ║  ┌────────────────────────────────────────┐   ║ │
    │   ║  │                                        │   ║ │
    │   ║  │   prompt.md ──▶ agent ──▶ check ──┐    │   ║ │
    │   ║  │       ▲                           │    │   ║ │
    │   ║  │       │                           │    │   ║ │
    │   ║  │       │     RALPH_COMPLETE?       │    │   ║ │
    │   ║  │       │                           │    │   ║ │
    │   ║  │       │   NO ◄─────────────┘      │    ║   ║ │
    │   ║  │       │                           │    │   ║ │
    │   ║  │       └───────────────────────────┘    │   ║ │
    │   ║  │                                        │   ║ │
    │   ║  │              YES ▼                     │   ║ │
    │   ║  │         ╔═══════════╗                  │   ║ │
    │   ║  │         ║   DONE!   ║                  │   ║ │
    │   ║  │         ╚═══════════╝                  │   ║ │
    │   ║  └────────────────────────────────────────┘   ║ │
    │   ╚═══════════════════════════════════════════════╝ │
    │                                                      │
    └──────────────────────────────────────────────────────┘
```

## What is the Ralph Method?

A bash loop that wraps an AI coding agent, re-prompting until the task is complete. Named after Ralph Wiggum's relentless optimism - the agent keeps trying until it succeeds.

**The core insight**: Files persist between iterations, but context resets. Progress accumulates in code and git commits while each iteration starts fresh with full context capacity.

## Why It Works

```
Iteration 1: Agent reads codebase, implements chunk 1, commits, outputs RALPH_COMPLETE
Iteration 2: Agent reads codebase (fresh context), implements chunk 2, commits, outputs RALPH_COMPLETE
Iteration 3: Agent reads codebase (fresh context), implements chunk 3, commits, outputs RALPH_COMPLETE
...
Iteration N: All chunks pass → loop exits → prompts for next sprint
```

Each iteration:
- Starts with a clean context window (fresh agent process)
- Reads `SCRATCHPAD.md` for learnings from prior iterations (dead ends, gotchas)
- Reads the current state from files (not memory)
- Makes progress on the next incomplete chunk
- Appends learnings to `SCRATCHPAD.md`, commits, marks chunk as passed, outputs RALPH_COMPLETE
- Loop continues to next iteration automatically

## Quick Start

1. Clone this repo
2. Clone your target project into this directory
3. Create `.ralph/` structure in target project (see `docs/sprint-structure.md`)
4. Create `IMPLEMENTATION_PLAN.md` in planning mode
5. Create `chunks.json` based on plan
6. Run `.ralph/loop.sh`

See `docs/` for detailed setup guides and `templates/` for starter files.

## Supported Agents

| Agent | Command | Autonomous Flag |
|-------|---------|-----------------|
| Claude Code | `claude` | `--dangerously-skip-permissions` |
| OpenAI Codex | `codex` | `--auto-approve` |
| Amp | `amp` | `--autonomous` |
| OpenCode | `opencode` | `--auto` |
| Droid (Factory) | `droid` | `exec --auto high` |

## Key Insight: Real-Time Visibility

Claude Code's `-p` flag enables non-interactive mode. Add `--output-format=stream-json` for real-time streaming:

```bash
claude --dangerously-skip-permissions -p "$(cat prompt.md)" \
  --output-format=stream-json --verbose 2>&1 \
  | tee "$LOG_FILE" | python3 format-stream.py
```

See `templates/format-stream.py` for colored terminal output while preserving full logs.

## Repository Structure

```
ralph-method/
├── README.md           # You are here
├── CLAUDE.md           # Context for Claude Code
├── AGENTS.md           # Context for other agents
├── docs/               # Detailed documentation
│   └── sprint-structure.md
└── templates/          # Starter files
    ├── loop.sh.template
    ├── config.env.template
    ├── prompt.md.template
    └── format-stream.py
```

Project repos (like `blackbird/`) are cloned here but tracked in their own git repos.

## The Completion Promise

When a chunk is complete, the agent outputs:

```
<promise>RALPH_COMPLETE</promise>
```

The loop greps for this marker and continues to the next chunk (fresh context window). The loop only exits when:
- **All chunks pass** - Sprint complete, prompts for next sprint
- **Agent blocked** - Outputs `<blocked>reason</blocked>`, needs human input
- **Max iterations** - Safety limit reached without completion

## Credits & References

- [frankbria/ralph-claude-code](https://github.com/frankbria/ralph-claude-code) - Original inspiration
- [vercel-labs/ralph-loop-agent](https://github.com/vercel-labs/ralph-loop-agent) - Vercel's implementation
- [Geoffrey Huntley's technique](https://ghuntley.com/ralph/) - The OG Ralph method

---

*This is a living document, refined through real autonomous coding sessions.*
