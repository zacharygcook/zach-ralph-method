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
Iteration 1: Agent reads codebase, implements feature A, commits, exits
Iteration 2: Agent reads codebase (now includes A), implements B, commits, exits
Iteration 3: Agent reads codebase (now includes A+B), implements C, commits, exits
...
Iteration N: All chunks complete → RALPH_COMPLETE → loop exits
```

Each iteration:
- Starts with a clean context window
- Reads the current state from files (not memory)
- Makes progress on the next chunk
- Commits and marks completion
- Exits, triggering the next iteration

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

The loop script greps for this marker. If found, it moves to the next chunk. If not, it re-prompts with the same chunk until success or max iterations.

## Credits & References

- [frankbria/ralph-claude-code](https://github.com/frankbria/ralph-claude-code) - Original inspiration
- [vercel-labs/ralph-loop-agent](https://github.com/vercel-labs/ralph-loop-agent) - Vercel's implementation
- [Geoffrey Huntley's technique](https://ghuntley.com/ralph/) - The OG Ralph method

---

*This is a living document, refined through real autonomous coding sessions.*
