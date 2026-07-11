# The Ralph Method

A hardened, observable autonomous coding loop for one repository or a coordinated group of repositories.

Ralph gives a coding agent a bounded chunk of work, lets it implement and verify that chunk in a fresh context, records durable handoff state, and repeats. The runtime treats autonomy as an operator-controlled capability: it installs disarmed, fingerprints its managed files, validates real state changes before accepting completion, and leaves interrupted post-sprint work resumable.

```text
SPEC → PLAN → CHUNKS → IMPLEMENT → VERIFY → COMMIT
                         ↑                    │
                         └── fresh context ───┘
                                  │
                           all chunks pass
                                  ↓
                        REVIEW → DOCS → TESTS
```

## Why this implementation

- **Fresh context, durable memory.** Each iteration starts a new agent process and reads `SCRATCHPAD.md`, plans, specs, and chunk state from disk.
- **Evidence-backed completion.** A completion marker counts only when the number of passing chunks increases.
- **Operator-owned safety.** Unattended execution and broad automatic staging have separate, explicit authorization gates. Both default off.
- **Crash-safe orchestration.** Manifests, locks, heartbeats, structured events, state files, and `--resume` make long runs inspectable and recoverable.
- **First-class multi-repo work.** Each child repository keeps its own Git boundary and start/end commit range.
- **Project-neutral hooks.** Review, documentation, test, and E2E commands are configured by the adopting project rather than assumed by the runtime.

## Install in 30 seconds

Clone this repository, then install into a Git repository:

```bash
python3 scripts/ralph.py init --repo /path/to/project --agent codex --test-command "your test command"
```

For a parent directory containing multiple child Git repositories:

```bash
python3 scripts/ralph.py init --repo /path/to/parent --mode multi-repo --repos api web --primary-repo api --agent codex --test-command "your cross-repo test command"
```

The installer creates `.ralph/` but leaves autonomous execution disarmed. Review `.ralph/config.env`, create a sprint, then explicitly set `RALPH_UNATTENDED_APPROVED=true` when you are ready—or pass `--approve-unattended` only when that authorization is deliberate.

## Quick start

Every sprint lives at `.ralph/sprints/<number-name>/` and contains:

```text
README.md                short goal and boundaries
IMPLEMENTATION_PLAN.md   ordered implementation design
relevant-specs.md        curated source-of-truth context
chunks.json              sequential work and acceptance criteria
prompt.md                instructions for each fresh agent context
SCRATCHPAD.md            append-only discoveries and handoff memory
```

Set `CURRENT_SPRINT` in `.ralph/config.env`, then:

```bash
python3 scripts/ralph.py validate --repo /path/to/project
/path/to/project/.ralph/loop.sh
python3 scripts/ralph.py status --repo /path/to/project
```

Use `.ralph/loop.sh --resume` after interruption. Use `--force-hooks` only when intentionally rerunning completed post-sprint hooks.

## Supported agent harnesses

The generated runtime supports Claude Code, Codex, Droid, Amp, OpenCode, and a trusted custom command. CLI flags evolve, so `RALPH_AGENT_COMMAND` provides an escape hatch without changing the orchestrator.

Custom commands receive:

- `RALPH_PROMPT_FILE` — the prompt file for the current iteration or hook
- `RALPH_PROJECT_ROOT` — the working directory the command should use

## Safety model

The default installation will not run autonomously. It also will not auto-commit. If a project deliberately enables runtime backup commits, both `RALPH_AUTO_COMMIT=true` and `I_ACCEPT_GIT_ADD_ALL=true` are required. Normal agent prompts instruct scoped staging instead.

`--update-runtime` refreshes only managed runtime files. It preserves operator configuration, sprints, logs, and scratchpad state, and refuses mode changes or managed symlinks that could escape `.ralph/`.

## Validation and portability

```bash
python3 -m unittest discover -s tests -v
```

The clean-room suite installs and executes disposable monorepo and multi-repo fixtures. GitHub Actions runs it on macOS and Linux with multiple Python versions.

## Documentation

- [`docs/sprint-structure.md`](docs/sprint-structure.md) — sprint anatomy and lifecycle
- [`docs/multi-repo-setup.md`](docs/multi-repo-setup.md) — coordinating independent repositories
- [`docs/definition-of-terms.md`](docs/definition-of-terms.md) — precise vocabulary
- [`docs/migration-report.md`](docs/migration-report.md) — hardening history

## Credits

Inspired by [Geoffrey Huntley's Ralph technique](https://ghuntley.com/ralph/), [frankbria/ralph-claude-code](https://github.com/frankbria/ralph-claude-code), and [vercel-labs/ralph-loop-agent](https://github.com/vercel-labs/ralph-loop-agent).
