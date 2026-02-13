# Sprint Structure

How to organize work for Ralph loops using sprints, planning, and chunks.

## The Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         RALPH METHOD WORKFLOW                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌──────────┐    ┌──────────────┐    ┌─────────┐    ┌──────────┐      │
│   │  SPEC    │───▶│    PLAN      │───▶│  CHUNK  │───▶│   RUN    │      │
│   │  (human) │    │  (agent+you) │    │ (agent) │    │  (loop)  │      │
│   └──────────┘    └──────────────┘    └─────────┘    └──────────┘      │
│        │                 │                 │               │            │
│        ▼                 ▼                 ▼               ▼            │
│   SPEC.md         IMPLEMENTATION    chunks.json      iterate until     │
│   (source of      _PLAN.md          (sequenced       all chunks        │
│    truth)         (60-70 lines)      tasks)          pass: true        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Phase 1: SPEC (Human-Driven)

You already have this - your detailed specification document.

## Phase 2: PLAN (Agent + Human)

Before chunking, enter **deep planning mode** with your agent to create:

```
.ralph/sprints/IMPLEMENTATION_PLAN.md (60-70 lines max)
```

This answers:
- What's the execution order and why?
- What are the dependencies between pieces?
- What patterns/files should be followed?
- What are the risks/gotchas?

```
┌────────────────────────────────────────────────────────┐
│              IMPLEMENTATION_PLAN.md                     │
├────────────────────────────────────────────────────────┤
│  # Implementation Plan: [Sprint Name]                   │
│                                                         │
│  ## Execution Order                                     │
│  1. Core tables first (others depend on these)         │
│  2. Supporting tables (can reference core)             │
│  3. Generation tables (depends on send_lists)          │
│  4. Queue infrastructure (needs models to exist)       │
│  5. Seeder + linking (final touches)                   │
│                                                         │
│  ## Key Dependencies                                    │
│  - leads requires workspaces (FK)                      │
│  - send_lists requires prompt_templates (FK)           │
│  - generation_outputs requires multiple FKs            │
│                                                         │
│  ## Patterns to Follow                                  │
│  - See backend/app/models/user.ts for model pattern    │
│  - UUID primary keys everywhere                         │
│  - CITEXT for email columns                            │
│                                                         │
│  ## Risks                                               │
│  - Circular FK if not ordered correctly                │
│  - Missing CITEXT extension                            │
└────────────────────────────────────────────────────────┘
```

## Phase 3: CHUNK (Agent Creates)

Based on IMPLEMENTATION_PLAN, create `chunks.json`:

```
┌─────────────────────────────────────────────────────────┐
│                    chunks.json                          │
├─────────────────────────────────────────────────────────┤
│  {                                                      │
│    "chunks": [                                          │
│      { "id": 1, "title": "Core Tables",                │
│        "passes": false,                                 │
│        "acceptance_criteria": [...] },                  │
│      { "id": 2, "title": "Supporting Tables",          │
│        "passes": false, ... },                          │
│      ...                                                │
│    ]                                                    │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
```

## Phase 4: RUN (Loop Executes)

Uses `tee` for **real-time streaming** and **auto-continues** through all chunks.

```
┌─────────────────────────────────────────────────────────┐
│                    EXECUTION LOOP                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│    ./.ralph/loop.sh                                     │
│          │                                              │
│          ▼                                              │
│    ┌─────────────┐                                      │
│    │ Read prompt │                                      │
│    │   + specs   │                                      │
│    └──────┬──────┘                                      │
│           │                                             │
│           ▼                                             │
│    ┌─────────────┐     ┌─────────────┐                 │
│    │ Find first  │────▶│   Execute   │                 │
│    │ chunk where │     │   chunk     │                 │
│    │ passes:false│     └──────┬──────┘                 │
│    └─────────────┘            │                        │
│                               ▼                        │
│                    ┌────────────────────────────┐      │
│                    │  RALPH_CHUNK_COMPLETE?     │      │
│                    └─────────────┬──────────────┘      │
│                             │                          │
│              ┌──────────────┼──────────────┐           │
│              ▼              ▼              ▼           │
│           [yes]         [blocked]       [no]           │
│              │              │              │           │
│              ▼              ▼              ▼           │
│    ┌─────────────┐     EXIT (1)    Next iteration      │
│    │All chunks   │    Human help   (fresh context)     │
│    │pass: true?  │     needed            │             │
│    └──────┬──────┘                       │             │
│      yes/ \no                            │             │
│        /   \                             │             │
│       ▼     ▼◄───────────────────────────┘             │
│   EXIT (0)  Continue to                                │
│   Sprint    next chunk                                 │
│   done!     (fresh ctx)                                │
│                                                         │
│   (Also exits with code 2 if max iterations reached)   │
└─────────────────────────────────────────────────────────┘
```

**Key behavior**: Agent completes chunk → commits with descriptive message → sets `passes: true` → outputs RALPH_CHUNK_COMPLETE. Loop continues to next chunk (fresh context) until: all chunks pass, agent blocked, or max iterations reached.

**Git commit sequence**:
1. Complete acceptance criteria
2. `git add -A && git commit -m "Descriptive message"`
3. Update chunks.json: `passes: true`
4. Output: `<promise>RALPH_CHUNK_COMPLETE</promise>`

**Scoped markers**: Use `RALPH_CHUNK_COMPLETE` for individual chunks, `RALPH_SPRINT_COMPLETE` when all chunks are done. Legacy `RALPH_COMPLETE` is still recognized as chunk-level.

**State-delta validation**: The loop verifies chunk pass count increased before accepting a marker-based completion signal.

## Directory Structure

```
<project>/.ralph/
├── config.env                      # Agent, max iterations, CURRENT_SPRINT, timeouts
├── loop.sh                         # Bash loop script (heartbeat, resume, state-delta)
├── status.sh                       # Operator status command
├── lib/
│   └── ralph-common.sh             # Shared helpers (locking, heartbeat, events)
├── format-stream.py                # Output formatter (Claude)
├── format-codex-stream.py          # Output formatter (Codex)
├── logs/
│   └── <sprint>/run-<timestamp>/   # Logs organized by sprint and run
│       ├── orchestrator.log        # Timestamped orchestrator events
│       ├── events.jsonl            # Structured event stream
│       ├── iteration-N.log         # Full JSON log
│       └── iteration-N.summary.log # Human-readable summary
└── sprints/
    ├── 1-scaffold-foundation/      # First sprint
    │   ├── prompt.md
    │   ├── README.md
    │   ├── IMPLEMENTATION_PLAN.md
    │   ├── relevant-specs.md
    │   └── chunks.json
    └── 2-api-integration/          # Next sprint
        └── ...
```

Set `CURRENT_SPRINT=1-scaffold-foundation` in config.env to select active sprint.

## Chunk Design Guidelines

Each chunk should:
- Be completable in one context window (~20-30 files max)
- Have clear, verifiable acceptance criteria
- End with validation (`yarn typecheck`, `migration:run`, etc.)
- Be independent enough that context reset doesn't break it

## Real-Time Output (Claude Code)

The `-p` (print) flag puts Claude in non-interactive mode, losing the TUI. To get real-time visibility of tool calls:

```bash
claude --dangerously-skip-permissions -p "$(cat "$PROMPT_FILE")" \
  --output-format=stream-json --include-partial-messages --verbose 2>&1 \
  | tee "$LOG_FILE" \
  | python3 format-stream.py
```

**Key flags**:
- `--output-format=stream-json` - Streams JSON events in real-time
- `--include-partial-messages` - Shows text as it's generated (requires stream-json)
- `--verbose` - Required for stream-json in print mode

**What you see**:
- Tool calls with their parameters as they happen
- Text output streaming token-by-token
- Tool results (success/error)
- Final result with cost and duration

The log file (`$LOG_FILE`) gets raw JSON, terminal shows formatted output. A separate summary log (`iteration-N.summary.log`) captures human-readable output. Grep for `RALPH_CHUNK_COMPLETE` still works in the JSON.

**Formatter** (`format-stream.py`) - simplified example, see `templates/format-stream.py` for full version with summary logging:
```python
#!/usr/bin/env python3
import json, sys
CYAN, GREEN, YELLOW, DIM, BOLD, RESET = "\033[36m", "\033[32m", "\033[33m", "\033[2m", "\033[1m", "\033[0m"
current_tool, current_input = None, ""
for line in sys.stdin:
    try: data = json.loads(line.strip())
    except: continue
    if data.get("type") == "stream_event":
        event = data.get("event", {})
        if event.get("type") == "content_block_start" and event.get("content_block", {}).get("type") == "tool_use":
            current_tool = event["content_block"].get("name")
            print(f"\n{CYAN}▶ {current_tool}{RESET}", end="", flush=True)
        elif event.get("type") == "content_block_delta":
            delta = event.get("delta", {})
            if delta.get("type") == "text_delta": print(delta.get("text", ""), end="", flush=True)
            elif delta.get("type") == "input_json_delta": current_input += delta.get("partial_json", "")
        elif event.get("type") == "content_block_stop" and current_tool:
            try:
                for k, v in json.loads(current_input).items(): print(f" {DIM}{k}={str(v)[:50]}{RESET}", end="")
            except: pass
            print(); current_tool, current_input = None, ""
    elif data.get("type") == "user" and data.get("tool_use_result"):
        result = str(data["tool_use_result"])[:80]
        print(f"  {'⚠' if 'Error' in result else '✓'} {result}")
    elif data.get("type") == "result":
        print(f"\n{BOLD}Done:{RESET} ${data.get('total_cost_usd', 0):.4f}")
```

## Tips

- Spend time on IMPLEMENTATION_PLAN - it prevents bad chunking
- Always include validation as final acceptance criterion
- Keep prompt.md generic - details live in sprint files
- Number chunks in dependency order
- Use stream-json + formatter for real-time visibility of what Claude is doing
